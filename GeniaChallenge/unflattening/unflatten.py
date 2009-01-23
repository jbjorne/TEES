import sys
import networkx as NX
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class Increment:
    """
    Increment instance gives all non-negative integers starting from
    zero. This is used to assign running ids for elements.
    """
    def __init__(self):
        self.cur = -1

    def get(self):
        """
        Returns the next id.

        @return: id
        @rtype: string representing an integer
        """
        self.cur += 1
        return(str(self.cur))

class Unflattener:
    def __init__(self,document):
        self.document = document

    def unflatten(self):
        G = NX.XDiGraph()
        counter = Increment()
        entities = dict( [(x.attrib['id'],x) for x in
                          self.document.getiterator('entity')] )
        for event in self.document.getiterator('interaction'):
            e1 = entities[event.attrib['e1']]
            e2 = entities[event.attrib['e2']]
            G.add_edge(e1,e2,event)

        def getGrouping(node):
            # NOTE: this function does not yet consider task 2
            uid = node.attrib['id']
            t = entities[uid].attrib['type']
            edges = G.out_edges(node)
            if t in ['Gene_expression','Transcription',
                     'Translation','Protein_catabolism']:
                return([[e] for e in edges])
            elif t=='Localization':
                return([[e] for e in edges])
            elif t=='Binding':
                pass
            elif t=='Phosphorylation':
                return([[e] for e in edges])
            elif t in ['Regulation','Positive_regulation',
                       'Negative_regulation']:
                pass
            else:
                sys.stderr.write("Invalid event type: %s"%t)
            return([edges])

        unprocessed_nodes = set([x for x in G.nodes() if not G.out_edges(n)])
        while unprocessed_nodes:
            next_nodes = set()
            for current in unprocessed_nodes:
                if G.out_edges(current):
                    groups = self.getGrouping(current)
                    for edges in groups:
                        newN = ET.Element('entity',current.attrib)
                        newId = newN.attrib['id']+'.E'+counter.get()
                        newN.attrib['id'] = newId
                        G.add_node(newN)
                        for e in edges:
                            newE = ET.Element('interaction',e[2].attrib)
                            newE.attrib['e1'] = newId
                            G.add_edge(newN,e[1],newE)
                        for e in G.in_edges(current):
                            newE = ET.Element('interaction',e[2].attrib)
                            newE.attrib['e2'] = newId
                            G.add_edge(e[0],newN,newE)
                    G.remove_node(current)
                next_nodes.update(set(G.in_neighbors(current)))
            # ensure that nodes-to-be-processed have only out-neighbors
            # that have already been processed
            for x in next_nodes:
                for y in next_nodes:
                    if NX.shortest_path(G,x,y) and not x==y:
                        next_nodes.remove(x)
            unprocessed_nodes = next_nodes



                    




        all_entities = ['Gene_expression','Transcription',
                        'Translation','Protein_catabolism',
                        'Localization','Binding','Phosphorylation',
                        'Regulation','Positive_regulation',
                        'Negative_regulation','Protein']
