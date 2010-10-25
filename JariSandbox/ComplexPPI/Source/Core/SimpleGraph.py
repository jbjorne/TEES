"""
For representing the event argument and dependency graphs. Should be deterministic.
"""

class Graph():
    """
    One edge per-associated data per direction
    """
    def __init__(self, directed=True):
        self.__directed = directed
        self.nodes = []
        self.edges = []
        self.__matrix = {}
        self.__resetAnalyses()
    
    def __resetAnalyses(self):
        self.__distances = None
        self.__nextInPath = None
    
    def isDirected(self):
        return self.__directed
    
    def toUndirected(self):
        g = Graph(False)
        g.nodes = self.nodes[:]
        for n1 in g.nodes:
            self.__matrix[n1] = {}
            for n2 in g.nodes:
                self.__matrix[n1][n2] = []
        for edge in self.edges:
            g.addEdge(edge[0], edge[1], edge[2])
            g.addEdge(edge[1], edge[2], edge[2])
    
    def addNode(self, node):
        if node in self.nodes:
            return False
        self.__resetAnalyses()
        for n in self.nodes:
            self.__matrix[n][node] = []
        self.nodes.append(node)
        self.__matrix[node] = {}
        for n in self.nodes:
            self.__matrix[node][n] = []
        return True
    
    def addNodes(self, nodes):
        addNodes = False
        for node in nodes:
            if node not in self.nodes:
                addNodes = True
                break
        if not addNodes:
            return False
        self.__resetAnalyses()
        for node in nodes:
            for n in self.nodes:
                self.__matrix[n][node] = []
            self.nodes.append(node)
            self.__matrix[node] = {}
            for n in self.nodes:
                self.__matrix[node][n] = []
        return True
    
    def addEdge(self, node1, node2, data=None):
        self.__resetAnalyses()
        if not node1 in self.nodes:
            self.addNode(node1)
        if not node2 in self.nodes:
            self.addNode(node2)
        # add forward edge
        forward = not self.hasEdge(node1, node2, data)
        if forward:
            self.__insertEdge(node1, node2, data)
        # add reverse edge
        reverse = False
        if not self.isDirected():
            reverse = not self.hasEdge(node2, node1, data)
            if reverse:
                self.__insertEdge(node2, node1, data)
        return forward or reverse
    
    def __insertEdge(self, node1, node2, data):
        """
        Assumes edge doesn't exist already
        """
        edge = (node1, node2, data)
        self.edges.append(edge)
        self.__matrix[node1][node2].append(edge)
        
    def hasEdge(self, node1, node2, data=None):
        for edge in self.__matrix[node1][node2]:
            if edge[2] == data:
                return True
        return False
    
    def getEdges(self, node1, node2):
        return self.__matrix[node1][node2]
    
    def FloydWarshall(self):
        n = len(self.nodes)
        self.__distances = {}
        infinity = sys.maxint # at least it's a really large number
        # Init distance matrix
        for n1 in self.nodes:
            self.__distances[n1] = {}
            for n2 in self.nodes:
                if n1 == n2:
                    self.__distances[n1][n2] = 0
                elif len(self.getEdges(n1, n2)) > 0:
                    self.__distances[n1][n2] = 1
                else:
                    self.__distances[n1][n2] = infinity
        # Init path traversal matrix    
        self.__nextInPath = {}
        for n1 in self.nodes:
            self.__nextInPath[n1] = {}
            for n2 in self.nodes:
                self.__nextInPath[n1][n2] = None
        # Calculate distances
        d = self.__distances    
        for k in self.nodes:
            for i in self.nodes:
                for j in self.nodes:
                    if d[i][k] + d[k][j] < d[i][j]:
                        d[i][j] = d[i][k] + d[k][j]
                        self.__nextInPath[i][j] = k
        print d
        
    def getPath(self, i, j):
        if self.__nextInPath == None:
            self.FloydWarshall()
        if self.__distances[i][j] == sys.maxint:
            return None
        intermediate = self.__nextInPath[i][j]
        if intermediate == None:
            return [i, j] #;   /* there is an edge from i to j, with no vertices between */
        else:
            segment = self.getPath(intermediate,j)
            return [i] + segment

    def getPathOld(self, i, j):
        if self.__nextInPath == None:
            self.FloydWarshall()
        if self.__distances[i][j] == sys.maxint:
            return None
        intermediate = self.__nextInPath[i][j]
        if intermediate == None:
            return [i, j] #;   /* there is an edge from i to j, with no vertices between */
        else:
            segment1 = self.getPath(i,intermediate)
            if segment1 == None:
                return None
            segment2 = self.getPath(intermediate,j)
            if segment2 == None:
                return None
            #return segment1 + [intermediate] + segment2
            return segment1 + segment2
    
    def getWalks(self, node1, node2, directed=False):
        path = self.getPath(node1, node2)
        return self.__getWalks(path, directed=directed)
    
    def __getWalks(self, path, position=1, walk=None, directed=False):
        """
        A path is defined by a list of tokens. But since there can be more than one edge
        between the same two tokens, there are multiple ways of getting from the first
        token to the last token. This function returns all of these "walks", i.e. the combinations
        of edges that can be travelled to get from the first to the last token of the path.
        """
        allWalks = []
        if walk == None:
            walk = []
        
        node1 = path[position-1]
        node2 = path[position]
        edges = self.__matrix[node1][node2]
        if not directed and not self.__directed: # an undirected graph already has the reverse edges
            edges += pathEdges[node2][node1]
        for edge in edges:
            if position < len(path)-1:
                allWalks.extend(self.getWalks(path, position+1, walk + [edge], directed))
            else:
                allWalks.append(walk + [edge])
        return allWalks

if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    g = Graph()
    print g
    g.addNodes([1, 2, 3, 4, 5])
    g.addEdge(1,2)
    g.addEdge(2,3)
    g.addEdge(1,4)
    g.addEdge(4,3)
    print "nodes", g.nodes
    print "edges", g.edges
    print g.getPath(1,3)
    print g.getPath(4,3)
