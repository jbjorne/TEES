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

    def parseText(self,input):
        self.text = input
        lines = input.split("\n")
        self.title = lines[0]
        self.abstract = lines[1]

    def parseAnnotation(self,lines,isName=True):
        for line in lines:
            if not line:
                continue
            uid,content = line.split("\t")
            if not content:
                sys.stderr.write("Unmatched line: '%s'"%line.strip())
                sys.exit(1)
            if uid[0]=="T":
                t,b,e = content.split(" ")
                if not self.entities.has_key(uid):
                    self.entities[uid] = {}
                self.entities[uid].update({'id':uid,
                                           'origId':uid,
                                           'charOffset':"%s-%s"%(b,int(e)-1),
                                           'text':self.text[int(b):int(e)],
                                           'type':t,
                                           'isName':str(isName)})
                self.mapping[uid] = 'rb.'+self.uid+'.'+self.counter.get()
            elif uid[0]=="*":
                t,e1,e2 = content.split(" ")
                if not self.events.has_key(uid):
                    self.events[uid] = []
                self.events[uid].append({'id':uid,
                                        'directed':'False',
                                        'e1':e1,
                                        'e2':e2,
                                        'type':t})
            elif uid[0]=="M":
                t,e = content.split(" ")
                if not self.modifiers.has_key(uid):
                    self.modifiers[uid] = {}
                self.modifiers[uid].update({'id':uid,
                                            'e1':e,
                                            'type':t})
            elif uid[0]=="E":
                t = content.split(" ")[0]
                args = content.split(" ")[1:]
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
            newEntity = ET.Element("entity",v)
            newEntity.attrib['origId'] = self.mapping[v['id']]
            newSentence.append(newEntity)
        for k,v in self.modifiers.items():
            newModifier = ET.Element("modifier",v)
            newSentence.append(newModifier)
        for k,v in self.events.items():
            for x in v:
                if x['e1'][0]==('E'):
                    x['e1'] = self.mapping[x['e1']]
                if x['e2'][0]==('E'):
                    x['e2'] = self.mapping[x['e2']]
                newEvent = ET.Element("pair",x)
                newSentence.append(newEvent)
        return(newDocument)

class Parser:
    def __init__(self):
        self.parsers = []

    def parse(self,filestems):
        for stem in filestems:
            tmp = SentenceParser()
            tmp.parse(stem)
            self.parsers.append(tmp)

    def getNode(self):
        newCorpus = ET.Element('corpus',{'source':'GENIA'})
        for x in self.parsers:
            newCorpus.append(x.getNode())
        return(newCorpus)

    def printNode(self):
        node = self.getNode()
        indent(node)
        print ET.tostring(node)

if __name__=="__main__":
    if len(sys.argv)<2:
        print "Please specify the stem as the first argument."
        print "\t<stem>.txt == original text"
        print "\t<stem>.a1 == protein annotation"
        print "\t<stem>.a2 == event annotation"
    else:
        parser = Parser()
        parser.parse(sys.argv[1:])
        parser.printNode()
