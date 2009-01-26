import sys
import networkx as NX
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

#         all_entities = ['Gene_expression','Transcription',
#                         'Translation','Protein_catabolism',
#                         'Localization','Binding','Phosphorylation',
#                         'Regulation','Positive_regulation',
#                         'Negative_regulation','Protein']

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
        self.graph = self.makeGraph()

    def makeGraph(self):
        G = NX.XDiGraph()
        entities = dict( [(x.attrib['id'],x) for x in
                          self.document.getiterator('entity')] )
        for event in self.document.getiterator('interaction'):
            e1 = entities[event.attrib['e1']]
            e2 = entities[event.attrib['e2']]
            G.add_edge(e1,e2,event)
        return(G)

    def analyse(self):
        counter = Increment()
        G = self.graph

        def getGrouping(node):
            # NOTE: this function does not yet consider task 2
            uid = node.attrib['id']
            t = node.attrib['type']
            edges = G.out_edges(node)
            if t in ['Gene_expression','Transcription',
                     'Translation','Protein_catabolism']:
                return([[e] for e in edges])
            elif t=='Localization':
                return([[e] for e in edges])
            elif t=='Binding':
                left,right = getLinearGrouping(node,edges)
                # simple approach that uses only linear order
                # (probably makes many mistakes)
                return([(le,ri) for le in left for ri in right])
            elif t=='Phosphorylation':
                return([[e] for e in edges])
            elif t in ['Regulation','Positive_regulation',
                       'Negative_regulation']:
                cause = [x for x in edges if
                         x[2].attrib['type'].startswith('Cause')]
                theme = [x for x in edges if
                         x[2].attrib['type'].startswith('Theme')]
                left,right = getLinearGrouping(node,edges)
                # simple approach that does not use linear order or syntax
                return([(ca,th) for ca in cause for th in theme])
            else:
                sys.stderr.write("Invalid event type: %s"%t)
            return([edges])

        def getLinearGrouping(node,edges):
            trigger_start = int(node.attrib['charOffset'].split('-')[0])
            result = ([],[])
            for e in edges:
                e_tmp = int(e[1].attrib['charOffset'].split('-')[0])
                # THIS SHOULD BE CHANGED TO SOMETHING BETTER!
                if e_tmp<trigger_start:
                    result[0].append(e)
                elif e_tmp>trigger_start:
                    result[1].append(e)
                else:
                    sys.stderr.write("Entities %s and %s start at the same offset\n"%(node.attrib['id'],e[1].attrib['id']))
            return(result)

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

    def unflatten(self):
        for elem in self.document:
            self.document.remove(elem)
        for node in self.graph.nodes():
            self.document.add(node)
        for edge in self.graph.edges():
            self.document.add(edge[2])



def interface(optionArgs=sys.argv[1:]):
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nGenia shared task specific unflattening.")
    op.add_option("-i", "--infile",
                  dest="infile",
                  help="Input file (gifxml)",
                  metavar="FILE")
    op.add_option("-o", "--outfile",
                  dest="outfile",
                  help="Output file (gifxml)",
                  metavar="FILE")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.infile:
        print "Please specify the input file."
        quit = True
    if not options.outfile:
        print "Please specify the output file."
        quit = True
    if quit:
        op.print_help()
        return(False)

    corpus = ET.parse(options.infile)
    for document in corpus.getroot().findall('document'):
        unflattener = Unflattener(document)
        unflattener.analyse()
        unflattener.unflatten()
    corpus.write(options.outfile)

if __name__=="__main__":
    interface()
