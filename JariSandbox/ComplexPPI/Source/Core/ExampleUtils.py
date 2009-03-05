# example is a 3-tuple (or list) of the format: (id, class, features, extra). id is a string,
# class is an int (-1 or +1) and features is a dictionary of int:float -pairs, where
# the int is the feature id and the float is the feature value

import Split
import types

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
    for example in examples:
        file.write(str(example[1]))
        keys = example[2].keys()
        keys.sort()
        for key in keys:
            file.write(" " + str(key)+":"+str(example[2][key]))
        file.write(" # id:" + example[0])
        for extraKey, extraValue in example[3].iteritems():
            assert(extraKey != "id")
            if type(extraValue) == types.StringType:
                file.write( " " + str(extraKey) + ":" + extraValue)
        file.write("\n")

def writeExamples(examples, filename, commentLines=None):
    f = open(filename,"wt")
    if commentLines != None:
        for commentLine in commentLines:
            f.write("# "+commentLine+"\n")
    appendExamples(examples, f)
    f.close()

def writePredictions(predictions, exampleFileName):
    f = open(exampleFileName, "wt")
    exampleLines = f.readlines()
    f.close()
    for line in exampleLines:
        if line[0] != "#":
            break
        if line.find("#commentColumns:") != -1:
            pass

def getIdsFromFile(filename):
    f = open(filename,"rt")
    ids = []
    for line in f.readlines():
        if line[0] == "#":
            continue
        splits = line.rsplit("#", 1)
        ids.append( splits[-1].strip() )
    return ids

def readExamples(filename, readFeatures=True):
    f = open(filename,"rt")
    examples = []
    for line in f.readlines():
        if line[0] == "#":
            continue
        splits = line.split("#")
        commentSplits = splits[-1].split()
        id = None
        extra = {}
        for commentSplit in commentSplits:
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
        examples.append([id,classId,features,extra])
    return examples

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
    f = open(exampleFileName, "rt")
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

def writeToInteractionXML(classifications, corpusElements, outputFile, classSet=None):
    import sys
    print >> sys.stderr, "Writing output to Interaction XML"
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import cElementTree as ET
    import cElementTreeUtils as ETUtils
    
    print >> sys.stderr, "Grouping examples"
    classificationsBySentence = {}
    xType = None
    for classification in classifications:
        if xType == None:
            if classification[0][3].has_key("xtype"):
                xType = classification[0][3]["xtype"]
        else:
            assert(classification[0][3]["xtype"] == xType)
        exampleId = classification[0][0]
        sentenceId = exampleId.rsplit(".",1)[0]
        if not classificationsBySentence.has_key(sentenceId):
            classificationsBySentence[sentenceId] = []
        classificationsBySentence[sentenceId].append(classification)
    
    if classSet != None:
        classIds = classSet.getIds()
    
    print >> sys.stderr, "Processing sentence elements"
    sentenceElements = corpusElements.sentences
    for sentenceObject in sentenceElements:
        sentenceElement = sentenceObject.sentence
        sentenceId = sentenceElement.get("id")
        # detach analyses
        sentenceAnalysesElement = None
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        if sentenceAnalysesElement != None:
            sentenceElement.remove(sentenceAnalysesElement)
        # remove pairs and interactions
        pairElements = sentenceElement.findall("pair")
        if pairElements != None:
            for pairElement in pairElements:
                sentenceElement.remove(pairElement)
        interactionElements = sentenceElement.findall("interaction")
        if interactionElements != None:
            for interactionElement in interactionElements:
                sentenceElement.remove(interactionElement)
        # remove entities
        if xType == "token":
            entityElements = sentenceElement.findall("entity")
            entityCount = 0
            if entityElements != None:
                entityCount = len(entityElements) # get the count _before_ removing entities
                for entityElement in entityElements:
                    if entityElement.get("isName") == "False": # interaction word
                        sentenceElement.remove(entityElement)
            # add new pairs
            entityElements = sentenceElement.findall("entity")
            if classificationsBySentence.has_key(sentenceId):
                for classification in classificationsBySentence[sentenceId]:
                    example = classification[0]
                    entityElement = ET.Element("entity")
                    entityElement.attrib["isName"] = "False"
                    headToken = example[3]["t"]
                    for token in sentenceObject.tokens:
                        if token.get("id") == headToken:
                            headToken = token
                            break
                    entityElement.attrib["charOffset"] = headToken.get("charOffset") 
                    entityElement.attrib["headOffset"] = headToken.get("charOffset")
                    entityElement.attrib["text"] = headToken.get("text")
                    entityElement.attrib["id"] = sentenceId + ".e" + str(entityCount)
                    if classSet == None: # binary classification
                        if classification[1] == "tp" or classification[1] == "fp":
                            entityElement.attrib["type"] = str(True)
                        else:
                            entityElement.attrib["type"] = str(False)
                    else:
                        entityElement.attrib["type"] = classSet.getName(classification[3])
                        classWeights = classification[4]
                        predictionString = ""
                        for i in range(len(classWeights)):
                            if predictionString != "":
                                predictionString += ","
                            predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
                        entityElement.attrib["predictions"] = predictionString
                    #if entityElement.attrib["type"] != "neg":
                    sentenceElement.append(entityElement)
                    entityCount += 1
        elif xType == "edge":
            pairCount = 0
            if classificationsBySentence.has_key(sentenceId):
                for classification in classificationsBySentence[sentenceId]:
                    example = classification[0]
                    pairElement = ET.Element("interaction")
                    #pairElement.attrib["origId"] = origId
                    #pairElement.attrib["type"] = example[3]["categoryName"]
                    pairElement.attrib["directed"] = "Unknown"
                    pairElement.attrib["e1"] = example[3]["e1"] #.attrib["id"]
                    pairElement.attrib["e2"] = example[3]["e2"] #.attrib["id"]
                    pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                    if classSet == None: # binary classification
                        if classification[1] == "tp" or classification[1] == "fp":
                            pairElement.attrib["type"] = str(True)
                        else:
                            pairElement.attrib["type"] = str(False)
                    else:
                        pairElement.attrib["type"] = classSet.getName(classification[3])
                        classWeights = classification[4]
                        predictionString = ""
                        for i in range(len(classWeights)):
                            if predictionString != "":
                                predictionString += ","
                            predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
                        pairElement.attrib["predictions"] = predictionString
                    sentenceElement.append(pairElement)
                    pairCount += 1
        else:
            sys.exit("Error, unknown xtype")
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
    # Write corpus
    print >> sys.stderr, "Writing corpus to", outputFile
    ETUtils.write(corpusElements.rootElement, outputFile)
    