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

def indent(elem, level=0):
    """
    In-place indentation of XML (in cElementTree.Element object).
    This function was provided by Filip Salomonsson. See
    http://infix.se/2007/02/06/gentlemen-indent-your-xml.
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

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

class Analyser:
    @classmethod
    def transformOffset(cls,string):
        return([int(x) for x in string.split('-')])

    @classmethod
    def collectTokens(cls,sentence):
        tmp = sentence.find('sentenceanalyses')
        tmp2 = [x for x in tmp.getiterator('tokenization')
                if x.attrib['tokenizer']=='Charniak-Lease'][0]
        tokens = dict( [(x.attrib['id'],x)
                        for x in tmp2.findall('token')] )
        return(tokens)

    @classmethod
    def findTokens(cls,tokens,offset):
        return( [k for k,v in tokens.items()
                 if ((offset[0]>=v[0] and offset[0]<=v[1]) or
                     (offset[1]>=v[0] and offset[1]<=v[1]) or
                     (offset[0]<=v[0] and offset[1]>=v[1]))] )

    @classmethod
    def mapEntitiesToTokens(cls,document,tokens):
        e2t = {}
        for sentence in document.findall('sentence'):
            toks = dict( [(k,Analyser.transformOffset(v.attrib['charOffset']))
                          for k,v in tokens[sentence].items()] )
            for x in sentence.findall('entity'):
                uid = x.attrib['id']
                offset = Analyser.transformOffset(x.attrib['charOffset'])
                for y in Analyser.findTokens(toks,offset):
                    if not e2t.has_key(uid):
                        e2t[uid] = []
                    e2t[uid].append(y)
        return(e2t)

    @classmethod
    def makeDepG(cls,sentence):
        tmp = sentence.find('sentenceanalyses')
        tmp2 = [x for x in tmp.getiterator('parse')
                if x.attrib['tokenizer']=='Charniak-Lease'][0]
        G = NX.XDiGraph()
        for x in tmp2.findall('dependency'):
            G.add_edge(x.attrib['t1'],x.attrib['t2'],x.attrib['type'])
        return(G)

    @classmethod
    def makeSemG(cls,document):
        entities = dict( [(x.attrib['id'],x) for x in
                          document.getiterator('entity')] )
        G = NX.XDiGraph()
        for event in document.getiterator('interaction'):
            # ignore negative pairs
            # WHICH SHOULD BE THERE IN THE FIRST PLACE!
            if event.attrib['type']=='neg':
                continue
            e1 = entities[event.attrib['e1']]
            e2 = entities[event.attrib['e2']]
            G.add_edge(e1,e2,event)
        return(G)

    @classmethod
    def findSentenceId(cls,element):
        # THIS IS DATA SPECIFIC SOLUTION!
        return('.'.join(element.attrib['id'].split('.')[:3]))



class Unflattener:
    def __init__(self,document,perfect):
        self.document = document
        self.perfect = perfect
        self.sentences = dict( [(x.attrib['id'],x)
                                for x in self.document.findall('sentence')] )
        # contains entity and interaction elements
        self.semG = Analyser.makeSemG(self.document)
        self.loners = [x for x in self.document.getiterator('entity')
                       if not self.semG.has_node(x)]
        # tokens and dep.graphs are sentence-specific because
        # TOKEN IDS ARE NOT HIERARCHICAL
        self.tokens = dict( [(x,Analyser.collectTokens(x))
                             for x in self.document.findall('sentence')] )
        self.mapping = Analyser.mapEntitiesToTokens(self.document,self.tokens)
        self.depDiGs = dict( [(x,Analyser.makeDepG(x))
                              for x in self.document.findall('sentence')] )
        self.depGs = dict( [(x,y.to_undirected())
                            for x,y in self.depDiGs.items()] )

    def analyse(self):
        def getCoordGrouping(edges):
            def coordPath(this,target):
                if depG.has_node(this) and depG.has_node(target):
                    paths1 = [NX.shortest_path(depG,x,this)
                              for x in parentTokens
                              if depG.has_node(x)]
                    paths2 = [NX.shortest_path(depG,x,target)
                              for x in parentTokens
                              if depG.has_node(x)]
                    # same coordination group if there is a pair of
                    # shortest paths from event that start with the same edge
                    # and this edge is not between the tokens of the event
                    start1 = set( [depG.get_edge(p[0],p[1]) for p in paths1
                                   if (p and
                                       len(p)>=2 and
                                       not p[1] in parentTokens)] )
                    start2 = set( [depG.get_edge(p[0],p[1]) for p in paths2
                                   if (p and
                                       len(p)>=2 and
                                       not p[1] in parentTokens)] )
                    return(start1.intersection(start2))
                return(False)
            def connected(e1,e2):
                # do not continue if not within sentence
                if self.mapping.has_key(e1):
                    for t1 in self.mapping[e1]:
                        # do not continue if not within sentence
                        if self.mapping.has_key(e2):
                            for t2 in self.mapping[e2]:
                                if coordPath(t1,t2):
                                    return(True)
                return(False)

            if not edges:
                return([])
            # where does the parent node belong to?
            sentence = self.sentences[Analyser.findSentenceId(edges[0][0])]
            depG = self.depGs[sentence]
            edgemap = dict( [(x[2].attrib['e2'],x) for x in edges] )
            connG = NX.Graph()
            for x in edgemap.values():
                connG.add_node(x)
            pid = edges[0][2].attrib['e1']
            parentTokens = []
            if self.mapping.has_key(pid):
                parentTokens = self.mapping[pid]
            for e1 in edgemap.keys():
                for e2 in edgemap.keys():
                    if not e1==e2:
                        if connected(e1,e2):
                            connG.add_edge(edgemap[e1],edgemap[e2])
            return(NX.connected_components(connG))

        def getGrouping(node):
            # NOTE: this function does not yet consider task 2
            uid = node.attrib['id']
            t = node.attrib['type']
            # 'neg' edges are not considered and will be
            # removed from the final xml
            edges = [x for x in self.semG.out_edges(node)
                     if not x[2].attrib['type']=='neg']
            if t in ['Gene_expression','Transcription',
                     'Translation','Protein_catabolism']:
                result = [[e] for e in edges]
#                #sys.stderr.write("Splitting %s (%s) into %s - %s\n"%(uid,t,
#                                                                     len(result),
#                                                                     [[y[2].attrib['id']
#                                                                       for y in x]
#                                                                      for x in result]))
                return(result)
            elif t=='Localization':
                result = [[e] for e in edges]
#                #sys.stderr.write("Splitting %s (%s) into %s - %s\n"%(uid,t,
#                                                                     len(result),
#                                                                     [[y[2].attrib['id']
#                                                                       for y in x]
#                                                                      for x in result]))
                return(result)
            elif t=='Binding':
                # Binding is not perfectly solvable
                if self.perfect:
                    #sys.stderr.write("Skipping %s (%s)\n"%(uid,t))
                    return([edges])
                # simple approach that uses only linear order
                # (probably makes many mistakes)
                # left,right = getLinearGrouping(node,edges)
                # return([(le,ri) for le in left for ri in right])
                groups = getCoordGrouping(edges)
                if len(groups)==1:
                    # data suggests that regardless of number of members
                    # in the group, the binding should be split
                    # (cases of >2 are very rare)
                    # (the decision to split events with 2 members is about
                    #  1:1 but splitting is still slightly favoured)
                    result = [[e] for e in edges]
#                    #sys.stderr.write("Splitting %s (%s) into %s - %s\n"%(uid,t,
#                                                                         len(result),
#                                                                         [[y[2].attrib['id']
#                                                                           for y in x]
#                                                                          for x in result]))
                    return(result)
                else:
                    # two groups should be split to pairwise combinations
                    # (can respectively be ignored?)
                    # events with more than two proteins are rare
                    # so three or more groups should be treated in a
                    # pairwise manner
                    result = []
                    while groups:
                        g1 = groups.pop()
                        result.extend( [(e1,e2)
                                        for g2 in groups
                                        for e1 in g1
                                        for e2 in g2] )
                    #sys.stderr.write("Generating inter-group pairs for %s (%s) - %s\n"%(uid,t,[[y[2].attrib['id'] for y in x] for x in result]))
                    return(result)
            elif t=='Phosphorylation':
                result = [[e] for e in edges]
#                #sys.stderr.write("Splitting %s (%s) into %s - %s\n"%(uid,t,
#                                                                     len(result),
#                                                                     [[y[2].attrib['id']
#                                                                       for y in x]
#                                                                      for x in result]))
                return(result)
            elif t in ['Regulation','Positive_regulation',
                       'Negative_regulation']:
                # Regulation is not perfectly solvable
                # but for now there no better way than the baseline
                # (can respectively be ignored?)
                cause = [x for x in edges if
                         x[2].attrib['type'].startswith('Cause')]
                theme = [x for x in edges if
                         x[2].attrib['type'].startswith('Theme')]
                if cause and theme:
                    result = [(ca,th) for ca in cause for th in theme]
                    #sys.stderr.write("Generating Cause-Theme combinations for %s (%s) - %s\n"%(uid,t,[[y[2].attrib['id'] for y in x] for x in result]))
                    return(result)
                else:
                    result = [[e] for e in edges]
#                    #sys.stderr.write("Splitting %s (%s) into %s - %s\n"%(uid,t,
#                                                                       len(result),
#                                                                       [[y[2].attrib['id']
#                                                                         for y in x]
#                                                                        for x in result]))
                    return(result)
            else:
                sys.stderr.write("Invalid event type: %s\n"%t)
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

        counter = Increment()
        unprocessed_nodes = set([x for x in self.semG.nodes()
                                 if not self.semG.out_edges(x)])
        while unprocessed_nodes:
            next_nodes = set()
            for current in unprocessed_nodes:
                next_nodes.update(set(self.semG.in_neighbors(current)))
                if self.semG.out_edges(current):
                    groups = getGrouping(current)
                    for edges in groups:
                        evid = counter.get()
                        newN = ET.Element('entity',current.attrib)
                        newId = newN.attrib['id']+'.E'+evid
                        newN.attrib['id'] = newId
                        self.semG.add_node(newN)
                        for e in edges:
                            newE = ET.Element('interaction',e[2].attrib)
                            newEid = newE.attrib['id']+'.E'+evid
                            newE.attrib['id'] = newEid
                            newE.attrib['e1'] = newId
                            self.semG.add_edge(newN,e[1],newE)
                        for e in self.semG.in_edges(current):
                            newE = ET.Element('interaction',e[2].attrib)
                            newEid = newE.attrib['id']+'.E'+evid
                            newE.attrib['id'] = newEid
                            newE.attrib['e2'] = newId
                            self.semG.add_edge(e[0],newN,newE)
                    self.semG.delete_node(current)
            # ensure that nodes-to-be-processed have only out-neighbors
            # that have already been processed
            removable = set()
            for x in next_nodes:
                for y in next_nodes:
                    if NX.shortest_path(self.semG,x,y) and not x==y:
                        removable.add(x)
            unprocessed_nodes = next_nodes - removable

    def unflatten(self):
        for sentence in self.document.findall('sentence'):
            for elem in sentence.findall('entity'):
                sentence.remove(elem)
            for elem in sentence.findall('interaction'):
                sentence.remove(elem)
        for edge in self.semG.edges():
            sentence = self.sentences[Analyser.findSentenceId(edge[2])]
            sentence.insert(0,edge[2])
        for node in self.loners:
            sentence = self.sentences[Analyser.findSentenceId(node)]
            sentence.insert(0,node)
        for node in self.semG.nodes():
            sentence = self.sentences[Analyser.findSentenceId(node)]
            sentence.insert(0,node)



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
    op.add_option("-p", "--perfect",
                  dest="perfect",
                  help="Process only those event which can be perfectly solved",
                  action="store_true",
                  default=False)
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
        #sys.stderr.write("Unflattening document %s\n"%document.attrib['id'])
        unflattener = Unflattener(document,options.perfect)
        unflattener.analyse()
        unflattener.unflatten()
    indent(corpus.getroot())
    corpus.write(options.outfile)

if __name__=="__main__":
    interface()
