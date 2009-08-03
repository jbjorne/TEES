import re,sys
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

    def parse(self,filestem,taskpostfix):
        self.uid = filestem.split("/")[-1]

        textFile = filestem+".txt"
        proteinFile = filestem+".a1"
        eventFile = filestem+taskpostfix

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
        self.text = rawinput
        lines = rawinput.split("\n")
        self.title = lines[0]
        self.abstract = lines[1]

    def parseAnnotation(self,lines,isName=True):
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
        for k,v in self.entities.items():
            print "%s\t%s"%(k,v)
        for k,v in self.modifiers.items():
            for k2,v2 in self.modifiers[k].items():
                print "%s\t%s\t%s"%(k,k2,v2)
        for k,v in self.events.items():
            for x in v:
                print "%s\t%s"%(k,x)

    def printNode(self,removeDuplicates):
        node = self.getNode(removeDuplicates)
        indent(node)
        print ET.tostring(node)

    def getNode(self,removeDuplicates):
        newDocument = ET.Element('document',{'id':self.uid,
                                             'origId':self.uid})
        newSentence = ET.Element('sentence',{'id':self.uid,
                                             'origId':self.uid,
                                             'text':self.text})
        newDocument.append(newSentence)

        entnodes = {}
        if removeDuplicates:
            for k,v in self.entities.items():
                oid = v['id']
                v['id'] = self.uid+'.'+v['id'] # prepend document id
                v['origId'] = v['id']
                newEntity = ET.Element("entity",v)
                # add negation and speculation attributes by default (as False)
                newEntity.attrib['negation'] = "False"
                newEntity.attrib['speculation'] = "False"
                newSentence.append(newEntity)
                entnodes[oid] = newEntity
            edges = []
            for k,v in self.events.items():
                for x in v:
                    # add task 3 information from self.modifiers to
                    # corresponding entity
                    origUid = x['e1']
                    if self.modifiers.has_key(origUid):
                        mappedUid = self.mapping[origUid]
                        # origUid is original E
                        # mappedUid is E mapped to T
                        if self.modifiers[origUid].has_key('Negation'):
                            entnodes[mappedUid].attrib['negation'] = "True"
                        if self.modifiers[origUid].has_key('Speculation'):
                            entnodes[mappedUid].attrib['speculation'] = "True"
                    # and the interaction itself
                    if x['e1'][0]==('E'):
                        x['e1'] = self.mapping[x['e1']]
                    if x['e2'][0]==('E'):
                        x['e2'] = self.mapping[x['e2']]
                    tmp = x.copy()
                    del tmp['id']
                    if not tmp in edges:
                        edges.append(tmp)
                        x['id'] = self.uid+'.'+x['id'] # prepend document id
                        x['e1'] = self.uid+'.'+x['e1'] # prepend document id
                        x['e2'] = self.uid+'.'+x['e2'] # prepend document id
                        x['origId'] = x['id']
                        newEvent = ET.Element("interaction",x)
                        newSentence.append(newEvent)

        else:
            entities = {}
            events = []
            for k,v in self.entities.items():
                if v['isName']=='True':
                    # add negation and speculation attributes
                    # by default (as False) even though it is irrelevant here
                    v['negation'] = "False"
                    v['speculation'] = "False"
                    newEntity = ET.Element("entity",v)
                    # prepend document id
                    newEntity.attrib['id'] = self.uid+'.'+v['id']
                    newEntity.attrib['origId'] = newEntity.attrib['id']
                    entities[v['id']] = newEntity
            for k,v in self.events.items():
                for x in v:
                    for y in ['e1','e2']:
                        if x[y][0]==('T'):
                            if not entities.has_key(x[y]):
                                e = self.entities[x[y]]
                                # prepend document id
                                e['id'] = self.uid+'.'+e['id']
                                e['origId'] = e['id']
                                # add negation and speculation attributes
                                # by default (as False) even though
                                # it is irrelevant here
                                e['negation'] = "False"
                                e['speculation'] = "False"
                                newEntity = ET.Element("entity",e)
                                entities[x[y]] = newEntity
                            x[y] = self.uid+'.'+x[y]
                        elif x[y][0]==('E'):
                            if not entities.has_key(x[y]):
                                e = self.entities[self.mapping[x[y]]]
                                # add negation and speculation attributes
                                e['negation'] = "False"
                                e['speculation'] = "False"
                                origUid = x[y]
                                if self.modifiers.has_key(origUid):
                                    if self.modifiers[origUid].has_key('Negation'):
                                        e['negation'] = "True"
                                    if self.modifiers[origUid].has_key('Speculation'):
                                        e['speculation'] = "True"
                                # create a new id for a copy of event trigger
                                # (the one reserved for 'T' item is not used)
                                newEntity = ET.Element("entity",e)
                                # prepend document id and append event id
                                newEntity.attrib['id'] = self.uid+'.'+e['id']+'.'+x[y]
                                newEntity.attrib['origId'] = newEntity.attrib['id']
                                entities[x[y]] = newEntity
                            x[y] = self.uid+'.'+self.mapping[x[y]]+'.'+x[y]
                        else:
                            sys.stderr.write("Skipping %s\n"%x['id'])
                    # prepend document id
                    x['id'] = self.uid+'.'+x['id']
                    x['origId'] = x['id']
                    newEvent = ET.Element("interaction",x)
                    events.append(newEvent)
            for x in entities.values():
                newSentence.append(x)
            for x in events:
                newSentence.append(x)
                
        return(newDocument)



class Parser:
    def __init__(self):
        self.parsers = []

    def parse(self,indir,filestems,taskpostfix):
        if not indir.endswith('/'):
            indir = indir+'/'
        for stem in filestems:
            print >> sys.stderr, "Working on:", stem
            filename = indir+stem
            tmp = SentenceParser()
            tmp.parse(filename,taskpostfix)
            self.parsers.append(tmp)

    def getNode(self,removeDuplicates):
        newCorpus = ET.Element('corpus',{'source':'GENIA'})
        for x in self.parsers:
            newCorpus.append(x.getNode(removeDuplicates))
        return(newCorpus)

    def printNode(self,outfile,removeDuplicates):
        node = self.getNode(removeDuplicates)
        indent(node)
        outfile = open(outfile,'w')
        outfile.write(ET.tostring(node))
        outfile.close()



def interface(optionArgs=sys.argv[1:]):
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nConvert genia shared task files into the generic interaction format.\nUse positional arguments to specify the document ids.\n\nNeeded files:\n\t<filestem>.txt == original text\n\t<filestem>.a1 == protein annotation\n\t<filestem>.a2.tXXX == event annotation")
    op.add_option("-i", "--indir",
                  dest="indir",
                  help="Input file directory",
                  metavar="DIR")
    op.add_option("-o", "--outfile",
                  dest="outfile",
                  help="Output file",
                  metavar="FILE")
    op.add_option("-p", "--preserve",
                  dest="remove_duplicates",
                  help="Preserve duplicate nodes and edges",
                  default=True,
                  action="store_false")
    op.add_option("-t", "--task",
                  dest="task",
                  help="Which tasks to process (a2.tXXX file must be present)",
                  choices=["1","12","13","123"],
                  default="1",
                  metavar="[1|12|13|123]")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.indir:
        print "Please specify the directory for input files."
        quit = True
    if not options.outfile:
        print "Please specify the output filename."
        quit = True
    if not args:
        print "Please specify at least one document id."
        quit = True
    if quit:
        op.print_help()
        return(False)

    # use original files for the whole challenge
    taskpostfix = ".a2.t"+options.task
    parser = Parser()
    parser.parse(options.indir,args,taskpostfix)
    parser.printNode(options.outfile,options.remove_duplicates)
    return(True)

if __name__=="__main__":
    interface()
