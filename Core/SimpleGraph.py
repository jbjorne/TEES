"""
For representing the event argument and dependency graphs. Should be deterministic.
"""
import sys    

class Graph:
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
        if node in self.__matrix:
            return False
        self.__resetAnalyses()
        self.nodes.append(node)
        self.__matrix[node] = {}
        return True
    
    def addNodes(self, nodes):
        self.__resetAnalyses()
        nodesAdded = False
        for node in nodes:
            if node not in self.__matrix:
                nodesAdded = True
                self.nodes.append(node)
                self.__matrix[node] = {}
        return nodesAdded
    
    def addEdge(self, node1, node2, data=None):
        self.__resetAnalyses()
        self.addNode(node1)
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
        
    def addEdgeTuple(self, edge):
        self.__resetAnalyses()
        self.addNode(edge[0])
        self.addNode(edge[1])
        # add forward edge
        forward = not self.hasEdgeTuple(edge) #not edge in self.edges
        if forward:
            self.edges.append(edge)
            if not edge[1] in self.__matrix[edge[0]]:
                self.__matrix[edge[0]][edge[1]] = []
            self.__matrix[edge[0]][edge[1]].append(edge)
        # add reverse edge
        reverse = False
        if not self.isDirected():
            reverse = not self.hasEdge(edge[1], edge[0], edge[2])
            if reverse:
                self.__insertEdge(edge[1], edge[0], edge[2])
        return forward or reverse
    
    def addEdges(self, edges):
        for edge in edges:
            self.addEdgeTuple(edge)
    
    def __insertEdge(self, node1, node2, data):
        """
        Assumes edge doesn't exist already
        """
        edge = (node1, node2, data)
        self.edges.append(edge)
        if not node2 in self.__matrix[node1]:
            self.__matrix[node1][node2] = []
        self.__matrix[node1][node2].append(edge)
    
    def hasEdges(self, node1, node2):
        assert node1 in self.__matrix, "Missing node 1: " + str(node1)
        assert node2 in self.__matrix, "Missing node 2: " + str(node2)
        #if not node1 in self.__matrix:
        #    return False
        if not node2 in self.__matrix[node1]:
            return False
        elif len(self.__matrix[node1][node2]) > 0:
            return True
        else:
            return False

    def hasEdge(self, node1, node2, data):
        assert node1 in self.__matrix, "Missing node 1: " + str(node1)
        assert node2 in self.__matrix, "Missing node 2: " + str(node2)
        #if not node1 in self.__matrix:
        #    return False
        if not node2 in self.__matrix[node1]:
            return False
        for edge in self.__matrix[node1][node2]:
            if edge[2] == data:
                return True
        return False
    
    def hasEdgeTuple(self, edge):
        assert edge[0] in self.__matrix, "Missing node 1: " + str(edge[0])
        assert edge[1] in self.__matrix, "Missing node 2: " + str(edge[1])
        #if not edge[0] in self.__matrix:
        #    return False
        if not edge[1] in self.__matrix[edge[0]]:
            return False
        elif edge in self.__matrix[edge[0]][edge[1]]:
            return True
        else:
            return False
    
    def getEdges(self, node1, node2):
        assert node1 in self.__matrix, "Missing node 1: " + str(node1)
        assert node2 in self.__matrix, "Missing node 2: " + str(node2)
        #if not node1 in self.__matrix:
        #    return []
        if not node2 in self.__matrix[node1]:
            return []
        else:
            return self.__matrix[node1][node2]
    
    def getInEdges(self, node):
        assert node in self.__matrix, "Missing node: " + str(node)
        assert self.__directed
        inEdges = []
        for edge in self.edges:
            if edge[1] == node:
                inEdges.append(edge)
        return inEdges

    def getOutEdges(self, node):
        assert node in self.__matrix, "Missing node: " + str(node)
        assert self.__directed
        outEdges = []
        for edge in self.edges:
            if edge[0] == node:
                outEdges.append(edge)
        return outEdges
    
    def FloydWarshall(self, filterCallback=None, callbackArgs={}):
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
                    if filterCallback != None: # permanent implementation of the DDI hack
                        edgeCount = 0
                        for edge in self.getEdges(n1, n2):
                            if not filterCallback(edge, **callbackArgs):
                                edgeCount += 1
                        if edgeCount == 0:
                            self.__distances[n1][n2] = infinity
                        else:
                            self.__distances[n1][n2] = 1
                    elif False: # temporary hack for DDI
                        edgeCount = 0
                        for edge in self.getEdges(n1, n2):
                            if edge[2].get("type") != "conj_and":
                                edgeCount += 1
                        if edgeCount == 0:
                            self.__distances[n1][n2] = infinity
                        else:
                            self.__distances[n1][n2] = 1
                    else:
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
    
    def resetAnalyses(self):
        self.__nextInPath = None
        self.__distances = None
        self.__nextInPath = None
    
    def showAnalyses(self):
        if self.__nextInPath == None:
            self.FloydWarshall()
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
        if node2 in self.__matrix[node1]:
            edges = self.__matrix[node1][node2][:] # copied so that joining with reverse won't change original
        else:
            edges = []
        if (not directed) and self.__directed: # an undirected graph already has the reverse edges
            if node1 in self.__matrix[node2]:
                edges += self.__matrix[node2][node1]
        for edge in edges:
            if position < len(path)-1:
                allWalks.extend(self.__getWalks(path, position+1, walk + [edge], directed))
            else:
                allWalks.append(walk + [edge])
        return allWalks
    
    def toGraphviz(self, filename=None):
        s = "digraph SimpleGraph {\nnode [shape=box];\n"
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

def evaluate(code, repeats):
    import time
    tSum = 0.0
    for repeat in range(repeats):
        t0= time.clock()
        code()
        t= time.clock() - t0 # t is CPU seconds elapsed (floating point)
        tSum += t
    return tSum / repeats

def speedSimple():
    edges = [('st_2', 'st_1', 'split_1'), ('st_4', 'st_2', 'split_2'), ('st_4', 'st_3', 'split_3'), ('st_78', 'st_4', 'split_4'), ('st_10', 'st_7', 'split_5'), ('st_10', 'st_9', 'split_6'), ('st_13', 'st_10', 'split_7'), ('st_13', 'st_11', 'split_8'), ('st_13', 'st_12', 'split_9'), ('st_4', 'st_13', 'split_10'), ('st_15', 'st_14', 'split_11'), ('st_13', 'st_15', 'split_12'), ('st_20', 'st_17', 'split_13'), ('st_20', 'st_18', 'split_14'), ('st_20', 'st_19', 'split_15'), ('st_13', 'st_20', 'split_16'), ('st_27', 'st_24', 'split_17'), ('st_27', 'st_25', 'split_18'), ('st_27', 'st_26', 'split_19'), ('st_13', 'st_27', 'split_20'), ('st_27', 'st_28', 'split_21'), ('st_30', 'st_29', 'split_22'), ('st_28', 'st_30', 'split_23'), ('st_34', 'st_32', 'split_24'), ('st_34', 'st_33', 'split_25'), ('st_44', 'st_34', 'split_26'), ('st_34', 'st_36', 'split_27'), ('st_40', 'st_39', 'split_28'), ('st_34', 'st_40', 'split_29'), ('st_44', 'st_40', 'split_30'), ('st_40', 'st_42', 'split_31'), ('st_30', 'st_44', 'split_32'), ('st_66', 'st_47', 'split_33'), ('st_66', 'st_50', 'split_34'), ('st_57', 'st_54', 'split_35'), ('st_57', 'st_55', 'split_36'), ('st_57', 'st_56', 'split_37'), ('st_50', 'st_57', 'split_38'), ('st_63', 'st_61', 'split_39'), ('st_63', 'st_62', 'split_40'), ('st_66', 'st_63', 'split_41'), ('st_66', 'st_64', 'split_42'), ('st_66', 'st_65', 'split_43'), ('st_13', 'st_66', 'split_44'), ('st_66', 'st_67', 'split_45'), ('st_72', 'st_68', 'split_46'), ('st_72', 'st_69', 'split_47'), ('st_72', 'st_70', 'split_48'), ('st_72', 'st_71', 'split_49'), ('st_67', 'st_72', 'split_50'), ('st_13', 'st_75', 'split_51'), ('st_4', 'st_77', 'split_52'), ('st_82', 'st_80', 'split_53'), ('st_82', 'st_81', 'split_54'), ('st_78', 'st_82', 'split_55'), ('st_87', 'st_86', 'split_56'), ('st_82', 'st_87', 'split_57'), ('st_87', 'st_89', 'split_58'), ('st_95', 'st_92', 'split_59'), ('st_95', 'st_94', 'split_60'), ('st_100', 'st_95', 'split_61'), ('st_95', 'st_97', 'split_62'), ('st_95', 'st_99', 'split_63'), ('st_97', 'st_99', 'split_64'), ('st_78', 'st_100', 'split_65'), ('st_105', 'st_101', 'split_66'), ('st_105', 'st_102', 'split_67'), ('st_105', 'st_103', 'split_68'), ('st_105', 'st_104', 'split_69'), ('st_100', 'st_105', 'split_70'), ('st_108', 'st_107', 'split_71'), ('st_105', 'st_108', 'split_72'), ('st_114', 'st_111', 'split_73'), ('st_114', 'st_112', 'split_74'), ('st_114', 'st_113', 'split_75'), ('st_100', 'st_114', 'split_76'), ('st_105', 'st_114', 'split_77'), ('st_114', 'st_116', 'split_78'), ('st_120', 'st_116', 'split_79'), ('st_120', 'st_118', 'split_80'), ('st_120', 'st_119', 'split_81'), ('st_116', 'st_120', 'split_82'), ('st_126', 'st_122', 'split_83'), ('st_126', 'st_123', 'split_84'), ('st_126', 'st_124', 'split_85'), ('st_126', 'st_125', 'split_86'), ('st_120', 'st_126', 'split_87'), ('st_132', 'st_129', 'split_88'), ('st_132', 'st_131', 'split_89'), ('st_136', 'st_132', 'split_90'), ('st_135', 'st_134', 'split_91'), ('st_132', 'st_135', 'split_92'), ('st_78', 'st_136', 'split_93'), ('st_141', 'st_137', 'split_94'), ('st_141', 'st_138', 'split_95'), ('st_141', 'st_139', 'split_96'), ('st_141', 'st_140', 'split_97'), ('st_136', 'st_141', 'split_98'), ('st_144', 'st_141', 'split_99'), ('st_144', 'st_143', 'split_100'), ('st_141', 'st_144', 'split_101'), ('st_146', 'st_145', 'split_102'), ('st_144', 'st_146', 'split_103'), ('st_144', 'st_148', 'split_104'), ('st_78', 'st_152', 'split_105'), ('st_78', 'st_154', 'split_106'), ('st_164', 'st_155', 'split_107'), ('st_160', 'st_157', 'split_108'), ('st_160', 'st_158', 'split_109'), ('st_160', 'st_159', 'split_110'), ('st_155', 'st_160', 'split_111'), ('st_163', 'st_162', 'split_112'), ('st_164', 'st_163', 'split_113'), ('st_78', 'st_164', 'split_114'), ('st_166', 'st_165', 'split_115'), ('st_164', 'st_166', 'split_116'), ('st_169', 'st_168', 'split_117'), ('st_164', 'st_169', 'split_118'), ('st_166', 'st_169', 'split_119'), ('st_54', 'st_52', None), ('st_61', 'st_59', None), ('st_86', 'st_84', None)]
    g = Graph()
    g.addEdges(edges)

def speedNX():
    edges = [('st_2', 'st_1', 'split_1'), ('st_4', 'st_2', 'split_2'), ('st_4', 'st_3', 'split_3'), ('st_78', 'st_4', 'split_4'), ('st_10', 'st_7', 'split_5'), ('st_10', 'st_9', 'split_6'), ('st_13', 'st_10', 'split_7'), ('st_13', 'st_11', 'split_8'), ('st_13', 'st_12', 'split_9'), ('st_4', 'st_13', 'split_10'), ('st_15', 'st_14', 'split_11'), ('st_13', 'st_15', 'split_12'), ('st_20', 'st_17', 'split_13'), ('st_20', 'st_18', 'split_14'), ('st_20', 'st_19', 'split_15'), ('st_13', 'st_20', 'split_16'), ('st_27', 'st_24', 'split_17'), ('st_27', 'st_25', 'split_18'), ('st_27', 'st_26', 'split_19'), ('st_13', 'st_27', 'split_20'), ('st_27', 'st_28', 'split_21'), ('st_30', 'st_29', 'split_22'), ('st_28', 'st_30', 'split_23'), ('st_34', 'st_32', 'split_24'), ('st_34', 'st_33', 'split_25'), ('st_44', 'st_34', 'split_26'), ('st_34', 'st_36', 'split_27'), ('st_40', 'st_39', 'split_28'), ('st_34', 'st_40', 'split_29'), ('st_44', 'st_40', 'split_30'), ('st_40', 'st_42', 'split_31'), ('st_30', 'st_44', 'split_32'), ('st_66', 'st_47', 'split_33'), ('st_66', 'st_50', 'split_34'), ('st_57', 'st_54', 'split_35'), ('st_57', 'st_55', 'split_36'), ('st_57', 'st_56', 'split_37'), ('st_50', 'st_57', 'split_38'), ('st_63', 'st_61', 'split_39'), ('st_63', 'st_62', 'split_40'), ('st_66', 'st_63', 'split_41'), ('st_66', 'st_64', 'split_42'), ('st_66', 'st_65', 'split_43'), ('st_13', 'st_66', 'split_44'), ('st_66', 'st_67', 'split_45'), ('st_72', 'st_68', 'split_46'), ('st_72', 'st_69', 'split_47'), ('st_72', 'st_70', 'split_48'), ('st_72', 'st_71', 'split_49'), ('st_67', 'st_72', 'split_50'), ('st_13', 'st_75', 'split_51'), ('st_4', 'st_77', 'split_52'), ('st_82', 'st_80', 'split_53'), ('st_82', 'st_81', 'split_54'), ('st_78', 'st_82', 'split_55'), ('st_87', 'st_86', 'split_56'), ('st_82', 'st_87', 'split_57'), ('st_87', 'st_89', 'split_58'), ('st_95', 'st_92', 'split_59'), ('st_95', 'st_94', 'split_60'), ('st_100', 'st_95', 'split_61'), ('st_95', 'st_97', 'split_62'), ('st_95', 'st_99', 'split_63'), ('st_97', 'st_99', 'split_64'), ('st_78', 'st_100', 'split_65'), ('st_105', 'st_101', 'split_66'), ('st_105', 'st_102', 'split_67'), ('st_105', 'st_103', 'split_68'), ('st_105', 'st_104', 'split_69'), ('st_100', 'st_105', 'split_70'), ('st_108', 'st_107', 'split_71'), ('st_105', 'st_108', 'split_72'), ('st_114', 'st_111', 'split_73'), ('st_114', 'st_112', 'split_74'), ('st_114', 'st_113', 'split_75'), ('st_100', 'st_114', 'split_76'), ('st_105', 'st_114', 'split_77'), ('st_114', 'st_116', 'split_78'), ('st_120', 'st_116', 'split_79'), ('st_120', 'st_118', 'split_80'), ('st_120', 'st_119', 'split_81'), ('st_116', 'st_120', 'split_82'), ('st_126', 'st_122', 'split_83'), ('st_126', 'st_123', 'split_84'), ('st_126', 'st_124', 'split_85'), ('st_126', 'st_125', 'split_86'), ('st_120', 'st_126', 'split_87'), ('st_132', 'st_129', 'split_88'), ('st_132', 'st_131', 'split_89'), ('st_136', 'st_132', 'split_90'), ('st_135', 'st_134', 'split_91'), ('st_132', 'st_135', 'split_92'), ('st_78', 'st_136', 'split_93'), ('st_141', 'st_137', 'split_94'), ('st_141', 'st_138', 'split_95'), ('st_141', 'st_139', 'split_96'), ('st_141', 'st_140', 'split_97'), ('st_136', 'st_141', 'split_98'), ('st_144', 'st_141', 'split_99'), ('st_144', 'st_143', 'split_100'), ('st_141', 'st_144', 'split_101'), ('st_146', 'st_145', 'split_102'), ('st_144', 'st_146', 'split_103'), ('st_144', 'st_148', 'split_104'), ('st_78', 'st_152', 'split_105'), ('st_78', 'st_154', 'split_106'), ('st_164', 'st_155', 'split_107'), ('st_160', 'st_157', 'split_108'), ('st_160', 'st_158', 'split_109'), ('st_160', 'st_159', 'split_110'), ('st_155', 'st_160', 'split_111'), ('st_163', 'st_162', 'split_112'), ('st_164', 'st_163', 'split_113'), ('st_78', 'st_164', 'split_114'), ('st_166', 'st_165', 'split_115'), ('st_164', 'st_166', 'split_116'), ('st_169', 'st_168', 'split_117'), ('st_164', 'st_169', 'split_118'), ('st_166', 'st_169', 'split_119'), ('st_54', 'st_52', None), ('st_61', 'st_59', None), ('st_86', 'st_84', None)]
    g = NX10.MultiDiGraph()
    for edge in edges:
        g.add_edge(edge[0], edge[1], data=edge[2])
        
if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    if True:
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
        print "undir nodes", u.nodes
        print "undir edges", u.edges
        print u.showAnalyses()
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
        g.addEdges([('st_2', 'st_1', 'split_1'), ('st_4', 'st_2', 'split_2'), ('st_4', 'st_3', 'split_3'), ('st_78', 'st_4', 'split_4'), ('st_10', 'st_7', 'split_5'), ('st_10', 'st_9', 'split_6'), ('st_13', 'st_10', 'split_7'), ('st_13', 'st_11', 'split_8'), ('st_13', 'st_12', 'split_9'), ('st_4', 'st_13', 'split_10'), ('st_15', 'st_14', 'split_11'), ('st_13', 'st_15', 'split_12'), ('st_20', 'st_17', 'split_13'), ('st_20', 'st_18', 'split_14'), ('st_20', 'st_19', 'split_15'), ('st_13', 'st_20', 'split_16'), ('st_27', 'st_24', 'split_17'), ('st_27', 'st_25', 'split_18'), ('st_27', 'st_26', 'split_19'), ('st_13', 'st_27', 'split_20'), ('st_27', 'st_28', 'split_21'), ('st_30', 'st_29', 'split_22'), ('st_28', 'st_30', 'split_23'), ('st_34', 'st_32', 'split_24'), ('st_34', 'st_33', 'split_25'), ('st_44', 'st_34', 'split_26'), ('st_34', 'st_36', 'split_27'), ('st_40', 'st_39', 'split_28'), ('st_34', 'st_40', 'split_29'), ('st_44', 'st_40', 'split_30'), ('st_40', 'st_42', 'split_31'), ('st_30', 'st_44', 'split_32'), ('st_66', 'st_47', 'split_33'), ('st_66', 'st_50', 'split_34'), ('st_57', 'st_54', 'split_35'), ('st_57', 'st_55', 'split_36'), ('st_57', 'st_56', 'split_37'), ('st_50', 'st_57', 'split_38'), ('st_63', 'st_61', 'split_39'), ('st_63', 'st_62', 'split_40'), ('st_66', 'st_63', 'split_41'), ('st_66', 'st_64', 'split_42'), ('st_66', 'st_65', 'split_43'), ('st_13', 'st_66', 'split_44'), ('st_66', 'st_67', 'split_45'), ('st_72', 'st_68', 'split_46'), ('st_72', 'st_69', 'split_47'), ('st_72', 'st_70', 'split_48'), ('st_72', 'st_71', 'split_49'), ('st_67', 'st_72', 'split_50'), ('st_13', 'st_75', 'split_51'), ('st_4', 'st_77', 'split_52'), ('st_82', 'st_80', 'split_53'), ('st_82', 'st_81', 'split_54'), ('st_78', 'st_82', 'split_55'), ('st_87', 'st_86', 'split_56'), ('st_82', 'st_87', 'split_57'), ('st_87', 'st_89', 'split_58'), ('st_95', 'st_92', 'split_59'), ('st_95', 'st_94', 'split_60'), ('st_100', 'st_95', 'split_61'), ('st_95', 'st_97', 'split_62'), ('st_95', 'st_99', 'split_63'), ('st_97', 'st_99', 'split_64'), ('st_78', 'st_100', 'split_65'), ('st_105', 'st_101', 'split_66'), ('st_105', 'st_102', 'split_67'), ('st_105', 'st_103', 'split_68'), ('st_105', 'st_104', 'split_69'), ('st_100', 'st_105', 'split_70'), ('st_108', 'st_107', 'split_71'), ('st_105', 'st_108', 'split_72'), ('st_114', 'st_111', 'split_73'), ('st_114', 'st_112', 'split_74'), ('st_114', 'st_113', 'split_75'), ('st_100', 'st_114', 'split_76'), ('st_105', 'st_114', 'split_77'), ('st_114', 'st_116', 'split_78'), ('st_120', 'st_116', 'split_79'), ('st_120', 'st_118', 'split_80'), ('st_120', 'st_119', 'split_81'), ('st_116', 'st_120', 'split_82'), ('st_126', 'st_122', 'split_83'), ('st_126', 'st_123', 'split_84'), ('st_126', 'st_124', 'split_85'), ('st_126', 'st_125', 'split_86'), ('st_120', 'st_126', 'split_87'), ('st_132', 'st_129', 'split_88'), ('st_132', 'st_131', 'split_89'), ('st_136', 'st_132', 'split_90'), ('st_135', 'st_134', 'split_91'), ('st_132', 'st_135', 'split_92'), ('st_78', 'st_136', 'split_93'), ('st_141', 'st_137', 'split_94'), ('st_141', 'st_138', 'split_95'), ('st_141', 'st_139', 'split_96'), ('st_141', 'st_140', 'split_97'), ('st_136', 'st_141', 'split_98'), ('st_144', 'st_141', 'split_99'), ('st_144', 'st_143', 'split_100'), ('st_141', 'st_144', 'split_101'), ('st_146', 'st_145', 'split_102'), ('st_144', 'st_146', 'split_103'), ('st_144', 'st_148', 'split_104'), ('st_78', 'st_152', 'split_105'), ('st_78', 'st_154', 'split_106'), ('st_164', 'st_155', 'split_107'), ('st_160', 'st_157', 'split_108'), ('st_160', 'st_158', 'split_109'), ('st_160', 'st_159', 'split_110'), ('st_155', 'st_160', 'split_111'), ('st_163', 'st_162', 'split_112'), ('st_164', 'st_163', 'split_113'), ('st_78', 'st_164', 'split_114'), ('st_166', 'st_165', 'split_115'), ('st_164', 'st_166', 'split_116'), ('st_169', 'st_168', 'split_117'), ('st_164', 'st_169', 'split_118'), ('st_166', 'st_169', 'split_119'), ('st_54', 'st_52', None), ('st_61', 'st_59', None), ('st_86', 'st_84', None)])
        #print "Paths 'st_14'->'st_6'", g.getPaths('st_14','st_6')
        u = g.toUndirected()
        #print "Undirected Paths 'st_14'->'st_6'", u.getPaths('st_14','st_6')
        #print "Undirected Paths 'st_14'->'st_11'", u.getPaths('st_14','st_11')
        #print "Walks", g.getWalks(['st_14', 'st_1', 'st_11'])
        #print "Walks", g.getWalks(['st_14', 'st_1', 'st_11'])
        #print "Walks", g.getWalks(['st_14', 'st_1', 'st_11'])
        #print u.showAnalyses()
        u.toGraphviz("vis.gv")
    if True:
        import timeit
        edges = [('st_2', 'st_1', 'split_1'), ('st_4', 'st_2', 'split_2'), ('st_4', 'st_3', 'split_3'), ('st_78', 'st_4', 'split_4'), ('st_10', 'st_7', 'split_5'), ('st_10', 'st_9', 'split_6'), ('st_13', 'st_10', 'split_7'), ('st_13', 'st_11', 'split_8'), ('st_13', 'st_12', 'split_9'), ('st_4', 'st_13', 'split_10'), ('st_15', 'st_14', 'split_11'), ('st_13', 'st_15', 'split_12'), ('st_20', 'st_17', 'split_13'), ('st_20', 'st_18', 'split_14'), ('st_20', 'st_19', 'split_15'), ('st_13', 'st_20', 'split_16'), ('st_27', 'st_24', 'split_17'), ('st_27', 'st_25', 'split_18'), ('st_27', 'st_26', 'split_19'), ('st_13', 'st_27', 'split_20'), ('st_27', 'st_28', 'split_21'), ('st_30', 'st_29', 'split_22'), ('st_28', 'st_30', 'split_23'), ('st_34', 'st_32', 'split_24'), ('st_34', 'st_33', 'split_25'), ('st_44', 'st_34', 'split_26'), ('st_34', 'st_36', 'split_27'), ('st_40', 'st_39', 'split_28'), ('st_34', 'st_40', 'split_29'), ('st_44', 'st_40', 'split_30'), ('st_40', 'st_42', 'split_31'), ('st_30', 'st_44', 'split_32'), ('st_66', 'st_47', 'split_33'), ('st_66', 'st_50', 'split_34'), ('st_57', 'st_54', 'split_35'), ('st_57', 'st_55', 'split_36'), ('st_57', 'st_56', 'split_37'), ('st_50', 'st_57', 'split_38'), ('st_63', 'st_61', 'split_39'), ('st_63', 'st_62', 'split_40'), ('st_66', 'st_63', 'split_41'), ('st_66', 'st_64', 'split_42'), ('st_66', 'st_65', 'split_43'), ('st_13', 'st_66', 'split_44'), ('st_66', 'st_67', 'split_45'), ('st_72', 'st_68', 'split_46'), ('st_72', 'st_69', 'split_47'), ('st_72', 'st_70', 'split_48'), ('st_72', 'st_71', 'split_49'), ('st_67', 'st_72', 'split_50'), ('st_13', 'st_75', 'split_51'), ('st_4', 'st_77', 'split_52'), ('st_82', 'st_80', 'split_53'), ('st_82', 'st_81', 'split_54'), ('st_78', 'st_82', 'split_55'), ('st_87', 'st_86', 'split_56'), ('st_82', 'st_87', 'split_57'), ('st_87', 'st_89', 'split_58'), ('st_95', 'st_92', 'split_59'), ('st_95', 'st_94', 'split_60'), ('st_100', 'st_95', 'split_61'), ('st_95', 'st_97', 'split_62'), ('st_95', 'st_99', 'split_63'), ('st_97', 'st_99', 'split_64'), ('st_78', 'st_100', 'split_65'), ('st_105', 'st_101', 'split_66'), ('st_105', 'st_102', 'split_67'), ('st_105', 'st_103', 'split_68'), ('st_105', 'st_104', 'split_69'), ('st_100', 'st_105', 'split_70'), ('st_108', 'st_107', 'split_71'), ('st_105', 'st_108', 'split_72'), ('st_114', 'st_111', 'split_73'), ('st_114', 'st_112', 'split_74'), ('st_114', 'st_113', 'split_75'), ('st_100', 'st_114', 'split_76'), ('st_105', 'st_114', 'split_77'), ('st_114', 'st_116', 'split_78'), ('st_120', 'st_116', 'split_79'), ('st_120', 'st_118', 'split_80'), ('st_120', 'st_119', 'split_81'), ('st_116', 'st_120', 'split_82'), ('st_126', 'st_122', 'split_83'), ('st_126', 'st_123', 'split_84'), ('st_126', 'st_124', 'split_85'), ('st_126', 'st_125', 'split_86'), ('st_120', 'st_126', 'split_87'), ('st_132', 'st_129', 'split_88'), ('st_132', 'st_131', 'split_89'), ('st_136', 'st_132', 'split_90'), ('st_135', 'st_134', 'split_91'), ('st_132', 'st_135', 'split_92'), ('st_78', 'st_136', 'split_93'), ('st_141', 'st_137', 'split_94'), ('st_141', 'st_138', 'split_95'), ('st_141', 'st_139', 'split_96'), ('st_141', 'st_140', 'split_97'), ('st_136', 'st_141', 'split_98'), ('st_144', 'st_141', 'split_99'), ('st_144', 'st_143', 'split_100'), ('st_141', 'st_144', 'split_101'), ('st_146', 'st_145', 'split_102'), ('st_144', 'st_146', 'split_103'), ('st_144', 'st_148', 'split_104'), ('st_78', 'st_152', 'split_105'), ('st_78', 'st_154', 'split_106'), ('st_164', 'st_155', 'split_107'), ('st_160', 'st_157', 'split_108'), ('st_160', 'st_158', 'split_109'), ('st_160', 'st_159', 'split_110'), ('st_155', 'st_160', 'split_111'), ('st_163', 'st_162', 'split_112'), ('st_164', 'st_163', 'split_113'), ('st_78', 'st_164', 'split_114'), ('st_166', 'st_165', 'split_115'), ('st_164', 'st_166', 'split_116'), ('st_169', 'st_168', 'split_117'), ('st_164', 'st_169', 'split_118'), ('st_166', 'st_169', 'split_119'), ('st_54', 'st_52', None), ('st_61', 'st_59', None), ('st_86', 'st_84', None)]
        import Graph.networkx_v10rc1 as NX10
        
        print "SimpleGraph: %.4f" % evaluate(speedSimple, 100)
        print "NXGraph: %.4f" % evaluate(speedNX, 100)

        # With full adjacency matrix:
        #
        # jari@jari-laptop:~/cvs_checkout/JariSandbox/ComplexPPI/Source/Core$ python SimpleGraph.py
        # Found Psyco, using
        # SimpleGraph: 0.0126
        # NXGraph: 0.0011
        #
        # With adjancency matrix that doesn't have all keys:
        #
        # jari@jari-laptop:~/cvs_checkout/JariSandbox/ComplexPPI/Source/Core$ python SimpleGraph.py
        # Found Psyco, using
        # SimpleGraph: 0.0017
        # NXGraph: 0.0010        
        #
        # After replacing addEdgeTuple's "not edge in self.edges" with
        # new method self.hasEdgeTuple(edge)
        #
        # jari@jari-laptop:~/cvs_checkout/JariSandbox/ComplexPPI/Source/Core$ python SimpleGraph.py
        # Found Psyco, using
        # SimpleGraph: 0.0005
        # NXGraph: 0.0010
    
