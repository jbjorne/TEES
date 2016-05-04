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
import DeleteElements

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

def catenateElements(inputs, inputDir):
    print >> sys.stderr, "##### Catenate interaction XML as elements #####"
    
    output = {}
    for dataSet in ("devel", "train"):
        root = ET.Element("corpus", {"source":",".join(inputs)})
        tree = ET.ElementTree(root)
        print "Processing corpus dataset", dataSet
        output[dataSet] = tree
        for input in inputs:
            corpusPath = os.path.join(inputDir, input + "-" + dataSet + ".xml")
            print >> sys.stderr, "Catenating", corpusPath
            if not os.path.exists(corpusPath):
                print "Input", corpusPath, "not found"
                continue
            xml = ETUtils.ETFromObj(corpusPath)
            for document in xml.getiterator("document"):
                root.append(document)
        RecalculateIds.recalculateIds(tree)
    
    return output

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
