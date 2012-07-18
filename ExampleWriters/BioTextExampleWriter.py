"""
Wrapper for all interaction XML example writers
"""
import sys, os, types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Core.ExampleUtils as ExampleUtils

from EntityExampleWriter import EntityExampleWriter
from EdgeExampleWriter import EdgeExampleWriter
from ModifierExampleWriter import ModifierExampleWriter
from PhraseTriggerExampleWriter import PhraseTriggerExampleWriter
#IF LOCAL
from UnmergingExampleWriter import UnmergingExampleWriter
#from UnmergedEdgeExampleWriter import UnmergedEdgeExampleWriter
#from AsymmetricEventExampleWriter import AsymmetricEventExampleWriter
#ENDIF

class BioTextExampleWriter:
    """
    A generic example writer that automatically calls the correct Example Writer
    based on the type of the examples.
    """
    @classmethod
    def write(cls, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None, goldCorpus=None, insertWeights=False):
        if type(examples) == types.StringType:
            print >> sys.stderr, "Reading examples from", examples
            examples = ExampleUtils.readExamples(examples, False)
        
        # This looks a bit strange, but should work with the re-iterable
        # generators that readExamples returns
        xType = None
        for example in examples:
            assert example[3].has_key("xtype")
            xType = example[3]["xtype"]
            break
        
        if xType == "token":
            w = EntityExampleWriter()
            if insertWeights:
                w.insertWeights = True
        elif xType == "edge":
            w = EdgeExampleWriter()
        elif xType == "task3":
            w = ModifierExampleWriter()
        elif xType == "entRel":
            w = EntityRelationExampleWriter()
        elif xType == "phrase":
            w = PhraseTriggerExampleWriter()
#IF LOCAL
        elif xType == "um":
            w = UnmergingExampleWriter()
        #elif xType == "ue":
        #    w = UnmergedEdgeExampleWriter()
        #elif xType == "asym":
        #    w = AsymmetricEventExampleWriter()
#ENDIF
        else:
            assert False, ("Unknown entity type", xType)
        return w.writeXML(examples, predictions, corpus, outputFile, classSet, parse, tokenization, goldCorpus=goldCorpus)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nWrite predicted examples to interaction XML")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="Machine learning example file", metavar="FILE")
    optparser.add_option("-p", "--predictions", default=None, dest="predictions", help="Classifier predictions for the example file", metavar="FILE")
    optparser.add_option("-i", "--classIds", default=None, dest="classIds", help="Multiclass class Ids")
    optparser.add_option("-c", "--corpus", default=None, dest="corpus", help="Interaction XML file for adding examples to", metavar="FILE")
    optparser.add_option("-g", "--goldCorpus", default=None, dest="goldCorpus", help="Interaction XML file with gold elements", metavar="FILE")
    optparser.add_option("-a", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file")
    optparser.add_option("-w", "--insertWeights", default=False, action="store_true", dest="insertWeights", help="Write weights for gold elements")
    #optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    (options, args) = optparser.parse_args()
    
    assert(options.examples != None)
    assert(options.predictions != None)
    assert(options.classIds != None)
    assert(options.corpus != None)
    assert(options.output != None)
    
    BioTextExampleWriter.write(options.examples, options.predictions, options.corpus, options.output, options.classIds, options.parse, options.tokenization, options.goldCorpus, insertWeights = options.insertWeights)
   