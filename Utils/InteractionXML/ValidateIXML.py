import sys, os
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
sys.path.append(extraPath)
import Utils.ElementTreeUtils as ETUtils
    
def validate(parent):
    attrib = parent.attrib
    for key in attrib:
        if not isinstance(attrib[key], basestring):
            raise Exception("Non-string value '" + str(attrib[key]) + "' for attribute '" + str(key) + "' in element '" + parent.tag + "': " + str(attrib) + "'")
    for element in parent.getchildren():
        validate(element)

def validateCorpus(input, output):
    print >> sys.stderr, "Validating XML"
    print >> sys.stderr, "Loading corpus file", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    validate(corpusRoot)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Validate #####"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)

    validateCorpus(options.input, options.output)
