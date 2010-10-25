"""
For representing the event argument and dependency graphs. Should be deterministic.
"""
import sys    

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
        g.addNodes(self.nodes)
        g.addEdges(self.edges)
        return g
    
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
    
    def addEdges(self, edges):
        for edge in edges:
            self.addEdge(edge[0], edge[1], edge[2])
    
    def __insertEdge(self, node1, node2, data):
        """
        Assumes edge doesn't exist already
        """
        edge = (node1, node2, data)
        self.edges.append(edge)
        self.__matrix[node1][node2].append(edge)
    
    def hasEdges(self, node1, node2):
        if len(self.__matrix[node1][node2]) > 0:
            return True
        else:
            return False
    
    def hasEdge(self, node1, node2, data):
        for edge in self.__matrix[node1][node2]:
            if edge[2] == data:
                return True
        return False
    
    def getEdges(self, node1, node2):
        return self.__matrix[node1][node2]
    
    def getInEdges(self, node):
        assert self.__directed
        inEdges = []
        for edge in self.edges:
            if edge[1] == node:
                inEdges.append(edge)
        return inEdges

    def getOutEdges(self, node):
        assert self.__directed
        outEdges = []
        for edge in self.edges:
            if edge[0] == node:
                outEdges.append(edge)
        return outEdges
    
    def FloydWarshall(self):
        """
        From Wikipedia, modified to return all paths
        """
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
                if d[i][k] == infinity:
                    continue
                for j in self.nodes:
                    if d[k][j] == infinity:
                        continue
                    # equal
                    if d[i][k] + d[k][j] < d[i][j]:
                        d[i][j] = d[i][k] + d[k][j]
        for k in self.nodes:
            for i in self.nodes:
                if d[i][k] == infinity:
                    continue
                for j in self.nodes:
                    if d[k][j] == infinity:
                        continue
                    # shorter or equal
                    if d[i][k] + d[k][j] <= d[i][j]:
                        if d[i][k] == 1 and k != j:
                            if self.__nextInPath[i][j] == None or d[i][k] + d[k][j] < d[i][j]:
                                self.__nextInPath[i][j] = []
                            self.__nextInPath[i][j].append(k)
        #self.showAnalyses()
    
    def showAnalyses(self):
        print "distances"
        for k in sorted(self.__distances.keys()):
            print ">", k, self.__distances[k]
        print "next"
        for k in sorted(self.__nextInPath.keys()):
            print ">", k, self.__nextInPath[k]

    def getPaths(self, i, j, depth=0):
        if self.__nextInPath == None:
            self.FloydWarshall()
        if self.__distances[i][j] == sys.maxint: # no path
            return []
        intermediates = self.__nextInPath[i][j]
        if intermediates == None:
            return [[i, j]] # there is an edge from i to j, with no vertices between
        else:
            segments = []
            for intermediate in intermediates:
                segments.extend( self.getPaths(intermediate,j, depth+1) )
            rvs = []
            for segment in segments:
                rvs.append( [i] + segment )
            return rvs
        
    def getPathOldSinglePath(self, i, j):
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
    
    def getWalks(self, path, directed=False):
        if directed:
            assert self.__directed
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
        if (not directed) and self.__directed: # an undirected graph already has the reverse edges
            edges += self.__matrix[node2][node1]
        for edge in edges:
            if position < len(path)-1:
                allWalks.extend(self.__getWalks(path, position+1, walk + [edge], directed))
            else:
                allWalks.append(walk + [edge])
        return allWalks
    
    def toGraphviz(self, filename=None):
        s = "digraph PhiloDilemma {\nnode [shape=box];\n"
        for node in self.nodes:
            s += str(node) + ";\n"
        for edge in self.edges:
            s += str(edge[0]) + "->" + str(edge[1]) + ";\n"
        s += "overlap=false;\nfontsize=12;\n}"
        if filename != None:
            f = open(filename, "wt")
            f.write(s)
            f.close()
        return s

if __name__=="__main__":
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
    g.addNodes([1, 2, 3, 4, 5, 6])
    g.addEdge(1,2)
    g.addEdge(2,3)
    g.addEdge(1,4)
    g.addEdge(4,3)
    g.addEdge(4,3,"Test")
    g.addEdge(3,6)
    g.addEdge(6,1)
    print "nodes", g.nodes
    print "edges", g.edges
    u = g.toUndirected()
    paths = g.getPaths(1,3)
    print g.showAnalyses()
    print "Paths 1->3", paths
    print "Undirected Paths 1->3", u.getPaths(1,3)
    print "Paths 4->3", g.getPaths(4,3)
    print "Paths 4->5", g.getPaths(4,5)
    print "Walks 1->3"
    for p in paths:
        print "Walks for path", p, ":", g.getWalks(p)
    print "Walks 4->5", g.getWalks([4,5])
    print "Walks 1->6->3", g.getWalks([1,6,3], True)
    print "Walks 1->6->3 (undirected walks from directed graph)", g.getWalks([1,6,3])
    print "Walks 1->6->3 from undirected", u.getWalks([1,6,3])
    print "Hard case"
    g = Graph()
    #g.addEdges([('st_4', 'st_3', 'split_1'), ('st_1', 'st_4', 'split_2'), ('st_11', 'st_6', 'split_3'), ('st_6', 'st_8', 'split_4'), ('st_11', 'st_10', 'split_5'), ('st_1', 'st_11', 'split_6'), ('st_4', 'st_11', 'split_7'), ('st_14', 'st_13', 'split_8'), ('st_1', 'st_14', 'split_9'), ('st_17', 'st_16', 'split_10'), ('st_14', 'st_17', 'split_11'), ('st_21', 'st_19', 'split_12'), ('st_21', 'st_20', 'split_13'), ('st_14', 'st_21', 'split_14'), ('st_26', 'st_23', 'split_15'), ('st_26', 'st_24', 'split_16'), ('st_26', 'st_25', 'split_17'), ('st_21', 'st_26', 'split_18'), ('st_26', 'st_27', 'split_19')])
    g.addEdges([('st_4', 'st_3', 'split_1'), ('st_1', 'st_4', 'split_2'), ('st_11', 'st_6', 'split_3'), ('st_6', 'st_8', 'split_4'), ('st_11', 'st_10', 'split_5'), ('st_1', 'st_11', 'split_6'), ('st_4', 'st_11', 'split_7'), ('st_14', 'st_13', 'split_8'), ('st_1', 'st_14', 'split_9'), ('st_17', 'st_16', 'split_10'), ('st_14', 'st_17', 'split_11'), ('st_21', 'st_19', 'split_12'), ('st_21', 'st_20', 'split_13'), ('st_14', 'st_21', 'split_14'), ('st_26', 'st_23', 'split_15'), ('st_26', 'st_24', 'split_16'), ('st_26', 'st_25', 'split_17'), ('st_21', 'st_26', 'split_18'), ('st_26', 'st_27', 'split_19')])
    print "Paths 'st_14'->'st_6'", g.getPaths('st_14','st_6')
    u = g.toUndirected()
    #print "Undirected Paths 'st_14'->'st_6'", u.getPaths('st_14','st_6')
    print "Undirected Paths 'st_14'->'st_11'", u.getPaths('st_14','st_11')
    print "Walks", g.getWalks(['st_14', 'st_1', 'st_11'])
    print u.showAnalyses()
    u.toGraphviz("vis.gv")
    
