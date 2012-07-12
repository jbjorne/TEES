import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import gzip, codecs
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import RecalculateIds

def catenate(inputs, output, fast):
    if not os.path.exists(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))
    if fast:
        catenateFiles(inputs, output)
    else:
        catenateElements(inputs, output)
    return output
    
def catenateFiles(inputs, output):
    print >> sys.stderr, "##### Catenate interaction XML as files #####"
    assert len(inputs) > 1
    print >> sys.stderr, "Writing catenated XML to", output
    if output.endswith(".gz"):
        outFile = gzip.open(output, 'wb')
    else:
        outFile = open(output, "wb")
    outWriter = codecs.getwriter("utf-8")(outFile)
    for i in range(len(inputs)):
        print >> sys.stderr, "Catenating", inputs[i]
        if inputs[i].endswith(".gz"):
            f = gzip.open(inputs[i], 'rb')
        else:
            f = open(inputs[i], "rb")
        state = "BEGIN"
        for line in codecs.getreader("utf-8")(f):
            if "<corpus" in line:
                assert state == "BEGIN"
                state = "MIDDLE"
                if i > 0:
                    continue
            elif "</corpus" in line:
                assert state == "MIDDLE"
                state = "END"
            if state == "BEGIN" and i > 0:
                continue
            if state == "END" and i < len(inputs) - 1:
                continue
            outWriter.write(line)
        f.close()
    outFile.close()

def catenateElements(inputs, output):
    print >> sys.stderr, "##### Catenate interaction XML as elements #####"
    c1 = RecalculateIds.recalculateIds(input1, None, False, 0)
    numDocs = len(c1.getroot().findall("document"))
    print >> sys.stderr, "Documents in input 1:", numDocs
    c2 = RecalculateIds.recalculateIds(input2, None, False, numDocs)
    
    print >> sys.stderr, "Appending documents"
    c1Root = c1.getroot()
    for document in c2.getroot().findall("document"):
        c1Root.append(document)
    
    print >> sys.stderr, "Validating ids"
    ids = set()
    for element in c1Root.getiterator("entity"):
        id = element.get("id")
        assert not id in ids
        ids.add(id)
    for element in c1Root.getiterator("interaction"):
        id = element.get("id")
        assert not id in ids
        ids.add(id)
    for element in c1Root.getiterator("sentence"):
        id = element.get("id")
        assert not id in ids
        ids.add(id)
    for element in c1Root.getiterator("document"):
        id = element.get("id")
        assert not id in ids
        ids.add(id)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(c1Root, output)
    return c1

if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--inputs", default=None, dest="inputs", help="A comma-separated list of corpora in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-f", "--fast", default=False, action="store_true", dest="fast", help="Fast, but unsafe catenation")
    (options, args) = optparser.parse_args()
    
    if options.inputs == None:
        print >> sys.stderr, "Error, input files not defined."
        optparser.print_help()
        sys.exit(1)
    options.inputs = options.inputs.split(",")
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)
    
    catenate(options.inputs, options.output, options.fast)
