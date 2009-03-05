import sys, os, shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
from Utils.ProgressCounter import ProgressCounter
from optparse import OptionParser

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--invariant", default=None, dest="invariant", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-v", "--variant", default=None, dest="variant", help="Corpus in analysis format", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    #invariantExamples = ExampleUtils.readExamples(os.path.join(options.invariant, "examples.txt"))
    variantExamples = ExampleUtils.readExamples(os.path.join(options.variant, "test-triggers.examples"))
    
    invariantFeatureSet = IdSet()
    invariantFeatureSet.load(os.path.join(options.invariant, "feature_names.txt"))
    invariantClassSet = IdSet()
    invariantClassSet.load(os.path.join(options.invariant, "class_names.txt"))

    variantFeatureSet = IdSet()
    variantFeatureSet.load(os.path.join(options.variant, "test-triggers.examples.feature_names"))
    variantClassSet = IdSet()
    variantClassSet.load(os.path.join(options.variant, "test-triggers.examples.class_names"))
    
    counter = ProgressCounter(len(variantExamples))
    for example in variantExamples:
        counter.update()
        example[1] = invariantClassSet.getId(variantClassSet.getName(example[1]))
        newFeatures = {}
        for k,v in example[2].iteritems():
            newFeatures[ invariantFeatureSet.getId(variantFeatureSet.getName(k)) ] = v
        example[2] = newFeatures
        
    ExampleUtils.writeExamples(variantExamples, os.path.join(options.variant, "realignedExamples.txt"))
