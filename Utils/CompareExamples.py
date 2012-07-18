import itertools
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
from Utils.ProgressCounter import ProgressCounter 

def removeFeatures(example):
    return [example[0], example[1], {}, example[3]]

def getFeatureNames(example, featureIds):
    names = []
    for feature in sorted(example[2].keys()):
        name = featureIds.getName(feature)
        assert name != None
        names.append(name)
    return names

def compareExamples(examples1, examples2, features1, features2=None):
    ExampleUtils.readExamples(examples1)
    exampleIter1 = ExampleUtils.readExamples(examples1)
    exampleIter2 = ExampleUtils.readExamples(examples2)
    features1 = IdSet(filename=features1)
    if features2 != None:
        features2 = IdSet(filename=features2)
    else:
        features2 = features1
    # Compare feature sets
    if set(features1.Ids.keys()) != set(features2.Ids.keys()):
        print "Feature sets differ"
    # Compare examples
    counter = ProgressCounter(step=1)
    for e1, e2 in itertools.izip(exampleIter1, exampleIter2):
        counter.update()
        assert e1[0] == e2[0], (removeFeatures(e1), removeFeatures(e2))
        if e1[1] != e2[1]:
            print "Class differs"
            print "  E1", removeFeatures(e1)
            print "  E2", removeFeatures(e2)
        f1 = getFeatureNames(e1, features1)
        f2 = getFeatureNames(e2, features2)
        f1Set = set(f1)
        f2Set = set(f2)
        f1Only = f1Set.difference(f2Set)
        f2Only = f2Set.difference(f1Set)
        if len(f1Only) > 0 or len(f2Only) > 0:
            print "Features differ"
            print "  E1", removeFeatures(e1)
            print "  E2", removeFeatures(e2)
            if len(f1Only) > 0:
                print "  E1-only features:", f1Only
            if len(f2Only) > 0:
                print "  E2-only features:", f2Only
        else:
            assert len(f1) == len(f2)
            fCount = 0
            differ = False
            for feature1, feature2 in zip(f1, f2):
                #f1Id = features1.getId(feature1, createIfNotExist=False)
                #if f1Id == 454 or feature1 == "e1_strength_Positive_regulation":
                #    print "!!!!!!!!!!!", 454, feature1, e1[2][f1Id]
                if feature1 != feature2:
                    if not differ:
                        print "Feature order differs for example", e1[0]
                        differ = True
                    print "[" + feature1 + "/" + feature2 + "](" + str(fCount) + ") ",
                else:
                    f1Id = features1.getId(feature1, createIfNotExist=False)
                    f2Id = features2.getId(feature2, createIfNotExist=False)
                    f1Value = e1[2][f1Id]
                    f2Value = e2[2][f2Id]
                    if f1Value != f2Value:
                        if not differ:
                            print "Feature values differ", e1[0]
                            differ = True
                        print "[" + feature1 + "/" + str(f1Id) + "]" + "[" + str(f1Value) + "/" + str(f2Value) + "]" + "(" + str(fCount) + ") ",
                fCount += 1              
            if differ:
                print
    counter.endUpdate()

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser(description="Analyze SVM example files")
    optparser.add_option("-a", "--fileA", default=None, dest="fileA", help="")
    optparser.add_option("-b", "--fileB", default=None, dest="fileB", help="")
    optparser.add_option("-f", "--featureIds", default=None, dest="featureIds", help="")
    optparser.add_option("-g", "--featureIdsB", default=None, dest="featureIdsB", help="")
    (options, args) = optparser.parse_args()
    
    compareExamples(options.fileA, options.fileB, options.featureIds, options.featureIdsB)