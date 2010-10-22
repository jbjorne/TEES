"""
For representing the event argument and dependency graphs. Should be deterministic.
"""

def Graph():
    """
    One edge per-associated data per direction
    """
    def __init__(directed=True):
        self.__directed = directed
        self.nodes = []
        self.edges = []
        self.__matrix = {}
        self.__resetAnalyses()
    
    def __resetAnalyses():
        self.__distances = None
        self.__nextInPath = None
    
    def isDirected():
        return self.__directed
    
    def toUndirected():
        g = Graph(False)
        g.nodes = self.nodes[:]
        for n1 in g.nodes:
            self.__matrix[n1] = {}
            for n2 in g.nodes:
                self.__matrix[n1][n2] = []
        for edge in self.edges:
            g.addEdge(edge[0], edge[1], edge[2])
            g.addEdge(edge[1], edge[2], edge[2])
    
    def addNode(node):
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
    
    def addEdge(node1, node2, data=None):
        self.__resetAnalyses()
        if not node1 in self.nodes:
            self.nodes.append(node1)
        if not node2 in self.nodes:
            self.nodes.append(node2)
        # add forward edge
        forward = not self.hasEdge(node1, node2, data)
        if forward:
            self.__insertEdge(node1, node2, data)
        # add reverse edge
        reverse = True
        if not self.isDirected():
            reverse = not self.hasEdge(node2, node1, data)
        if reverse:
            self.__insertEdge(node2, node1, data)
        return forward or reverse
    
    def __insertEdge(node1, node2, data):
        """
        Assumes edge doesn't exist already
        """
        edge = (node1, node2, data)
        self.edges.append(edge)
        self.__matrix[node1][node2].append(edge)
        
    def hasEdge(node1, node2, data=None):
        for edge in self.__matrix[node1][node2]:
            if edge[2] == data:
                return True
        return False
    
    def getEdges(node1, node2):
        return self.__matrix[node1][node2]
    
    def FloydWarshall():
        n = len(self.nodes)
        self.__distances = {}
        infinity = sys.maxint # at least it's a really large number
        # Init distance matrix
        for n1 in self.__nodes:
            self.__distances[n1] = {}
            for n2 in self.__nodes:
                if n1 == n2:
                    self.__distances[n1][n2] = 0
                else:
                    self.__distances[n1][n2] = infinity
        # Init path traversal matrix    
        self.__nextInPath = {}
        for n1 in self.__nodes:
            self.__nextInPath[n1] = {}
            for n2 in self.__nodes:
                self.__nextInPath[n1][n2] = None
        # Calculate distances
        d = self.__distances    
        for k in self.__nodes:
            for i in self.__nodes:
                for j in self.__nodes:
                    if d[i][k] + d[k][j] <= d[i][j]:
                        d[i][j] = d[i][k] + d[k][j]
                        self.__nextInPath[i][j] = k

    def getPath(self, i, j):
        if self.__nextInPath == None:
            self.FloydWarshall()
        if self.__nextInPath[i][j] == None:
            return None
        intermediate = self.__nextInPath[i][j]
        if intermediate == 0:
            return [i, j] #;   /* there is an edge from i to j, with no vertices between */
        else:
            return self.getPath(i,intermediate) + intermediate + self.getPath(intermediate,j)
    
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
