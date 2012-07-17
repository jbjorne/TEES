import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils

def getFeatureNames(examples, featureIds):
    names = set()
    for example in examples:
        for feature, value in example[2].iteritems():
            names.add(featureIds.getName(feature))
    return names

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    import os
    optparser = OptionParser(description="Analyze SVM example files")
    optparser.add_option("-s", "--source", default=None, dest="source", help="examples", metavar="FILE")
    optparser.add_option("-t", "--target", default=None, dest="target", help="examples")
    optparser.add_option("-f", "--sourceFeatureIds", default=None, dest="sourceFeatureIds", help="examples", metavar="FILE")
    optparser.add_option("-g", "--targetFeatureIds", default=None, dest="targetFeatureIds", help="examples")
    (options, args) = optparser.parse_args()
    
    print "Loading ids"
    sFeatIds = IdSet(filename=options.sourceFeatureIds)
    tFeatIds = IdSet(filename=options.targetFeatureIds)
    print "Loading examples"
    sExamples = ExampleUtils.readExamples(options.source)
    tExamples = ExampleUtils.readExamples(options.target)
    print "Making name sets"
    s = getFeatureNames(sExamples, sFeatIds)
    t = getFeatureNames(tExamples, tFeatIds)
    print "Source features:", len(s)
    print "Target features:", len(t)
    print "Intersection:", len(s & t)
    onlyS = s - t
    onlyT = t - s
    print "Only source:", len(onlyS)
    print "Only target:", len(onlyT)
#    state = {}
#    for n in onlyS:
#        presence = state.setdefault(n, [0,0])
#        presence[0] = 1
#    for n in onlyT:
#        presence = state.setdefault(n, [0,0])
#        presence[1] = 1
#    for key in sorted(state.keys()):
#        print key, state[key]
    print "#Only Source:"
    for value in sorted(onlyS): 
        print value
    print "#Only Target:"
    for value in sorted(onlyT): 
        print value
    print "#Intersection:"
    for value in sorted(s & t): 
        print value
            
