import sys
import networkx as NX
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class Analyser:
    def __init__(self,filename):
        self.corpus = ET.parse(filename).getroot()

    def analyseDependencyAdjacency(self):
        def transformOffset(string):
            return(string.split('-'))
        def findTokens(offset):
            return( [k for k,v in tokens.items()
                     if ((offset[0]>=v[0] and offset[0]<=v[1]) or
                         (offset[1]>=v[0] and offset[1]<=v[1]) or
                         (offset[0]<=v[0] and offset[1]>=v[1]))] )
        def findAdj(node,traversed=[]):
            nexts = [x for x in tmp.neighbors(node) if x not in traversed]
            founds = [x for x in nexts if t2e.has_key(x)]
            nonfounds = [x for x in nexts if not t2e.has_key(x)]
            for x in nonfounds:
                founds.extend(findAdj(x,traversed+[node]+nexts))
            return(founds)
        def findIndirectPath(G,source,target):
            tmp = G.copy()
            tmp.delete_edge(source,target)
            return(NX.shortest_path(tmp,source,target))
        
        results = {'sem': {'direct': [],
                           'indirect': [],
                           'both': [],
                           'neither': []},
                   'nosem': {'direct': [],
                             'indirect': [],
                             'both': [],
                             'neither': []}
                   }
        for document in self.corpus.findall('document'):
            for sentence in document.findall('sentence'):
                tmp = sentence.find('sentenceanalyses')
                # collect tokens
                tmp2 = [x for x in tmp.getiterator('tokenization')
                        if x.attrib['tokenizer']=='Charniak-Lease'][0]
                tokens = dict( [(x.attrib['id'],
                                 transformOffset(x.attrib['charOffset']))
                                for x in tmp2.findall('token')] )
                # collect dep.edges
                tmp2 = [x for x in tmp.getiterator('parse')
                        if x.attrib['tokenizer']=='Charniak-Lease'][0]
                G = NX.Graph()
                for x in tmp2.findall('dependency'):
                    G.add_edge(x.attrib['t1'],x.attrib['t2'])
                # map entities to tokens
                t2e = {}
                for x in sentence.findall('entity'):
                    offset = transformOffset(x.attrib['charOffset'])
                    for y in findTokens(offset):
                        if not t2e.has_key(y):
                            t2e[y] = []
                        t2e[y].append(x.attrib['id'])
                # collect adjacencies of entities in syntax
                adj = {}
                tmp = G.copy()
                while tmp.nodes():
                    current = tmp.nodes()[0]
                    if t2e.has_key(current):
                        adj[current] = [x for x in findAdj(current)]
                    tmp.delete_node(current)
                adjEntities = NX.Graph()
                for x,val in adj.items():
                    for y in val:
                        for e1 in t2e[x]:
                            for e2 in t2e[y]:
                                adjEntities.add_edge(e1,e2)
                for x in sentence.findall('entity'):
                    adjEntities.add_node(x.attrib['id'])
                # check if sem.edge goes or is forced to go
                # through third-party entity
                sems = [(x.attrib['e1'],x.attrib['e2'])
                        for x in sentence.findall('interaction')]
                ents = [x for x in sentence.findall('entity')]
                while ents:
                    current = ents.pop()
                    e1 = current.attrib['id']
                    for x in ents:
                        e2 = x.attrib['id']
                        if (((e1,e2) in sems) or
                            ((e2,e1) in sems)):
                            s1 = 'sem'
                        else:
                            s1 = 'nosem'
                        d = (e2 in adjEntities.neighbors(e1))
                        i = findIndirectPath(adjEntities,e1,e2)
                        if d and i:
                            results[s1]['both'].append( (e1,e2) )
                        elif d:
                            results[s1]['direct'].append( (e1,e2) )
                        elif i:
                            results[s1]['indirect'].append( (e1,e2) )
                        else:
                            results[s1]['neither'].append( (e1,e2) )

        edge_total = reduce(lambda a,b:a+b,
                            [len(x) for x in results['sem'].values()])
        nonedge_total = reduce(lambda a,b:a+b,
                               [len(x) for x in results['nosem'].values()])
        sys.stderr.write("---- Entity/trigger adjacency in syntax  ----\n")
        sys.stderr.write("Pair total: %s\n"%(edge_total+nonedge_total))
        sys.stderr.write("Edge total: %s\n"%(edge_total))
        sys.stderr.write("Non-edge total: %s\n"%(nonedge_total))
        for k,v in results['sem'].items():
            sys.stderr.write("Sem.edge present, %s dep.edges: %s\n"%(k,len(v)))
            if len(v)<10:
                for x in v:
                    sys.stderr.write("\t%s - %s\n"%(x[0],x[1]))
        for k,v in results['nosem'].items():
            sys.stderr.write("No sem.edge present, %s dep.edges: %s\n"%(k,len(v)))
            if len(v)<10:
                for x in v:
                    sys.stderr.write("\t%s - %s\n"%(x[0],x[1]))

    def analyseInterSentenceEdges(self):
        edges = {}
        inter_edges = {}
        for document in self.corpus.findall('document'):
            for sentence in document.findall('sentence'):
                uid = sentence.attrib['id']
                edges[uid] = []
                inter_edges[uid] = []
                entities = {}
                for ent in sentence.findall('entity'):
                    eid = ent.attrib['id']
                    entities[eid] = True
                for pair in sentence.findall('interaction'):
                    t = pair.attrib['type']
                    e1id = pair.attrib['e1']
                    e2id = pair.attrib['e2']
                    edges[uid].append(t)
                    if not (entities.has_key(e1id) and entities.has_key(e2id)):
                        inter_edges[uid].append(t)

        total = reduce(lambda a,b: a+len(b),
                       edges.values(), 0)
        inter_total = reduce(lambda a,b: a+len(b),
                             inter_edges.values(), 0)
        sys.stderr.write("---- Edges across sentence boundaries ----\n")
        sys.stderr.write("Total: %s out of %s\n"%(inter_total,total))
        for k,v in inter_edges.items():
            if v==[]:
                continue
            sys.stderr.write("%s - %s\n"%(k,v))

    def analyseEdgeCombinations(self):
        edges = {}
        nodes = {}
        for document in self.corpus.findall('document'):
            for edge in document.getiterator('interaction'):
                uid = edge.attrib['e1']
                t = edge.attrib['type'].strip('1234567890')
                if not edges.has_key(uid):
                    edges[uid] = []
                edges[uid].append(t)
            for node in document.getiterator('entity'):
                uid = node.attrib['id']
                nodes[uid] = node.attrib['type']
        
        summary = {}
        sums = {}
        for k,v in edges.items():
            uid = str(sorted(v))
            t = nodes[k]
            if not summary.has_key(uid):
                summary[uid] = {}
            if not summary[uid].has_key(t):
                summary[uid][t] = 0
            summary[uid][t] += 1
        for k in summary.keys():
            sums[k] = sum(summary[k].values())
        sys.stderr.write("---- Out-going edge combinations ----\n")
        sys.stderr.write("Total: %s\n"%(len(edges.keys())))
        for k,v in sorted(sums.items(),lambda a,b:b[1]-a[1]):
            sys.stderr.write("%s - %s\n"%(v,k))
            for k2,v2 in sorted(summary[k].items(),lambda a,b:b[1]-a[1]):
                sys.stderr.write("\t%s - %s\n"%(v2,k2))
                if v2<10:
                    sys.stderr.write("\t\t%s\n"%str([x for x,y in edges.items()
                                                     if str(sorted(y))==k and
                                                     nodes[x]==k2]))

    def analyseTokens(self):
        t_result = {}
        e_result = {}
        mapping = {}
        mapping2 = {}
        for document in self.corpus.findall('document'):
            for sentence in document.findall('sentence'):
                sid = sentence.attrib['id']
                tmp = sentence.find('sentenceanalyses').find('tokenizations').find('tokenization').findall('token')
                token_offsets = [(sid+'.'+x.attrib['id'],x.attrib['text'],
                                  map(lambda a:int(a),
                                      x.attrib['charOffset'].split('-')))
                                 for x in tmp]
                entity_offsets = [(x.attrib['id'],x.attrib['text'],
                                   map(lambda a:int(a),
                                       x.attrib['charOffset'].split('-')),
                                   x.attrib['type'])
                                  for x in sentence.findall('entity')]
                for ta in token_offsets:
                    for eb in entity_offsets:
                        a = ta[2]
                        b = eb[2]
                        if ((a[1]>=b[0] and a[1]<=b[1])
                            or (a[0]>=b[0] and a[0]<=b[1])
                            or (a[0]<b[0] and a[1]>b[1])):
                            if not t_result.has_key(ta[0]):
                                t_result[ta[0]] = []
                            t_result[ta[0]].append(eb)
                            mapping[ta[0]] = ta[1]
                            if not e_result.has_key(eb[0]):
                                e_result[eb[0]] = []
                            e_result[eb[0]].append(ta)
                            mapping[eb[0]] = eb[1]
                            mapping2[eb[0]] = eb[3]
        t_summary = dict( [(k,v) for k,v in t_result.items() if len(v)>1] )
        e_summary2 = dict( [(k,v) for k,v in e_result.items()
                           if len(v)>1 and mapping2[k]=='Protein'] )
        e_summary = dict( [(k,v) for k,v in e_result.items()
                           if len(v)>1 and mapping2[k]!='Protein'] )
        sys.stderr.write("---- Tokens --> multiple entities  ----\n")
        sys.stderr.write("Total: %s\n"%(len(t_summary.keys())))
        for k,v in t_summary.items():
            ids = "%20s - %40s"%(k,[x[0] for x in v])
            texts = "%20s - %40s"%(mapping[k],[x[1] for x in v])
            sys.stderr.write("\t%s == %s\n"%(ids,texts))
        sys.stderr.write("---- Proteins --> multiple tokens  ----\n")
        sys.stderr.write("Total: %s\n"%(len(e_summary2.keys())))
        for k,v in e_summary2.items():
            ids = "%20s - %50s"%(k,[x[0].split('.')[-1] for x in v])
            texts = "%s"%mapping[k]
            sys.stderr.write("\t%s == %s\n"%(ids,texts))
        sys.stderr.write("---- Triggers --> multiple tokens  ----\n")
        sys.stderr.write("Total: %s\n"%(len(e_summary.keys())))
        for k,v in e_summary.items():
            ids = "%20s - %50s"%(k,[x[0].split('.')[-1] for x in v])
            texts = "%s"%mapping[k]
            sys.stderr.write("\t%s == %s\n"%(ids,texts))

    def analyseProteinOverlaps(self):
        result = []
        for document in self.corpus.findall('document'):
            for sentence in document.findall('sentence'):
                entity_offsets = [(x.attrib['id'],x.attrib['type'],
                                   map(lambda a:int(a),
                                       x.attrib['charOffset'].split('-')))
                                  for x in sentence.findall('entity')]
                while entity_offsets:
                    ea = entity_offsets.pop()
                    for eb in entity_offsets:
                        if ea[1]==eb[1] and ea[2]==eb[2]:
                            continue
                        a = ea[2]
                        b = eb[2]
                        if ((a[1]>=b[0] and a[1]<=b[1])
                            or (a[0]>=b[0] and a[0]<=b[1])
                            or (a[0]<b[0] and a[1]>b[1])):
                            result.append( (ea[0],eb[0]) )
        sys.stderr.write("---- Overlapping entities  ----\n")
        sys.stderr.write("Total: %s\n"%(len(result)))
        for a in result:
            sys.stderr.write("\t%s - %s\n"%(a[0],a[1]))

    def analyseProteins(self):
        for document in self.corpus.findall('document'):
            for sentence in document.findall('sentence'):
                pass



def interface(optionArgs=sys.argv[1:]):
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nPrint genia shared task specific statistics.")
    op.add_option("-i", "--infile",
                  dest="infile",
                  help="Input file (gifxml)",
                  metavar="FILE")
    op.add_option("-o", "--overlap",
                  dest="overlap",
                  help="Overlaps in entities",
                  default=False,
                  action="store_true")
    op.add_option("-t", "--token",
                  dest="token",
                  help="Multiple tokens per entity or vice versa",
                  default=False,
                  action="store_true")
    op.add_option("-s", "--sentence",
                  dest="sentence",
                  help="Inter-sentence edges",
                  default=False,
                  action="store_true")
    op.add_option("-e", "--edge",
                  dest="edge",
                  help="Combinations of out-going edges",
                  default=False,
                  action="store_true")
    op.add_option("-d", "--dep",
                  dest="dep",
                  help="Adjacency of entities/triggers in dependency graph",
                  default=False,
                  action="store_true")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.infile:
        print "Please specify the input file."
        quit = True
    if quit:
        op.print_help()
        return(False)

    tmp = Analyser(options.infile)
    if options.overlap:
        tmp.analyseProteinOverlaps()
    if options.token:
        tmp.analyseTokens()
    if options.sentence:
        tmp.analyseInterSentenceEdges()
    if options.edge:
        tmp.analyseEdgeCombinations()
    if options.dep:
        tmp.analyseDependencyAdjacency()



if __name__=="__main__":
    interface()
