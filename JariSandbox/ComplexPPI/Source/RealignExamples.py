import sys, os, shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import Core.ExampleUtils as Example
import Core.IdSet as IdSet
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
    
    for example in variantExamples:
        example[1] = invariantClassSet.getId(variantClassSet.getName(example[1]))
        for k,v in example[2]:
            del example[2][k]
            example[2][ invariantFeatureSet.getId(variantFeatureSet.getName(k)) ] = v
    
    ExampleUtils.writeExamples(os.path.join(options.variant, "realignedExamples.txt"))
