import sys
import networkx as NX
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

class Pruner:
    def __init__(self,document):
        self.data = [(x,
                      [y for y in x.findall('entity')],
                      [z for z in x.findall('interaction')])
                     for x in document.findall('sentence')]

    def prune(self):
        def subsuper(n1,n2):
            # mask ids
            n1Data = n1.attrib.copy()
            del n1Data['id']
            del n1Data['origId']
            n2Data = n2.attrib.copy()
            del n2Data['id']
            del n2Data['origId']
            if (n1Data==n2Data and
                not [x for x in edges
                     if x.attrib['e2']==n1.attrib['id']]):
                # no in-edges allowed for the duplicate
                return(matchEdges(n1,n2))
            return(False)
        def matchEdges(n1,n2):
            i1 = [x.attrib.copy() for x in edges
                  if x.attrib['e1']==n1.attrib['id']]
            i2 = [x.attrib.copy() for x in edges
                  if x.attrib['e1']==n2.attrib['id']]
            # mask interaction ids and parent ids
            # that is, children ids should match
            for x in i1:
                del x['id']
                del x['e1']
                del x['origId']
            for x in i2:
                del x['id']
                del x['e1']
                del x['origId']
            for x in i1:
                if not x in i2:
                    return(False)
                i2.remove(x)
            return(True)
        def remove(n):
            sys.stderr.write("Removing %s\n"%n.attrib['id'])
            sentence.remove(n)
            for x in edges:
                if x.attrib['e1']==n.attrib['id']:
                    sys.stderr.write("Removing %s\n"%x.attrib['id'])
                    sentence.remove(x)
        
        for sentence,nodes,edges in self.data:
            while nodes:
                prev = nodes.pop()
                for curr in nodes:
                    # if previous is sub
                    # remove it and take the next into consideration
                    if subsuper(prev,curr):
                        sys.stderr.write("Match: %s is sub of %s\n"%(prev.attrib['id'],
                                                                     curr.attrib['id']))
                        remove(prev)
                        break
                    # if previous is super
                    # remove the other and continue with the previous
                    if subsuper(curr,prev):
                        sys.stderr.write("Match: %s is super of %s\n"%(prev.attrib['id'],
                                                                       curr.attrib['id']))
                        remove(curr)
                        nodes.remove(curr)



def interface(optionArgs=sys.argv[1:]):
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nGenia shared task specific removal of noise.")
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
        sys.stderr.write("Cleaning document %s\n"%document.attrib['id'])
        processor = Pruner(document)
        processor.prune()
    indent(corpus.getroot())
    corpus.write(options.outfile)

if __name__=="__main__":
    interface()
