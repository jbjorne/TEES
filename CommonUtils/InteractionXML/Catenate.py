import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import RecalculateIds

def catenate(input1, input2, output):
    print >> sys.stderr, "##### Catenate interaction XML #####"
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
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-j", "--input2", default=None, dest="input2", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, first input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.input2 == None:
        print >> sys.stderr, "Error, second input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)
    
    catenate(options.input, options.input2, options.output)
