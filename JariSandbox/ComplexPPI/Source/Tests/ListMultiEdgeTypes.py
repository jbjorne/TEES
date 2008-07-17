import networkx as NX

if __name__=="__main__":
    print >> sys.stderr, "Loading corpus file", options.input
    corpusTree = ET.parse(options.input)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    
    # Make sentence graphs
    sentences = []
    counter = ProgressCounter(len(corpusElements.sentences))
    for sentence in corpusElements.sentences:
        counter.update(1, "Making sentence graphs: ")
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        graph.mapInteractions(sentence.entities, sentence.interactions)
        sentences.append( [graph,None,None] )
        sentences[-1][1] = graph.dependencyGraph.to_undirected()
    
    for sentence in sentences:
        tokens = sentence[0].tokens
        for i in range(len(tokens)):
            for j in range(i+1,len(tokens)-1):
                path = NX.shortest_path(sentence[1], tokens[i], tokens[j])