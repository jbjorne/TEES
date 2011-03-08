import sys, os
import Graph.networkx_v10rc1 as NX
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import prune

thisPath = os.path.dirname(os.path.abspath(__file__))
RELEASE = True
#IF LOCAL
RELEASE = False
#ENDIF
if RELEASE:
    sys.path.append( os.path.split(os.path.abspath(__file__))[0] + "/../.." )
#IF LOCAL
else:
    sys.path.append( os.path.split(os.path.abspath(__file__))[0] + "/../../JariSandbox/ComplexPPI/Source" )
#ENDIF
from Utils.ProgressCounter import ProgressCounter

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
    """
    Class for generating the analyses required by teh Unflattener.
    This is simply a collection of class methods.
    """
    @classmethod
    def transformOffset(cls,string):
        """
        Transforms an offset string 'XX-YY' into list [XX,YY].

        @type string: string
        @param string: offset
        @rtype: list of integers
        @return: [begin,end]
        """
        return([int(x) for x in string.split('-')])

    @classmethod
    def collectTokens(cls,sentence,tokenName):
        """
        Collect the tokens of the given tokenisation and
        map them by their ids.
        
        @type sentence: cElementTree.Element
        @param sentence: sentence node
        @type tokenName: string
        @param tokenName: tokeniser
        @rtype: (id,cElementTree.Element) dictionary
        @return: tokens mapped by their ids
        """
        tmp = sentence.find('sentenceanalyses')
        if tmp == None:
            return {}
        tmp2 = [x for x in tmp.getiterator('tokenization')
                if x.attrib['tokenizer']==tokenName][0]
        if tmp2 == None:
            return {}
        tokens = dict( [(x.attrib['id'],x)
                        for x in tmp2.findall('token')] )
        return(tokens)

    @classmethod
    def findTokens(cls,tokens,offset):
        """
        Finds the tokens that are at least partially
        within the given offset range.

        @type tokens: (id, cElementTree.Element) dictionary
        @param tokens: tokens mapped by their ids
        @type offset: list of integers
        @param offset: [begin,end]
        @rtype: list of strings
        @return: ids of tokens
        """
        return( [k for k,v in tokens.items()
                 if ((offset[0]>=v[0] and offset[0]<=v[1]) or
                     (offset[1]>=v[0] and offset[1]<=v[1]) or
                     (offset[0]<=v[0] and offset[1]>=v[1]))] )

    @classmethod
    #def mapEntitiesToTokens(cls,document,tokens):
    def mapEntitiesToTokens(cls,sentences,tokens):
        """
        Maps semantic entities to the corresponding syntactic tokens.

        @type sentences: list of cElementTree.Element
        @param sentences: sentence nodes to be processed
        @type tokens: (sentence id, (token id, cElementTree.Element) dictionary) dictionary
        @param tokens: tokens mapped by sentence and token ids

        @rtype: (token id, list of cElementTree.Element) dictionary
        @return: entities mapped by overlapping tokens
        """
        e2t = {}
        for sentence in sentences: #self.getSentencesWithParse(document.findall('sentence')):
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
    def makeDepG(cls,sentence,tokenName,parseName):
        """
        Processes the given parse into a directed acyclic graph.
        Nodes are token ids and edges contain types as strings.

        @type sentence: cElementTree.Element
        @param sentence: sentence node to be processed
        @type tokenName: string
        @param tokenName: tokeniser
        @type parseName: string
        @param parseName: parser

        @rtype: networkx.DiGraph()
        @return: parse graph
        """
        tmp = sentence.find('sentenceanalyses')
        tmp2 = [x for x in tmp.getiterator('parse')
                if (x.attrib['parser']==parseName and
                    x.attrib['tokenizer']==tokenName)][0]
        G = NX.DiGraph()
        for x in tmp2.findall('dependency'):
            G.add_edge(x.attrib['t1'],x.attrib['t2'],type=x.attrib['type'])
        return(G)

    @classmethod
    def makeSemG(cls,document):
        """
        Processes the semantic annotation of the given document
        into a directed acyclic graph. Unconnected nodes are excluded.

        Nodes are cElementTree.Element objects and edges contain
        the corresponding cElementTree.Element objects as attributes.

        @type document: cElementTree.Element
        @param document: document node to be processed

        @rtype: networkx.DiGraph()
        @return: semantic graph
        """
        entities = dict( [(x.attrib['id'],x) for x in
                          document.getiterator('entity')] )
        G = NX.DiGraph()
        for event in document.getiterator('interaction'):
            # ignore negative pairs
            # WHICH SHOULD NOT BE THERE IN THE FIRST PLACE!
            if event.attrib['type']=='neg':
                continue
            e1 = entities[event.attrib['e1']]
            e2 = entities[event.attrib['e2']]
            G.add_edge(e1,e2,xmlnode=event)
        return(G)

    @classmethod
    def findSentenceId(cls,element):
        """
        Finds the sentence id of the given element. This method relies
        on the hierarchy present in ids.

        @type element: cElementTree.Element
        @param element: node to be processed
        @rtype: string
        @return: id of sentence to which the element belongs
        """
        # THIS IS DATA SPECIFIC SOLUTION!
        return('.'.join(element.attrib['id'].split('.')[:3]))



class Unflattener:
    """
    Workhorse class for unflattening.
    """
    def __init__(self,document,perfect,tokenName,parseName):
        """
        Initial analyses are performed here.

        @type document: cElementTree.Element
        @param document: input document node
        @type perfect: boolean
        @param perfect: modify only perfectly-resolvable events?
        @type tokenName: string
        @param tokenName: tokeniser
        @type parseName: string
        @param parseName: parser
        """
        self.document = document
        self.perfect = perfect
        self.tokenName = tokenName
        self.parseName = parseName
        
        validSentences = self.getSentencesWithParse(self.document.findall('sentence'))
        
        self.sentences = dict( [(x.attrib['id'],x)
                                for x in validSentences] )
        
        # contains entity and interaction elements
        self.semG = Analyser.makeSemG(self.document)
        
        ###############################################################
        # NOTE! CRASH FIX FOR THE 1% PROJECT LAST 50 DOCUMENTS
        # This crashes for sentences with no parse
        #self.loners = [x for x in self.document.getiterator('entity')
        #               if not self.semG.has_node(x)]
        self.loners = []
        for sentence in validSentences:
            for entity in sentence.getiterator('entity'):
                if not self.semG.has_node(entity):
                    self.loners.append(entity)
        ###############################################################
        
        
        # tokens and dep.graphs are sentence-specific because
        # TOKEN IDS ARE NOT HIERARCHICAL
        self.tokens = dict( [(x,Analyser.collectTokens(x,self.tokenName))
                             for x in validSentences] )
        self.mapping = Analyser.mapEntitiesToTokens(validSentences,self.tokens)
        self.depDiGs = dict( [(x,Analyser.makeDepG(x,self.tokenName,self.parseName))
                              for x in validSentences] )
        self.depGs = dict( [(x,y.to_undirected())
                            for x,y in self.depDiGs.items()] )

    def analyse(self):
        """
        Analyses the parse, determines the unflattening strategy
        for each event, and modifies the cache accordingly.
        """
        def getCoordGrouping(edges):
            """
            Workhorse function for determining the grouping of arguments.

            @type edges: list of 3-tuples
            @param edges: out-going edges of an event to be grouped
            @rtype: list of lists of 3-tuples
            @return: grouped edges
            """
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
                    start1 = set( [depG[p[0]][p[1]]['type'] for p in paths1
                                   if (p and
                                       len(p)>=2 and
                                       not p[1] in parentTokens)] )
                    start2 = set( [depG[p[0]][p[1]]['type'] for p in paths2
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
            """
            Generates the edge groups describing the unflattened event.

            @type node: cElementTree.Element
            @param node: event to be unflattened
            @rtype: list of lists of 3-tuples
            @return: grouped edges
            """
            uid = node.attrib['id']
            t = node.attrib['type']
            # 'neg' edges are not considered and will be
            # removed from the final xml
            edges = [(x[0],x[1],x[2]['xmlnode'])
                      for x in self.semG.out_edges(node,True)
                     if not x[2]['xmlnode'].attrib['type']=='neg']
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
                    # (can 'respectively' be ignored?)
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
                # (can 'respectively' be ignored?)
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
            elif t in ['Protein']:
                # Proteins have sites (etc.) as successors
                # these edges will be processed later --> do nothing at this point
                result = [edges]
            else:
                if t != "Entity":
                    sys.stderr.write("Invalid event type: %s\n"%t)
            return([edges])

        # unflatten the graph in the cache
        counter = Increment()
        unprocessed_nodes = set([x for x in self.semG.nodes()
                                 if not self.semG.out_edges(x)])
        while unprocessed_nodes:
            next_nodes = set()
            for current in unprocessed_nodes:
                next_nodes.update(set(self.semG.predecessors(current)))
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
                            self.semG.add_edge(newN,e[1],xmlnode=newE)
                        for e in self.semG.in_edges(current,True):
                            newE = ET.Element('interaction',e[2]['xmlnode'].attrib)
                            newEid = newE.attrib['id']+'.E'+evid
                            newE.attrib['id'] = newEid
                            newE.attrib['e2'] = newId
                            self.semG.add_edge(e[0],newN,xmlnode=newE)
                    self.semG.remove_node(current)
            # ensure that nodes-to-be-processed have only out-neighbors
            # that have already been processed
            removable = set()
            for x in next_nodes:
                for y in next_nodes:
                    if NX.shortest_path(self.semG,x,y) and not x==y:
                        removable.add(x)
            unprocessed_nodes = next_nodes - removable

    def unflatten(self):
        """
        Modify the original document node to match the cache.
        See also 'analyse'.
        """
        for sentence in self.getSentencesWithParse(self.document.findall('sentence')):
            for elem in sentence.findall('entity'):
                sentence.remove(elem)
            for elem in sentence.findall('interaction'):
                sentence.remove(elem)
        for edge in self.semG.edges(data=True):
            sentence = self.sentences[Analyser.findSentenceId(edge[2]['xmlnode'])]
            sentence.insert(0,edge[2]['xmlnode'])
        for node in self.loners:
            sentence = self.sentences[Analyser.findSentenceId(node)]
            sentence.insert(0,node)
        for node in self.semG.nodes():
            sentence = self.sentences[Analyser.findSentenceId(node)]
            sentence.insert(0,node)

    def getSentencesWithParse(self, sentences):
        """
        Returns a list of sentences for which a parse is available.

        @type sentences: list of cElementTree.Element
        @param sentences: sentences to be filtered
        @rtype: list of cElementTree.Element
        @return: sentences with parse
        """
        sentencesWithParse = []
        for sentence in sentences:
            analyses = sentence.find("sentenceanalyses")
            if analyses == None:
                continue
            parses = analyses.find("parses")
            if parses == None:
                continue
            parseFound = False
            for p in parses.findall("parse"):
                if p.get("parser") == self.parseName:
                    parseFound = True
                    break
            if parseFound:
                sentencesWithParse.append(sentence)
        return sentencesWithParse

def unflatten(input, parse, tokenization=None, output=None, perfect=False, pruneInput=True):
    """
    Convenience wrapper that first prunes the graph and then unflattens.
    This function processes the whole corpus.

    @type input: string
    @param input: input file
    @type parse: string
    @param parse: parse to be used
    @type tokenization: string
    @param tokenization: tokenization to be used
    @type output: string
    @param output: output file
    @type perfect: boolean
    @param perfect: modify only perfectly-resolvable events?
    @rtype: cElementTree.Element
    @return: corpus node
    """
    if pruneInput:
        xml = prune.prune(input)
    else:
        xml = input
    return unflattenPruned(xml, parse, tokenization, output, perfect)

def unflattenPruned(input, parse, tokenization=None, output=None, perfect=False):
    """
    Convenience wrapper for unflattening a pruned corpus.

    @type input: string
    @param input: input file
    @type parse: string
    @param parse: parse to be used
    @type tokenization: string
    @param tokenization: tokenization to be used
    @type output: string
    @param output: output file
    @type perfect: boolean
    @param perfect: modify only perfectly-resolvable events?
    @rtype: cElementTree.Element
    @return: corpus node
    """
    print >> sys.stderr, "Unflattening"
    if tokenization == None:
        tokenization = parse
    options = ["-i",input,"-o",output,"-a",parse,"-t",tokenization]
    if perfect:
        options.append("-p")
    return interface(options)

def interface(optionArgs=sys.argv[1:]):
    """
    The function to handle the command-line interface.
    """
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
    op.add_option("-a", "--parse",
                  dest="parse",
                  help="Parse to be used",
                  metavar="PARSE")
    op.add_option("-t", "--tokens",
                  dest="tokens",
                  help="Tokens to be used",
                  metavar="TOKENS")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.infile:
        print "Please specify the input file."
        quit = True
#    if not options.outfile:
#        print "Please specify the output file."
#        quit = True
    if not options.parse:
        print "Please specify the parse."
        quit = True
    if not options.tokens:
        print "Please specify the tokenisation."
        quit = True
    if quit:
        op.print_help()
        return(False)

    corpus = ETUtils.ETFromObj(options.infile)
    documents = corpus.getroot().findall('document')
    counter = ProgressCounter(len(documents), "Unflatten")
    for document in documents:
        counter.update(1, "Unflattening ("+document.get("id")+"): ")
        #sys.stderr.write("Unflattening document %s\n"%document.attrib['id'])
        unflattener = Unflattener(document,options.perfect,
                                  options.tokens,options.parse)
        #if len(unflattener.tokens) == 0:
        #    continue
        unflattener.analyse()
        unflattener.unflatten()
    #indent(corpus.getroot())
    if options.outfile:
        ETUtils.write(corpus, options.outfile)
    return corpus

if __name__=="__main__":
    #interface()

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
    op.add_option("-a", "--parse",
                  dest="parse",
                  help="Parse to be used",
                  metavar="PARSE")
    op.add_option("-t", "--tokens",
                  dest="tokens",
                  help="Tokens to be used",
                  metavar="TOKENS")
    (options2, args2) = op.parse_args()

    quit = False
    if not options2.infile:
        print "Please specify the input file."
        quit = True
    if not options2.parse:
        print "Please specify the parse."
        quit = True
    if not options2.tokens:
        print "Please specify the tokenisation."
        quit = True
    if quit:
        op.print_help()
        sys.exit()
    
    unflatten(input=options2.infile, parse=options2.parse, tokenization=options2.tokens, output=options2.outfile)
