import sys, os, types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import ExampleUtils

from EntityExampleWriter import EntityExampleWriter
from EdgeExampleWriter import EdgeExampleWriter
from Task3ExampleWriter import Task3ExampleWriter
from UnmergedEdgeExampleWriter import UnmergedEdgeExampleWriter

class BioTextExampleWriter:
    @classmethod
    def write(cls, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None):
        if type(examples) == types.StringType:
            print >> sys.stderr, "Reading examples from", examples
            examples = ExampleUtils.readExamples(examples, False)
        
        # This looks a bit strange, but should work with the re-iterable
        # generators that readExamples returns
        for example in examples:
            assert example[3].has_key("xtype")
            xType = example[3]["xtype"]
            break
        
        if xType == "token":
            w = EntityExampleWriter()
        elif xType == "edge":
            w = EdgeExampleWriter()
        elif xType == "task3":
            w = Task3ExampleWriter()
        elif xType == "ue":
            w = UnmergedEdgeExampleWriter()
        else:
            assert False, ("Unknown entity type", xType)
        return w.writeXML(examples, predictions, corpus, outputFile, classSet, parse, tokenization)
   