import sys
import networkx as NX
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

all_event_types = ['Gene_expression','Transcription',
                   'Translation','Protein_catabolism',
                   'Localization','Binding','Phosphorylation',
                   'Regulation','Positive_regulation',
                   'Negative_regulation']

class Analyser:
    def __init__(self,filename):
        self.corpus = ET.parse(filename).getroot()

    @classmethod
    def collectTokens(cls,sentence):
        tmp = sentence.find('sentenceanalyses')
        # collect tokens
        tmp2 = [x for x in tmp.getiterator('tokenization')
                if x.attrib['tokenizer']=='Charniak-Lease'][0]
        tokens = dict( [(x.attrib['id'],
                         Analyser.transformOffset(x.attrib['charOffset']))
                        for x in tmp2.findall('token')] )
        return(tokens)

    @classmethod
    def transformOffset(cls,string):
        return(string.split('-'))

    @classmethod
    def findTokens(cls,tokens,offset):
        return( [k for k,v in tokens.items()
                 if ((offset[0]>=v[0] and offset[0]<=v[1]) or
                     (offset[1]>=v[0] and offset[1]<=v[1]) or
                     (offset[0]<=v[0] and offset[1]>=v[1]))] )
    
    @classmethod
    def mapEntitiesToTokens(cls,sentence,tokens):
        # map entities to tokens
        t2e = {}
        e2t = {}
        for x in sentence.findall('entity'):
            uid = x.attrib['id']
            offset = Analyser.transformOffset(x.attrib['charOffset'])
            for y in Analyser.findTokens(tokens,offset):
                if not t2e.has_key(y):
                    t2e[y] = []
                if not e2t.has_key(uid):
                    e2t[uid] = []
                t2e[y].append(uid)
                e2t[uid].append(y)
        return((t2e,e2t))

    @classmethod
    def collectDependencies(cls,sentence):
        tmp = sentence.find('sentenceanalyses')
        # collect dep.edges
        tmp2 = [x for x in tmp.getiterator('parse')
                if x.attrib['tokenizer']=='Charniak-Lease'][0]
        G = NX.XGraph()
        for x in tmp2.findall('dependency'):
            G.add_edge(x.attrib['t1'],x.attrib['t2'],x.attrib['type'])
        return(G)
    
    def analyseCoordGroups(self,details=False):
        def any(l):
            tmp = l[:]
            while tmp:
                if tmp.pop(0):
                    return(True)
            return(False)
        def findEdges(traversed):
            tmp = traversed[:]
            result = []
            prev = tmp.pop(0)
            while tmp:
                result.append(G.get_edge(prev,tmp[0]))
                prev = tmp.pop(0)
            return(result)
        def coordPath(this,target):
            if G.has_edge(this,target):
                return(G.get_edge(this,target).startswith('conj'))
            return(False)
#         def coordPath(this,target,tmp=[]):
#             traversed = tmp[:]
#             # special case: same token returns true
#             if this==target:
#                 return(True)
#             traversed += [this]
#             if G.has_edge(this,target):
#                 # check that 'conj_*' is in path
#                 traversed += [target]
#                 if any([x.startswith('conj')
#                         for x in findEdges(traversed)]):
#                     return(True)
#                 return(False)
#             for fromT,toT,edge in G.edges(this):
#                 # continue if neighbor is not an entity token
#                 if (not toT in traversed and
#                     not t2e.has_key(toT)):
#                     if coordPath(toT,target,traversed):
#                         return(True)
#             return(False)
        def connected(s1,s2):
            for e1 in s1:
                for e2 in s2:
                    # do not continue if not within sentence
                    if e2t.has_key(e1):
                        for t1 in e2t[e1]:
                            # do not continue if not within sentence
                            if e2t.has_key(e2):
                                for t2 in e2t[e2]:
                                    if coordPath(t1,t2):
                                        return(True)
            return(False)
        
        egroups = {}
        processed = []
        for document in self.corpus.findall('document'):
            entities = dict( [(x.attrib['id'],x)
                              for x in document.getiterator('entity')] )
            for sentence in document.findall('sentence'):
                tokens = Analyser.collectTokens(sentence)
                t2e,e2t = Analyser.mapEntitiesToTokens(sentence,tokens)
                G = Analyser.collectDependencies(sentence)
                # groups in events
                for i in sentence.findall('interaction'):
                    uid = i.attrib['e1']
                    t = entities[i.attrib['e1']].attrib['type']
                    e = i.attrib['type']
                    if not egroups.has_key(t):
                        egroups[t] = {}
                    if not egroups[t].has_key(e):
                        egroups[t][e] = {}
                    if not egroups[t][e].has_key(uid):
                        egroups[t][e][uid] = set()
                    egroups[t][e][uid].add(i.attrib['e2'])
                # groups in syntax
                unprocessed = [set([x.attrib['id']])
                               for x in sentence.findall('entity')]
                while unprocessed:
                    used = []
                    current = unprocessed.pop()
                    while unprocessed:
                        next = unprocessed.pop()
                        if connected(current,next):
                            current.update(next)
                            unprocessed.extend(used)
                            used = []
                        else:
                            used.append(next)
                    processed.append(current)
                    unprocessed = used
        # analyse
        tmp = [z
               for x in egroups.values()
               for y in x.values()
               for z in y.values()]
        matched = len([x for x in tmp if x in processed])
        unmatched = len([x for x in tmp if x not in processed])
        sys.stderr.write("---- Coordination groups  ----\n")
        sys.stderr.write("Total: %s\n"%(matched+unmatched))
        sys.stderr.write("Fully matched total: %s\n"%(matched))
        sys.stderr.write("Non-matched total: %s\n"%(unmatched))
        for k1,v1 in egroups.items():
            sys.stderr.write("%s\n"%k1)
            for k2,v2 in v1.items():
                sys.stderr.write("\t%s\n"%k2)
                matched = [x for x in v2.values() if x in processed]
                sys.stderr.write("\t\tmatched: %s\n"%len(matched))
                if details:
                    for x in matched:
                        sys.stderr.write("\t\t\t%s\n"%str(x))
                unmatched = [x for x in v2.values() if x not in processed]
                sys.stderr.write("\t\tunmatched: %s\n"%len(unmatched))
                if details:
                    for x in unmatched:
                        sys.stderr.write("\t\t\t%s\n"%str(x))
                    
    
    def analyseMultiEdges(self,details=False):
        results = []
        for document in self.corpus.findall('document'):
            for sentence in document.findall('sentence'):
                for i1 in sentence.findall('interaction'):
                    for i2 in sentence.findall('interaction'):
                        if (not i1==i2 and
                            i1.attrib['e1']==i2.attrib['e1'] and
                            i1.attrib['e2']==i2.attrib['e2']):
                            results.append( (i1,i2) )
        sys.stderr.write("---- Multi-edges  ----\n")
        sys.stderr.write("Total: %s\n"%(len(results)))
        if details:
            for r in results:
                sys.stderr.write("%s - from %s to %s\n"%(str([x.attrib['type']
                                                              for x in r]),
                                                         r[0].attrib['e1'],
                                                         r[0].attrib['e2']))
    
    def analyseDependencyAdjacency(self,details=False):
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

        results = []
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
                sems = dict( [((x.attrib['e1'],x.attrib['e2']),x)
                              for x in sentence.findall('interaction')] )
                ents = [x for x in sentence.findall('entity')]
                while ents:
                    current = ents.pop()
                    e1 = current.attrib['id']
                    for x in ents:
                        e2 = x.attrib['id']
                        d = (e2 in adjEntities.neighbors(e1))
                        i = findIndirectPath(adjEntities,e1,e2)
                        if d and i:
                            di = 'direct+indirect'
                        elif d:
                            di = 'direct'
                        elif i:
                            di = 'indirect'
                        else:
                            di = 'neither'
                        if (e1,e2) in sems.keys():
                            results.append( ('sem',di,current,x,
                                             sems[(e1,e2)]) )
                        elif (e2,e1) in sems.keys():
                            results.append( ('sem',di,x,current,
                                             sems[(e2,e1)]) )
                        else:
                            results.append( ('nosem',di,current,x,None) )

        edge_total = len([x for x in results if x[0]=='sem'])
        edge_adj = len([x for x in results
                        if (x[0]=='sem' and
                            (x[1]=='direct' or x[1]=='direct+indirect'))])
        nonedge_total = len([x for x in results if x[0]=='nosem'])
        nonedge_adj = len([x for x in results
                           if (x[0]=='nosem' and
                               (x[1]=='direct' or x[1]=='direct+indirect'))])
        sys.stderr.write("---- Entity/trigger adjacency in syntax  ----\n")
        sys.stderr.write("All pairs total: %s\n"%(edge_total+nonedge_total))
        sys.stderr.write("Edge total: %s\n"%(edge_total))
        sys.stderr.write("Edge adjacent total: %s\n"%(edge_adj))
        sys.stderr.write("Non-edge total: %s\n"%(nonedge_total))
        sys.stderr.write("Non-edge adjacent total: %s\n"%(nonedge_adj))
        summary = {}
        for t in set([x[2].attrib['type']
                      for x in results if x[0]=='sem']):
            summary[t] = {}
            for e in set([x[4].attrib['type']
                          for x in results if x[0]=='sem']):
                summary[t][e] = {}
                for di in set([x[1]
                               for x in results if x[0]=='sem']):
                    summary[t][e][di] = []
        for x in results:
            if x[0]=='sem':
                summary[x[2].attrib['type']][x[4].attrib['type']][x[1]].append( (x[2].attrib['id'],x[3].attrib['id']) )
        for t in summary.keys():
            sys.stderr.write("%s\n"%t)
            for e in summary[t].keys():
                s = reduce(lambda a,b: a+len(b), summary[t][e].values(),0)
                if s:
                    sys.stderr.write("\t%s - %s\n"%(e,s))
                    for di in summary[t][e].keys():
                        l = len(summary[t][e][di])
                        sys.stderr.write("\t\t%s: %s\n"%(di,l))
                        if details:
                            for x in summary[t][e][di]:
                                sys.stderr.write("\t\t\t%s\n"%(str(x)))

    def analyseInterSentenceEdges(self,details=False):
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
        if details:
            for k,v in inter_edges.items():
                if v==[]:
                    continue
                sys.stderr.write("%s - %s\n"%(k,v))

    def analyseEdgeCombinations(self,details=False):
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
                if details:
                    sys.stderr.write("\t\t%s\n"%str([x for x,y in edges.items()
                                                     if str(sorted(y))==k and
                                                     nodes[x]==k2]))

    def analyseTokens(self,details=False):
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
        if details:
            for k,v in t_summary.items():
                ids = "%20s - %40s"%(k,[x[0] for x in v])
                texts = "%20s - %40s"%(mapping[k],[x[1] for x in v])
                sys.stderr.write("\t%s == %s\n"%(ids,texts))
        sys.stderr.write("---- Proteins --> multiple tokens  ----\n")
        sys.stderr.write("Total: %s\n"%(len(e_summary2.keys())))
        if details:
            for k,v in e_summary2.items():
                ids = "%20s - %50s"%(k,[x[0].split('.')[-1] for x in v])
                texts = "%s"%mapping[k]
                sys.stderr.write("\t%s == %s\n"%(ids,texts))
        sys.stderr.write("---- Triggers --> multiple tokens  ----\n")
        sys.stderr.write("Total: %s\n"%(len(e_summary.keys())))
        if details:
            for k,v in e_summary.items():
                ids = "%20s - %50s"%(k,[x[0].split('.')[-1] for x in v])
                texts = "%s"%mapping[k]
                sys.stderr.write("\t%s == %s\n"%(ids,texts))

    def analyseProteinOverlaps(self,details=False):
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
        if details:
            for a in result:
                sys.stderr.write("\t%s - %s\n"%(a[0],a[1]))

    def analyseProteins(self,details=False):
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
    op.add_option("--details",
                  dest="details",
                  help="Print detailed information",
                  default=False,
                  action="store_true")
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
    op.add_option("-m", "--multi",
                  dest="multi",
                  help="Multi-edges between pairs of entities/triggers",
                  default=False,
                  action="store_true")
    op.add_option("-c", "--coord",
                  dest="coord",
                  help="Coordination groups",
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
        tmp.analyseProteinOverlaps(options.details)
    if options.token:
        tmp.analyseTokens(options.details)
    if options.sentence:
        tmp.analyseInterSentenceEdges(options.details)
    if options.edge:
        tmp.analyseEdgeCombinations(options.details)
    if options.dep:
        tmp.analyseDependencyAdjacency(options.details)
    if options.multi:
        tmp.analyseMultiEdges(options.details)
    if options.coord:
        tmp.analyseCoordGroups(options.details)



if __name__=="__main__":
    interface()
