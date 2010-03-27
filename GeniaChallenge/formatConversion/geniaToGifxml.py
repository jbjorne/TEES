import re,sys,os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET



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



class SentenceParser:
    """
    Sentence parser generates a cElementTree node for a single document.
    """
    siteCount = re.compile(r'^Site([0-9]*)$')

    def __init__(self):
        self.uid = ''
        self.text = ''
        self.title = ''
        self.abstract = ''

        self.counter = Increment()
        self.entities = {}
        self.events = {}
        self.modifiers = {}
        self.mapping = {}
    
    def parseDocument(self, txtFile, a1File, taskSuffix):
        """
        Parses a single document from the given files.

        @type txtFile: string
        @param txtFile: .txt file
        @type a1File: string
        @param a1File: .a1 file
        @type taskSuffix: string
        @param taskSuffix: suffix of a2-file (without 't')
        """
        self.uid="uima"
        tmp = open(txtFile)
        self.parseText(tmp.read())
        tmp.close()
        
        tmp = open(a1File)
        self.parseAnnotation(tmp.read().split("\n"),isName=True)
        tmp.close()

    def parse(self,filestem,tasksuffix):
        """
        Parses a document based on its id.

        @type filestem: string
        @param filestem: document id
        @type tasksuffix: string
        @param tasksuffix: suffix of .a2-file (without 't')
        """
        self.uid = filestem.split("/")[-1]

        textFile = filestem+".txt"
        proteinFile = filestem+".a1"
        eventFile = filestem+tasksuffix

        tmp = open(textFile)
        self.parseText(tmp.read())
        tmp.close()

        tmp = open(proteinFile)
        self.parseAnnotation(tmp.read().split("\n"),isName=True)
        tmp.close()

        try:
            tmp = open(eventFile)
        except IOError, e:
            sys.stderr.write("Cannot open %s\n"%eventFile)
        else:
            self.parseAnnotation(tmp.read().split("\n"),isName=False)
            tmp.close()

    def parseText(self,rawinput):
        """
        Parses the document text and splits it into title and abstract.

        @type rawinput: string
        @param rawinput: document text
        """
        self.text = rawinput
        lines = rawinput.split("\n")
        self.title = lines[0]
        self.abstract = lines[1]

    def parseAnnotation(self,lines,isName=True):
        """
        Parses the annotation lines (either from .a1 or .a2 files).

        @type lines: list of strings
        @param lines: annotation lines
        @type isName: boolean
        @param isName: encountered T-entities are named entities?
        """
        for line in lines:
            if not line:
                continue
            if line.startswith("T"):
                uid,content,text = line.split("\t")
            else:
                uid,content = line.split("\t")
            if not content:
                sys.stderr.write("Unmatched line: '%s'"%line.strip())
                continue
            if uid[0]=="T":
                t,b,e = content.split()
                if not self.entities.has_key(uid):
                    self.entities[uid] = {}
                else:
                    sys.stderr.write("Id %s already exists in document %s!"%(uid,self.uid))
                assert(text==self.text[int(b):int(e)])
                self.entities[uid].update({'id':uid,
                                           'origId':uid,
                                           'charOffset':"%s-%s"%(b,int(e)-1),
                                           'text':self.text[int(b):int(e)],
                                           'type':t,
                                           'isName':str(isName)})
            elif uid[0]=="*":
                t,args = content.split(None,1)
                args = args.split()
                if not self.events.has_key(uid):
                    self.events[uid] = []
                while args:
                    e1 = args.pop(0)
                    count = 0
                    for e2 in args:
                        self.events[uid].append({'id':uid+'.'+str(count),
                                                 'directed':'False',
                                                 'e1':e1,
                                                 'e2':e2,
                                                 'type':t})
                        count += 1
            elif uid[0]=="M":
                t,e = content.split()
                if not self.modifiers.has_key(e):
                    self.modifiers[e] = {}
                self.modifiers[e][t] = uid
            elif uid[0]=="E":
                t = content.split()[0]
                args = content.split()[1:]
                if not self.events.has_key(uid):
                    self.events[uid] = []
                bgnt,bgne = t.split(":")
                count = 0
                for arg in args:
                    endt,ende = arg.split(":")
                    self.events[uid].append({'id':uid+'.'+str(count),
                                            'directed':'True',
                                            'e1':uid,
                                            'e2':ende,
                                            'type':endt})
                    count += 1
                self.mapping[uid] = bgne

    def printSimple(self):
        """
        Prints parsed annotations. For debugging only.
        """
        for k,v in self.entities.items():
            print "%s\t%s"%(k,v)
        for k,v in self.modifiers.items():
            for k2,v2 in self.modifiers[k].items():
                print "%s\t%s\t%s"%(k,k2,v2)
        for k,v in self.events.items():
            for x in v:
                print "%s\t%s"%(k,x)

    def printNode(self,removeDuplicates):
        """
        Prints the cElementTree node of the document. For debugging only.

        @type removeDuplicates: boolean
        @param removeDuplicates: merge duplicates?
        """
        node = self.getNode(removeDuplicates)
        indent(node)
        print ET.tostring(node)

    def getNode(self,removeDuplicates,modifyExtra):
        """
        Generates a cElementTree node of the document.

        @type removeDuplicates: boolean
        @param removeDuplicates: merge duplicates?
        @type modifyExtra: boolean
        @param modifyExtra: modify extra arguments?
        @rtype: cElementTree.Element
        @return: document as a cElementTree node
        """
        def createPhysical(v):
            # add negation and speculation attributes
            # by default (as False) even though it is irrelevant here
            v['negation'] = "False"
            v['speculation'] = "False"
            newEntity = ET.Element("entity",v)
            # prepend document id
            newEntity.attrib['id'] = self.uid+'.'+v['id']
            newEntity.attrib['origId'] = newEntity.attrib['id']
            return(newEntity)

        def createEvent(v,origUid):
            # add default negation and speculation attributes
            v['negation'] = "False"
            v['speculation'] = "False"
            if self.modifiers.has_key(origUid):
                if self.modifiers[origUid].has_key('Negation'):
                    v['negation'] = "True"
                if self.modifiers[origUid].has_key('Speculation'):
                    v['speculation'] = "True"
            # create a new id for a copy of event trigger
            # (the one reserved for 'T' item is not used)
            newEntity = ET.Element("entity",v)
            # prepend document id and append event id
            newEntity.attrib['id'] = self.uid+'.'+v['id']+'.'+origUid
            newEntity.attrib['origId'] = newEntity.attrib['id']
            return(newEntity)

        newDocument = ET.Element('document',{'id':self.uid,
                                             'origId':self.uid})
        newSentence = ET.Element('sentence',{'id':self.uid,
                                             'origId':self.uid,
                                             'text':self.text})
        newDocument.append(newSentence)

        # create unmerged graph
        entityNodes = {}
        eventNodes = []
        t2e = {}
        # create all names only once
        for k,v in self.entities.items():
            if v['isName']=='True':
                entityNodes[v['id']] = createPhysical(v)
        # create interactions and event entities (as necessary)
        for edges in self.events.values():
            for edge in edges:
                for end in ['e1','e2']:
                    e = edge[end]
                    # create non-name physical (only task 2)
                    if e[0]==('T'):
                        if not entityNodes.has_key(e):
                            entityNodes[e] = createPhysical(self.entities[e])
                        edge[end] = self.uid+'.'+edge[end]
                    # create event node
                    elif e[0]==('E'):
                        te = self.mapping[e]
                        if not entityNodes.has_key(e):
                            entityNodes[e] = createEvent(self.entities[te],e)
                        edge[end] = self.uid+'.'+te+'.'+e
                        # map event to its text (for duplicate removal)
                        if not t2e.has_key(te):
                            t2e[te] = []
                        if not edge[end] in t2e[te]:
                            t2e[te].append(edge[end])
                    else:
                        sys.stderr.write("Skipping %s\n"%edge['id'])
                # prepend document id
                edge['id'] = self.uid+'.'+edge['id']
                edge['origId'] = edge['id']
                newEvent = ET.Element("interaction",edge)
                eventNodes.append(newEvent)
        for x in sorted(entityNodes.values(),key=lambda a: a.attrib['id']):
            newSentence.append(x)
        for x in sorted(eventNodes,key=lambda a: a.attrib['id']):
            newSentence.append(x)
                
        if modifyExtra:
            self.modifyExtra(newSentence)
        if removeDuplicates:
            self.removeDuplicates(newSentence,t2e)

        # re-sort elements
        entities = sorted(newSentence.findall('entity'),
                          key=lambda a: a.attrib['id'])
        interactions = sorted(newSentence.findall('interaction'),
                              key=lambda a: a.attrib['id'])
        while len(newSentence):
            newSentence.remove(newSentence[0])
        for x in entities:
            newSentence.append(x)
        for x in interactions:
            newSentence.append(x)

        return(newDocument)

    def modifyExtra(self,sentence):
        """
        Modify extra arguments. (Do not use if you do not know what it does.)

        @type sentence: cElementTree.Element
        @param sentence: document node
        """
        nodeMap = dict([(x.attrib['id'],x)
                        for x in sentence.findall('entity')])
        predMap = {}
        for edge in sentence.findall('interaction'):
            if not predMap.has_key(edge.attrib['e1']):
                predMap[edge.attrib['e1']] = {}
            if not predMap[edge.attrib['e1']].has_key(edge.attrib['type']):
                predMap[edge.attrib['e1']][edge.attrib['type']] = []
            predMap[edge.attrib['e1']][edge.attrib['type']].append(edge)
        # all lists should have only one member
        for k1 in predMap.keys():
            for k2 in predMap[k1].keys():
                assert len(predMap[k1][k2])==1, "Predecessor--edgetype pair not unique in event %s"%k1
        relocate = [] # targetProtein--extraEdge pairs
        for nid,node in nodeMap.items():
            if not predMap.has_key(node.attrib['id']):
                continue
            edges = predMap[node.attrib['id']]
            if node.attrib['type']=='Localization':
                assert not ('ToLoc' in edges.keys() and 'AtLoc' in edges.keys()), "Both ToLoc and AtLoc encountered in event %s"%nid
                if edges.has_key('ToLoc'):
                    assert edges.has_key('Theme'), "ToLoc present without Theme in event %s"%nid
                    relocate.append((edges['Theme'][0].attrib['e2'],
                                     edges['ToLoc'][0]))
                if edges.has_key('AtLoc'):
                    assert edges.has_key('Theme'), "AtLoc present without Theme in event %s"%nid
                    relocate.append((edges['Theme'][0].attrib['e2'],
                                     edges['AtLoc'][0]))
            elif node.attrib['type']=='Binding':
                for t in edges.keys():
                    if SentenceParser.siteCount.match(t):
                        c = SentenceParser.siteCount.match(t).groups()[0]
                        assert edges["Theme%s"%c], "Site%s present without Theme%s in event %s"%(c,c,nid)
                        relocate.append((edges["Theme%s"%c][0].attrib['e2'],
                                         edges["Site%s"%c][0]))
            elif node.attrib['type']=='Phosphorylation':
                if edges.has_key('Site'):
                    assert edges.has_key('Theme'), "Site present without Theme in event %s"%nid
                    relocate.append((edges['Theme'][0].attrib['e2'],
                                     edges['Site'][0]))
            elif (node.attrib['type']=='Regulation' or
                  node.attrib['type']=='Negative_regulation' or
                  node.attrib['type']=='Positive_regulation'):
                if edges.has_key('Site'):
                    assert edges.has_key('Theme'), "Site present without Theme in event %s"%nid
                    relocate.append((edges['Theme'][0].attrib['e2'],
                                     edges['Site'][0]))
                if edges.has_key('CSite'):
                    assert edges.has_key('Cause'), "CSite present without Cause in event %s"%nid
                    relocate.append((edges['Cause'][0].attrib['e2'],
                                     edges['CSite'][0]))

        for protein,edge in relocate:
            # event-->site becomes site-->protein
            edge.attrib['e1'] = edge.attrib['e2']
            edge.attrib['e2'] = protein

    def removeDuplicates(self,sentence,t2e):
        """
        Merge duplicate nodes and edges (i.e. flatten the graph).

        @type sentence: cElementTree.Element
        @param sentence: document node
        @type t2e: (string, list of cElementTree.Element objects) dictionary
        @param t2e: entities mapped by their text binding
        """
        mapping = {}
        nodeDict = dict([(x.attrib['id'],x)
                          for x in sentence.findall('entity')])
        edgeDict = dict([(x.attrib['id'],x)
                          for x in sentence.findall('interaction')])
        for events in t2e.values():
            # each event node has the same text binding -> merge nodes
            oldId = events.pop(0)
            # remove event id since events will be merged
            newId = oldId.rsplit('.',1)[0]
            mapping[oldId] = newId
            # create mapping for changes
            for e in events:
                assert not mapping.has_key(e), "Id %s already in mapping"%e
                mapping[e] = newId
                sentence.remove(nodeDict[e])
        # change all event references to corresponding newId
        for e in sentence.findall('entity'):
            if mapping.has_key(e.attrib['id']):
                e.attrib['id'] = mapping[e.attrib['id']]
                e.attrib['origId'] = mapping[e.attrib['origId']]
        for e in sentence.findall('interaction'):
            if mapping.has_key(e.attrib['e1']):
                e.attrib['e1'] = mapping[e.attrib['e1']]
            if mapping.has_key(e.attrib['e2']):
                e.attrib['e2'] = mapping[e.attrib['e2']]
        # remove duplicate edges
        encountered = {}
        for e in sentence.findall('interaction'):
            tri = (e.attrib['e1'],e.attrib['e2'],e.attrib['type'])
            if not encountered.has_key(tri):
                encountered[tri] = True
            else:
                sentence.remove(edgeDict[e.attrib['id']])



class Parser:
    """
    Parser is a wrapper for the workhorse class SentenceParser.
    """
    def __init__(self):
        self.parsers = []

    def parse(self,indir,filestems,tasksuffix):
        """
        Parses the corpus from an input directory.

        @type indir: string
        @param indir: input directory
        @type filestems: list of strings
        @param filestems: ids of documents to be included
        @type tasksuffix: string
        @param tasksuffix: suffix of .a2-files (without 't')
        """
        if not indir.endswith('/'):
            indir = indir+'/'
        for stem in filestems:
            print >> sys.stderr, "Working on:", stem
            filename = indir+stem
            tmp = SentenceParser()
            tmp.parse(filename,tasksuffix)
            self.parsers.append(tmp)
    
    def parseDocument(self, txtFile, a1File, taskSuffix):
        """
        Parses a single document from a file.

        @type txtFile: string
        @param txtFile: .txt file
        @type a1File: string
        @param a1File: .a1 file
        @type taskSuffix: string
        @param taskSuffix: suffix of a2-file (without 't')
        """
        tmp = SentenceParser()
        tmp.parseDocument(txtFile, a1File, taskSuffix)
        self.parsers.append(tmp)

    def getNode(self,removeDuplicates,modifyExtra):
        """
        Generates a cElementTree node of the corpus.

        @type removeDuplicates: boolean
        @param removeDuplicates: merge duplicates?
        @type modifyExtra: boolean
        @param modifyExtra: modify extra arguments?
        @rtype: cElementTree.Element
        @return: corpus as a cElementTree node
        """
        newCorpus = ET.Element('corpus',{'source':'GENIA'})
        for x in self.parsers:
            newCorpus.append(x.getNode(removeDuplicates,modifyExtra))
        return(newCorpus)

    def printNode(self,outfile,removeDuplicates,modifyExtra):
        """
        Outputs the corpus node into a file.

        @type outfile: string
        @param outfile: output filename
        @param removeDuplicates: see 'getNode'
        @param modifyExtra: see 'getNode'
        """
        node = self.getNode(removeDuplicates,modifyExtra)
        indent(node)
        outfile = open(outfile,'w')
        outfile.write(ET.tostring(node))
        outfile.close()


def process(indir, task, outfile, remove_duplicates, modify_extra, docIds=None):
    tasksuffix = ".a2.t"+task
    parser = Parser()
    filestems = set()
    for filename in os.listdir(indir):
        filestem = filename.split(".",1)[0]
        if docIds == None:
            filestems.add(filestem)
        elif filestem in docIds:
            filestems.add(filestem)
    filestems = list(filestems)
    filestems.sort()
    parser.parse(indir,filestems,tasksuffix)
    parser.printNode(outfile, (not remove_duplicates), modify_extra)
    return(True)


def interface(optionArgs=sys.argv[1:]):
    """
    The function to handle the command-line interface.
    """
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nConvert genia shared task files into the generic interaction format.\nUse positional arguments to specify the document ids.\n\nNeeded files:\n\t<filestem>.txt == original text\n\t<filestem>.a1 == protein annotation\n\t<filestem>.a2.tXXX == event annotation")
    op.add_option("-i", "--indir",
                  dest="indir",
                  help="Input file directory",
                  metavar="DIR")
    op.add_option("-a", "--a1file",
                  dest="a1file",
                  help="A1 File (-a & -x are an alternative for -i)",
                  metavar="FILE")
    op.add_option("-x", "--txtfile",
                  dest="txtfile",
                  help="Text file (-a & -x are an alternative for -i)",
                  metavar="FILE")
    op.add_option("-o", "--outfile",
                  dest="outfile",
                  help="Output file",
                  metavar="FILE")
    op.add_option("-p", "--preserve",
                  dest="remove_duplicates",
                  help="Preserve duplicate nodes and edges",
                  default=True,
                  action="store_false")
    op.add_option("-e", "--extra",
                  dest="modify_extra",
                  help="Modify extra arguments (do not use if you do not know what it does)",
                  default=False,
                  action="store_true")
    op.add_option("-t", "--task",
                  dest="task",
                  help="Which tasks to process (a2.tXXX file must be present)",
                  choices=["1","12","13","123"],
                  default="1",
                  metavar="[1|12|13|123]")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.indir:
        if not options.a1file and options.txtfile:
            print "Please specify the directory for input files."
            quit = True
    if options.a1file or options.txtfile:
        if not options.a1file:
            print "Please specify the a1 file."
            quit = True
        elif not options.txtfile:
            print "Please specify the text file."
            quit = True
        if options.indir:
            print "-i and -a & -x are mutually exclusive options"
            quit = True
    if not options.outfile:
        print "Please specify the output filename."
        quit = True
    if options.indir and not args:
        print "Please specify at least one document id."
        quit = True
    if quit:
        op.print_help()
        return(False)

    # use original files for the whole challenge
    tasksuffix = ".a2.t"+options.task
    parser = Parser()
    if options.indir:
        parser.parse(options.indir,args,tasksuffix)
    else:
        parser.parseDocument(options.txtfile, options.a1file, tasksuffix)
    parser.printNode(options.outfile,
                     options.remove_duplicates,
                     options.modify_extra)
    return(True)

if __name__=="__main__":
    interface()
