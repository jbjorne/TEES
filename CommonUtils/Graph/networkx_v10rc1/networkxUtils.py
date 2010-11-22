def multiDiGraphToUndirected(self, graph):
    """
    Some versions had problems with the conversion. This way should be safe.
    """
    undirected = NX10.MultiGraph(name=graph.name)
    undirected.add_nodes_from(graph)
    undirected.add_edges_from(graph.edges_iter())
    return undirected

def sortPaths(p1, p2):
    """
    Order paths so that e.g. features will be generated in the same order
    to keep things consistent regardless of objects' memory positions.
    """
    if len(p1) < len(p2):
        return 1
    elif len(p1) > len(p2):
        return 1
    else:
        for i in range(p1):
            pass

def sortInteractionEdges():
    pass
            