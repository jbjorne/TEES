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

    def parse(self,filestem):
        self.uid = filestem.split("/")[-1]

        textFile = filestem+".txt"
        proteinFile = filestem+".a1"
        eventFile = filestem+".a2"

        tmp = open(textFile)
        self.parseText(tmp.read())
        tmp.close()

        tmp = open(proteinFile)
        self.parseAnnotation(tmp.read().split("\n"),isName=True)
        tmp.close()

        tmp = open(eventFile)
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
                sys.exit(1)
            if uid[0]=="T":
                t,b,e = content.split()
                if not self.entities.has_key(uid):
                    self.entities[uid] = {}
                assert(text==self.text[int(b):int(e)])
                self.entities[uid].update({'id':uid,
                                           'origId':uid,
                                           'charOffset':"%s-%s"%(b,int(e)-1),
                                           'text':self.text[int(b):int(e)],
                                           'type':t,
                                           'isName':str(isName)})
                self.mapping[uid] = 'rb.'+self.uid+'.'+self.counter.get()
            elif uid[0]=="*":
                t,args = content.split(None,1)
                args = args.split()
                if not self.events.has_key(uid):
                    self.events[uid] = []
                while args:
                    e1 = args.pop(0)
                    for e2 in args:
                        self.events[uid].append({'id':uid,
                                                 'directed':'False',
                                                 'e1':e1,
                                                 'e2':e2,
                                                 'type':t})
            elif uid[0]=="M":
                t,e = content.split()
                if not self.modifiers.has_key(uid):
                    self.modifiers[uid] = {}
                self.modifiers[uid].update({'id':uid,
                                            'e1':e,
                                            'type':t})
            elif uid[0]=="E":
                t = content.split()[0]
                args = content.split()[1:]
                if not self.events.has_key(uid):
                    self.events[uid] = []
                bgnt,bgne = t.split(":")
                for arg in args:
                    endt,ende = arg.split(":")
                    self.events[uid].append({'id':uid,
                                            'directed':'True',
                                            'e1':bgne,
                                            'e2':ende,
                                            'type':endt})
                self.mapping[uid] = bgne

    def printSimple(self):
        for k,v in self.entities.items():
            print "%s\t%s"%(k,v)
        for k,v in self.modifiers.items():
            print "%s\t%s"%(k,v)
        for k,v in self.events.items():
            for x in v:
                print "%s\t%s"%(k,x)

    def printNode(self):
        node = self.getNode()
        indent(node)
        print ET.tostring(node)

    def getNode(self):
        newDocument = ET.Element('document',{'id':self.uid})
        newSentence = ET.Element('sentence',{'id':self.uid,
                                             'origId':self.uid,
                                             'text':self.text})
        newDocument.append(newSentence)
        for k,v in self.entities.items():
            v['origId'] = self.mapping[v['id']]
            v['id'] = self.uid+'.'+v['id'] # prepend document id
            newEntity = ET.Element("entity",v)
            newSentence.append(newEntity)
        for k,v in self.modifiers.items():
            v['id'] = self.uid+'.'+v['id'] # prepend document id
            v['e1'] = self.uid+'.'+v['e1'] # prepend document id
            newModifier = ET.Element("modifier",v)
            newSentence.append(newModifier)
        for k,v in self.events.items():
            for x in v:
                if x['e1'][0]==('E'):
                    x['e1'] = self.mapping[x['e1']]
                if x['e2'][0]==('E'):
                    x['e2'] = self.mapping[x['e2']]
                x['id'] = self.uid+'.'+x['id'] # prepend document id
                x['e1'] = self.uid+'.'+x['e1'] # prepend document id
                x['e2'] = self.uid+'.'+x['e2'] # prepend document id
                newEvent = ET.Element("pair",x)
                newSentence.append(newEvent)
        return(newDocument)



class Parser:
    def __init__(self):
        self.parsers = []

    def parse(self,indir,filestems):
        if not indir.endswith('/'):
            indir = indir+'/'
        for stem in filestems:
            print >> sys.stderr, "Working on:", stem
            filename = indir+stem
            tmp = SentenceParser()
            tmp.parse(filename)
            self.parsers.append(tmp)

    def getNode(self):
        newCorpus = ET.Element('corpus',{'source':'GENIA'})
        for x in self.parsers:
            newCorpus.append(x.getNode())
        return(newCorpus)

    def printNode(self,outfile):
        node = self.getNode()
        indent(node)
        outfile = open(outfile,'w')
        outfile.write(ET.tostring(node))
        outfile.close()



def interface(optionArgs=sys.argv[1:]):
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nConvert genia shared task files into the generic interaction format.\nUse positional arguments to specify the document ids.\n\nNeeded files:\n\t<filestem>.txt == original text\n\t<filestem>.a1 == protein annotation\n\t<filestem>.a2 == event annotation")
    op.add_option("-i", "--indir",
                  dest="indir",
                  help="Input file directory",
                  metavar="DIR")
    op.add_option("-o", "--outfile",
                  dest="outfile",
                  help="Output file",
                  metavar="FILE")
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

    parser = Parser()
    parser.parse(options.indir,args)
    parser.printNode(options.outfile)
    return(True)

if __name__=="__main__":
    interface()
