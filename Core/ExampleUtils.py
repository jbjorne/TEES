"""
Tools for writing and reading classifier example files

These functions read and write machine learning example files and convert
examples into final data forms. The memory representation for each
example is a 4-tuple (or list) of the format: (id, class, features, extra). id is a string,
class is an int (-1 or +1 for binary) and features is a dictionary of int:float -pairs, where
the int is the feature id and the float is the feature value.
Extra is a dictionary of String:String pairs, for additional information about the 
examples.
"""

import sys, os, itertools
import Split
import types
#from IdSet import IdSet
#thisPath = os.path.dirname(os.path.abspath(__file__))
#sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
#import Utils.InteractionXML.IDUtils as IDUtils
#import Utils.Libraries.combine as combine
import types
import gzip
#try:
#    import xml.etree.cElementTree as ET
#except ImportError:
#    import cElementTree as ET
#import Utils.ElementTreeUtils as ETUtils
import RecallAdjust

def gen2iterable(genfunc):
    """
    Makes a multi-use iterator generator. See http://bugs.python.org/issue5973
    for details.
    """
    def wrapper(*args, **kwargs):
        class _iterable(object):
            def __iter__(self):
                return genfunc(*args, **kwargs)
        return _iterable()
    return wrapper

def isDuplicate(example1, example2):
    if example1[1] != example2[1]:
        return False
    if example1[2] != example2[2]:
        return False
    return True

def removeDuplicates(examples):
    """ removes all but one of the examples that have the same class and identical feature vectors"""
    duplicateList = [False] * len(examples)
    for i in range(len(examples)):
        if not duplicateList[i]:
            for j in range(i+1, len(examples)):
                if not duplicateList[j]:
                    if isDuplicate(examples[i], examples[j]):
                        duplicateList[j] = True
    newExamples = []
    for i in range(len(examples)):
        if not duplicateList[i]:
            newExamples.append(examples[i])
    return newExamples

def normalizeFeatureVectors(examples):
    for example in examples:
        # Normalize features
        total = 0.0
        for v in example[2].values(): total += abs(v)
        if total == 0.0: 
            total = 1.0
        for k,v in example[2].iteritems():
            example[2][k] = float(v) / total

def copyExamples(examples):
    examplesCopy = []
    for example in examples:
        examplesCopy.append([example[0], example[1], example[2].copy(), example[3]])
    return examplesCopy

def appendExamples(examples, file):
    noneClassCount = 0
    for example in examples:
        # None-value as a class indicates a class that did not match an existing id,
        # in situations where new ids cannot be defined, such as predicting. An example
        # with class == None should never get this far, ideally it should be filtered
        # in the ExampleBuilder, but this at least prevents a crash.
        if example[1] == None:
            noneClassCount += 1
            continue
        # Write class
        file.write(str(example[1]))
        # Get and sort feature ids
        keys = example[2].keys()
        keys.sort()
        # None-value as a key indicates a feature that did not match an existing id,
        # in situations where new ids cannot be defined, such as predicting
        if None in example[2]:
            keys.remove(None)
        # Write features
        for key in keys:
            file.write(" " + str(key)+":"+str(example[2][key]))
        # Write comment area
        file.write(" # id:" + example[0])
        for extraKey, extraValue in example[3].iteritems():
            assert(extraKey != "id") # id must be defined as example[0]
            if type(extraValue) in types.StringTypes:
                file.write( " " + str(extraKey) + ":" + extraValue)
        file.write("\n")
    if noneClassCount != 0: 
        print >> sys.stderr, "Warning,", noneClassCount, "examples had an undefined class."

def appendExamplesBinary(examples, file):
    import struct
    for example in examples:
        #file.write(str(example[1]))
        keys = example[2].keys()
        keys.sort()
        file.write(struct.pack("1i", len(keys)))
        file.write(struct.pack(str(len(keys))+"i", *keys))
        #for key in keys:
        #    file.write(" " + str(key)+":"+str(example[2][key]))
        #file.write(" # id:" + example[0])
        #for extraKey, extraValue in example[3].iteritems():
        #    assert(extraKey != "id")
        #    if type(extraValue) == types.StringType:
        #        file.write( " " + str(extraKey) + ":" + extraValue)
        #file.write("\n")

def writeExamples(examples, filename, commentLines=None):
    if filename.endswith(".gz"):
        f = gzip.open(filename,"wt")
    else:
        f = open(filename,"wt")
    if commentLines != None:
        for commentLine in commentLines:
            f.write("# "+commentLine+"\n")
    appendExamples(examples, f)
    f.close()

def writePredictions(predictions, exampleFileName):
    if exampleFileName.endswith(".gz"):
        f = gzip.open(exampleFileName,"wt")
    else:
        f = open(exampleFileName,"wt")
    exampleLines = f.readlines()
    f.close()
    for line in exampleLines:
        if line[0] != "#":
            break
        if line.find("#commentColumns:") != -1:
            pass

def getIdsFromFile(filename):
    if filename.endswith(".gz"):
        f = gzip.open(filename,"rt")
    else:
        f = open(filename,"rt")
    ids = []
    for line in f.readlines():
        if line[0] == "#":
            continue
        splits = line.rsplit("#", 1)
        ids.append( splits[-1].strip() )
    return ids

@gen2iterable
def readExamples(filename, readFeatures=True):
    if filename.endswith(".gz"):
        f = gzip.open(filename,"rt")
    else:
        f = open(filename,"rt")
    #try:
    for line in f:
        if line[0] == "#":
            continue
        splits = line.split("#")
        commentSplits = splits[-1].split()
        id = None
        extra = {}
        for commentSplit in commentSplits:
            #if commentSplit.find("id:") == -1:
            #    continue
            key, value = commentSplit.split(":")
            if key == "id":
                id = value
            else:
                extra[key] = value
        splits2 = splits[0].split()
        classId = int(splits2[0])
        features = {}
        if readFeatures:
            for item in splits2[1:]:
                featureId, featureValue = item.split(":")
                features[int(featureId)] = float(featureValue)
        yield [id,classId,features,extra]
    #finally:
    f.close()
    
def makeCorpusDivision(corpusElements, fraction=0.5, seed=0):
    documentIds = corpusElements.documentsById.keys()
    return makeDivision(documentIds, fraction, seed)

def makeCorpusFolds(corpusElements, folds=10):
    documentIds = corpusElements.documentsById.keys()
    return makeFolds(documentIds, folds)

def makeExampleDivision(examples, fraction=0.5):
    documentIds = set()
    for example in examples:
        documentIds.add(example[0].rsplit(".",2)[0])
    documentIds = list(documentIds)
    return makeDivision(documentIds, fraction)

def makeExampleFolds(examples, folds=10):
    documentIds = set()
    for example in examples:
        documentIds.add(example[0].rsplit(".",2)[0])
    documentIds = list(documentIds)
    return makeFolds(documentIds, folds)

def makeDivision(ids, fraction=0.5, seed=0):
    sample = Split.getSample(len(ids),fraction, seed)
    division = {}
    for i in range(len(ids)): 
        division[ids[i]] = sample[i]
    return division

def makeFolds(ids, folds=10):
    sample = Split.getFolds(len(ids),folds)
    division = {}
    for i in range(len(ids)): 
        division[ids[i]] = sample[i]
    return division

def divideExamples(examples, division=None):
    if division == None:
        division = makeExampleDivision(examples)
    
    exampleSets = {}
    for example in examples:
        documentId = example[0].rsplit(".",2)[0]
        if division.has_key(documentId):
            if not exampleSets.has_key(division[documentId]):
                exampleSets[division[documentId]] = []
            exampleSets[division[documentId]].append(example)
    return exampleSets

def divideExampleFile(exampleFileName, division, outputDir):
    if exampleFileName.endswith(".gz"):
        f = gzip.open(exampleFileName,"rt")
    else:
        f = open(exampleFileName,"rt")
    lines = f.readlines()
    f.close()
    
    divisionFiles = {}
    for line in lines:
        if line[0] == "#":
            continue
        id = line.split("#")[-1].strip()
        documentId = id.rsplit(".",2)[0]
        if not divisionFiles.has_key(division[documentId]):
            divisionFiles[division[documentId]] = open(outputDir+"/set"+str(division[documentId]),"wt")
        divisionFiles[division[documentId]].write(line)
    for v in divisionFiles.values():
        v.close()

#@gen2iterable        
#def loadPredictions(predictionsFile):
#    if predictionsFile.endswith(".gz"):
#        f = gzip.open(predictionsFile,"rt")
#    else:
#        f = open(predictionsFile,"rt")
#    #try:
#    for line in f:
#        splits = line.split()
#        if len(splits) == 1:
#            yield [float(splits[0])]
#        else: # multiclass
#            if "," in splits[0]: # multilabel
#                pred = [[]]
#                for value in splits[0].split(","):
#                    pred[0].append(int(value))
#            else:
#                pred = [int(splits[0])]
#            for split in splits[1:]:
#                if split != "N/A":
#                    split = float(split)
#                pred.append(split)
#            yield pred
#    #finally:
#    f.close()

@gen2iterable        
def loadPredictions(predictionsFile, recallAdjust=None, classRanges=None, threshold=None):
    if predictionsFile.endswith(".gz"):
        f = gzip.open(predictionsFile,"rt")
    else:
        f = open(predictionsFile,"rt")
    #try:
    for line in f:
        splits = line.split()
        if len(splits) == 1: # true binary
            assert recallAdjust == None or recallAdjust == 1.0 # not implemented for binary classification
            yield [float(splits[0])]
        elif len(splits) == 3 and (recallAdjust != None and recallAdjust != 1.0) and classRanges == None: # SVM multiclass two class "binary" classification
            # Go through all the predictions to get the ranges
            predictions = [splits]
            for line in f:
                predictions.append(line.split())
            f.close() # end first iteration
            classRanges = RecallAdjust.getClassRangesFromPredictions(predictions)
            # Load predictions again with the range information
            for yieldedValue in loadPredictions(predictionsFile, recallAdjust, classRanges):
                yield yieldedValue
            break
        else: # multiclass
            if "," in splits[0]: # multilabel
                pred = [[]]
                for value in splits[0].split(","):
                    pred[0].append(int(value))
            else:
                pred = [int(splits[0])]
            for split in splits[1:]:
                if split != "N/A":
                    split = float(split)
                pred.append(split)
            # Recall adjust
            if recallAdjust != None and recallAdjust != 1.0:
                if classRanges == None:
                    pred[1] = RecallAdjust.scaleVal(pred[1], recallAdjust)
                else: # SVM multiclass two class "binary" classification 
                    pred[1] = RecallAdjust.scaleRange(pred[1], recallAdjust, classRanges[1])
                #if pred[0] == 1:
                maxStrength = pred[1]
                pred[0] = 1
                for i in range(2, len(pred)):
                    if pred[i] > maxStrength:
                        maxStrength = pred[i]
                        pred[0] = i
            # Thresholding
            if threshold != None:
                if pred[1] > threshold:
                    pred[0] = 1
                else:
                    maxStrength = pred[2]
                    pred[0] = 2
                    for i in range(2, len(pred)):
                        if pred[i] > maxStrength:
                            maxStrength = pred[i]
                            pred[0] = i       
            # Return the prediction
            yield pred
    #finally:
    f.close()