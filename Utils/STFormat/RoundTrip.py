from STTools import *
from ConvertXML import *
import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../JariSandbox/ComplexPPI/Source")))
import Tools.GeniaSentenceSplitter

def roundTrip(input, output, sentenceSplitter, workdir=None):
    if workdir != None and not os.path.exists(workdir):
        os.makedirs(workdir)
    print >> sys.stderr, "Loading STFormat"
    documents = loadSet(input)
    print >> sys.stderr, "Converting to Interaction XML"
    if workdir != None:
        xml = toInteractionXML(documents, "ER", os.path.join(workdir, "documents.xml"))
    else:
        xml = toInteractionXML(documents)
    print >> sys.stderr, "Splitting Sentences"
    if workdir != None:
        sentenceSplitter.makeSentences(xml, os.path.join(workdir, "sentences.xml"), postProcess=True)
    else:
        sentenceSplitter.makeSentences(xml)
    print >> sys.stderr, "Converting back to STFormat"
    documents = toSTFormat(xml)
    print >> sys.stderr, "Writing STFormat"
    writeSet(documents, output)

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

    optparser = OptionParser(description="Convert ST format to interaction XML and back")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-w", "--workdir", default=None, dest="workdir", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    roundTrip(input=options.input, output=options.output, sentenceSplitter=Tools.GeniaSentenceSplitter, workdir=options.workdir)
