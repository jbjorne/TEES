# example is a 4-tuple (or list) of the format: (id, class, features, extra). id is a string,
# class is an int (-1 or +1 for binary) and features is a dictionary of int:float -pairs, where
# the int is the feature id and the float is the feature value.
# Extra is a dictionary of String:String pairs, for additional information about the 
# examples.

import sys, os
import Split
import types
from IdSet import IdSet
import InteractionXML.IDUtils as IDUtils
import combine
import types
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

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
    strMap = {}
    try:
        for line in f:
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
                    value = strMap.setdefault(value, value)
                    extra[key] = value
            splits2 = splits[0].split()
            classId = int(splits2[0])
            features = {}
            if readFeatures:
                for item in splits2[1:]:
                    featureId, featureValue = item.split(":")
                    features[int(featureId)] = float(featureValue)
            yield [id,classId,features,extra]
    finally:
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
        
def loadPredictions(predictionsFile):
    f = open(predictionsFile, "rt")
    try:
        for line in f:
            splits = line.split()
            if len(splits) == 1:
                yield [float(splits[0])]
            else: # multiclass
                pred = [int(splits[0])]
                for split in splits[1:]:
                    pred.append(float(split))
                yield pred
                #predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass",lines[i].split()[1:]) )
    finally:
        f.close()

def writeTask3ToInteractionXML(classifications, corpusElements, outputFileName, task3Type):
    import sys
    print >> sys.stderr, "Adding task 3 to Interaction XML"
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import cElementTree as ET
    import cElementTreeUtils as ETUtils
    
    assert task3Type == "speculation" or task3Type == "negation"
    
    corpusTree = ETUtils.ETFromObj(corpusElements)
    corpusRoot = corpusTree.getroot()
    
    specMap = {}
    negMap = {}
    for classification in classifications:
        assert classification[0][3]["xtype"] == "task3"
        if classification[0][3]["t3type"] == "speculation":
            map = specMap
        else:
            map = negMap
        if classification[3] != 1:
            assert not map.has_key(classification[0][3]["entity"])
            map[classification[0][3]["entity"]] = True
    
    for entity in corpusRoot.getiterator("entity"):
        if task3Type == "speculation":
            if specMap.has_key(entity.get("id")):
                entity.set("speculation", "True")
            else:
                entity.set("speculation", "False")
        elif task3Type == "negation":
            if negMap.has_key(entity.get("id")):
                entity.set("negation", "True")
            else:
                entity.set("negation", "False")
    
    ETUtils.write(corpusRoot, outputFileName)

def writeToInteractionXML(examples, predictions, corpusElements, outputFile, classSet=None, parse=None, tokenization=None):
    import sys
    #print >> sys.stderr, "Writing output to Interaction XML"
    
    if type(corpusElements) == types.StringType or isinstance(corpusElements,ET.ElementTree): # corpus is in file
        import SentenceGraph
        corpusElements = SentenceGraph.loadCorpus(corpusElements, parse, tokenization)
    
    if type(classSet) == types.StringType: # class names are in file
        classSet = IdSet(filename=classSet)
    
    if type(predictions) == types.StringType:
        print >> sys.stderr, "Loading predictions from", predictions
        predictions = loadPredictions(predictions)
    if type(examples) == types.StringType:
        print >> sys.stderr, "Loading examples from", examples
        examples = readExamples(examples, False)
    
    #print >> sys.stderr, "Grouping examples"
    examplesBySentence = {}
    predictionsByExample = {}
    xType = None
    assert len(examples) == len(predictions)
    if len(examples) == 0:
        xType = "noExamples"
    for i in range(len(examples)):
        example = examples[i]
        if xType == None:
            if example[3].has_key("xtype"):
                xType = example[3]["xtype"]
        else:
            assert(example[3]["xtype"] == xType)
        exampleId = example[0]
        sentenceId = exampleId.rsplit(".",1)[0]
        if not examplesBySentence.has_key(sentenceId):
            examplesBySentence[sentenceId] = []
        examplesBySentence[sentenceId].append(example)
        assert not predictionsByExample.has_key(exampleId)
        predictionsByExample[exampleId] = predictions[i]
    
    if classSet != None:
        classIds = classSet.getIds()
    
    #print >> sys.stderr, "Processing sentence elements"
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
            newEntityIdCount = IDUtils.getNextFreeId(entityElements)
            if examplesBySentence.has_key(sentenceId):
                for example in examplesBySentence[sentenceId]:
                    prediction = predictionsByExample[example[0]]
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
                    entityElement.attrib["id"] = sentenceId + ".e" + str(newEntityIdCount)
                    newEntityIdCount += 1
                    if classSet == None: # binary classification
                        if prediction[0] > 0:
                            entityElement.attrib["type"] = str(True)
                        else:
                            entityElement.attrib["type"] = str(False)
                    else:
                        entityElement.attrib["type"] = classSet.getName(prediction[0])
                        classWeights = prediction[1:]
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
            if examplesBySentence.has_key(sentenceId):
                for example in examplesBySentence[sentenceId]:
                    prediction = predictionsByExample[example[0]]
                    pairElement = ET.Element("interaction")
                    #pairElement.attrib["origId"] = origId
                    #pairElement.attrib["type"] = example[3]["categoryName"]
                    pairElement.attrib["directed"] = "Unknown"
                    pairElement.attrib["e1"] = example[3]["e1"] #.attrib["id"]
                    pairElement.attrib["e2"] = example[3]["e2"] #.attrib["id"]
                    pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                    if classSet == None: # binary classification
                        if prediction[0] > 0:
                            pairElement.attrib["type"] = str(True)
                        else:
                            pairElement.attrib["type"] = str(False)
                    else:
                        pairElement.attrib["type"] = classSet.getName(prediction[0])
                        classWeights = prediction[1:]
                        predictionString = ""
                        for i in range(len(classWeights)):
                            if predictionString != "":
                                predictionString += ","
                            predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
                        pairElement.attrib["predictions"] = predictionString
                    sentenceElement.append(pairElement)
                    pairCount += 1
        elif xType == "trigger-event":
            eventsByToken = {}
            existingEntities = set()
            entityElements = sentenceElement.findall("entity")
            entityCount = 0
            pairCount = 0
            if entityElements != None:
                entityCount = len(entityElements) # get the count _before_ removing entities
                for entityElement in entityElements:
                    if entityElement.get("isName") == "False": # interaction word
                        sentenceElement.remove(entityElement)
                    else:
                        existingEntities.add(entityElement.get("id"))
            # add new pairs
            entityElements = sentenceElement.findall("entity")
            newEntityIdCount = IDUtils.getNextFreeId(entityElements)
            if examplesBySentence.has_key(sentenceId):
                eventIdByExample = {}
                newEntities = []
                for example in examplesBySentence[sentenceId]:
                    prediction = predictionsByExample[example[0]]
                    if prediction[0] == 1:
                        continue
                    entityElement = ET.Element("entity")
                    newEntities.append(entityElement)
                    entityElement.attrib["isName"] = "False"
                    headToken = example[3]["et"]
                    for token in sentenceObject.tokens:
                        if token.get("id") == headToken:
                            headToken = token
                            break
                    entityElement.attrib["charOffset"] = headToken.get("charOffset") 
                    entityElement.attrib["headOffset"] = headToken.get("charOffset")
                    entityElement.attrib["text"] = headToken.get("text")
                    entityElement.attrib["id"] = sentenceId + ".e" + str(newEntityIdCount)
                    newEntityIdCount += 1
                    eventIdByExample[example[0]] = entityElement.get("id")
                    
                    #if not eventByOrigId.has_key(example[3]["e"]):
                    #    eventByOrigId[example[3]["e"]] = []
                    #eventByOrigId[example[3]["e"]].append(entityElement.attrib["id"])
                    #example[3]["e"] = entityElement.attrib["id"]
                    
                    
                    if not eventsByToken.has_key(example[3]["et"]):
                        eventsByToken[example[3]["et"]] = []
                    eventsByToken[example[3]["et"]].append(entityElement.get("id"))

                    entityElement.attrib["type"] = example[3]["type"]
                    classWeights = prediction[1:]
                    predictionString = ""
                    for i in range(len(classWeights)):
                        if predictionString != "":
                            predictionString += ","
                        predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
                    entityElement.attrib["predictions"] = predictionString
                    #if entityElement.attrib["type"] != "neg":
                    sentenceElement.append(entityElement)
                    entityCount += 1
                    
                for example in examplesBySentence[sentenceId]:
                    prediction = predictionsByExample[example[0]]
                    if prediction[0] == 1:
                        continue
                    # add theme edge
                    if example[3].has_key("t"):
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = eventIdByExample[example[0]]
                        if eventsByToken.has_key(example[3]["tt"]):
                            pairElement.attrib["e2"] = eventsByToken[example[3]["tt"]][0]
                        else:
                            if example[3]["t"] in existingEntities:
                                pairElement.attrib["e2"] = example[3]["t"] #.attrib["id"]
                        pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                        pairElement.attrib["type"] = "Theme"
                        if pairElement.get("e2") != None:
                            sentenceElement.append(pairElement)
                            pairCount += 1
                    
                    # add cause edge
                    if example[3].has_key("c"):
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = eventIdByExample[example[0]]
                        if eventsByToken.has_key(example[3]["ct"]):
                            pairElement.attrib["e2"] = eventsByToken[example[3]["ct"]][0]
                        else:
                            if example[3]["c"] in existingEntities:
                                pairElement.attrib["e2"] = example[3]["c"] #.attrib["id"]
                        pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                        pairElement.attrib["type"] = "Cause"
                        if pairElement.get("e2") != None:
                            sentenceElement.append(pairElement)
                            pairCount += 1
#                    classWeights = prediction[1:]
#                    predictionString = ""
#                    for i in range(len(classWeights)):
#                        if predictionString != "":
#                            predictionString += ","
#                        predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
#                    pairElement.attrib["predictions"] = predictionString
        elif xType == "event":
            if True:
                process(sentenceObject, examplesBySentence, classSet, classIds, predictionsByExample)
            else:
                eventsByToken = {}
                existingEntities = set()
                entityElements = sentenceElement.findall("entity")
                entityCount = 0
                pairCount = 0
                if entityElements != None:
                    entityCount = len(entityElements) # get the count _before_ removing entities
                    for entityElement in entityElements:
                        if entityElement.get("isName") == "False": # interaction word
                            sentenceElement.remove(entityElement)
                        else:
                            existingEntities.add(entityElement.get("id"))
                # add new pairs
                entityElements = sentenceElement.findall("entity")
                newEntityIdCount = IDUtils.getNextFreeId(entityElements)
                if examplesBySentence.has_key(sentenceId):
                    # split merged examples
                    for example in examplesBySentence[sentenceId][:]:
                        prediction = predictionsByExample[example[0]]
                        if classSet.getName(prediction[0]).find("---") != -1:
                            nameSplits = classSet.getName(prediction[0]).split("---")
                            prediction[0] = classSet.getId(nameSplits[0], False)
                            count = 1
                            for nameSplit in nameSplits[1:]:
                                newExample = example[:]
                                newExample[0] += ".dupl" + str(count)
                                examplesBySentence[sentenceId].append(newExample)
                                newPrediction = prediction[:]
                                newPrediction[0] = classSet.getId(nameSplit, False)
                                predictionsByExample[newExample[0]] = newPrediction
                                count += 1
                    
                    # the rest of the stuff
                    eventIdByExample = {}
                    newEntities = []
                    for example in examplesBySentence[sentenceId]:
                        prediction = predictionsByExample[example[0]]
                        if prediction[0] == 1:
                            continue
                        entityElement = ET.Element("entity")
                        newEntities.append(entityElement)
                        entityElement.attrib["isName"] = "False"
                        headToken = example[3]["et"]
                        for token in sentenceObject.tokens:
                            if token.get("id") == headToken:
                                headToken = token
                                break
                        entityElement.attrib["charOffset"] = headToken.get("charOffset") 
                        entityElement.attrib["headOffset"] = headToken.get("charOffset")
                        entityElement.attrib["text"] = headToken.get("text")
                        entityElement.attrib["id"] = sentenceId + ".e" + str(newEntityIdCount)
                        newEntityIdCount += 1
                        eventIdByExample[example[0]] = entityElement.get("id")
                        
                        #if not eventByOrigId.has_key(example[3]["e"]):
                        #    eventByOrigId[example[3]["e"]] = []
                        #eventByOrigId[example[3]["e"]].append(entityElement.attrib["id"])
                        #example[3]["e"] = entityElement.attrib["id"]
                        
                        
                        if not eventsByToken.has_key(example[3]["et"]):
                            eventsByToken[example[3]["et"]] = []
                        eventsByToken[example[3]["et"]].append(entityElement.get("id"))
    
                        entityElement.attrib["type"] = classSet.getName(prediction[0]) #example[3]["type"]
                        classWeights = prediction[1:]
                        predictionString = ""
                        for i in range(len(classWeights)):
                            if predictionString != "":
                                predictionString += ","
                            predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
                        entityElement.attrib["predictions"] = predictionString
                        #if entityElement.attrib["type"] != "neg":
                        sentenceElement.append(entityElement)
                        entityCount += 1
                        
                    for example in examplesBySentence[sentenceId]:
                        prediction = predictionsByExample[example[0]]
                        if prediction[0] == 1:
                            continue
                        # add theme edge
                        if example[3].has_key("tt"):
                            pairElement = ET.Element("interaction")
                            pairElement.attrib["directed"] = "Unknown"
                            pairElement.attrib["e1"] = eventIdByExample[example[0]]
                            if eventsByToken.has_key(example[3]["tt"]):
                                pairElement.attrib["e2"] = eventsByToken[example[3]["tt"]][0]
                            elif example[3].has_key("t") and example[3]["t"] in existingEntities:
                                pairElement.attrib["e2"] = example[3]["t"] #.attrib["id"]
                            pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                            pairElement.attrib["type"] = "Theme"
                            if pairElement.get("e2") != None:
                                sentenceElement.append(pairElement)
                                pairCount += 1
                        
                        # add cause edge
                        if example[3].has_key("ct"):
                            pairElement = ET.Element("interaction")
                            pairElement.attrib["directed"] = "Unknown"
                            pairElement.attrib["e1"] = eventIdByExample[example[0]]
                            if eventsByToken.has_key(example[3]["ct"]):
                                pairElement.attrib["e2"] = eventsByToken[example[3]["ct"]][0]
                            elif example[3].has_key("c") and example[3]["c"] in existingEntities:
                                pairElement.attrib["e2"] = example[3]["c"] #.attrib["id"]
                            pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                            pairElement.attrib["type"] = "Cause"
                            if pairElement.get("e2") != None:
                                sentenceElement.append(pairElement)
                                pairCount += 1
        elif xType == "noExamples":
            pass
        else:
            sys.exit("Error, unknown xtype")
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
    # Write corpus
    if outputFile != None:
        print >> sys.stderr, "Writing corpus to", outputFile
        ETUtils.write(corpusElements.rootElement, outputFile)
    return corpusElements.tree

def getTokenById(id, sentenceObject):
    for token in sentenceObject.tokens:
        if token.get("id") == id:
            return token

#map[token][example][dup, final]

def addExamples(map, examples):
    for example in examples:
        eTokId = example[3]["et"]
        if not map.has_key(eTokId): map[eTokId] = {}
        exId = example[0]
        map[eTokId][exId] = [1, False, example, []] # [number of duplicates, marked final, example, entity elements]
        if example[3].has_key("tt"):
            ids = example[3]["tt"]
            if ids.find(","): ids = ids.split(",")
            else: ids = [ids]
            for id in ids:
                assert id in map.keys(), (id, example[0], example[3], sorted(map.keys()))
        if example[3].has_key("ct"):
            ids = example[3]["ct"]
            if ids.find(","): ids = ids.split(",")
            else: ids = [ids]
            for id in ids:
                assert id in map.keys(), (id, example[0], example[3], sorted(map.keys()))
        
def addExistingEntities(map, entities, sentenceObject):
    count = 0
    for entity in entities:
        headTokenOffset = entity.get("headOffset")
        headToken = None
        for tokenElement in sentenceObject.tokens:
            if tokenElement.get("charOffset") == headTokenOffset:
                headToken = tokenElement
                break
        assert headToken != None
        eTokId = headToken.get("id")
        if not map.has_key(eTokId): map[eTokId] = {}
        exId = "name" + str(count)
        map[eTokId][exId] = [1, True, None, [entity]] # [number of duplicates, marked final, example, entity elements]
        count += 1
        
def isFinal(token, map):
    assert map.has_key(token), (token, sorted(map.keys()))
    for exId in sorted(map[token].keys()):
        if map[token][exId][1] == False:
            return False
    return True

def getCount(token, map):
    count = 0
    for exId in sorted(map[token].keys()):
        count += map[token][exId][0]
    return count

def getEntityNodes(token, map):
    nodes = []
    for exId in sorted(map[token].keys()):
        nodes.extend( map[token][exId][3] )
    return nodes

def markFinal(map):
    tokenIds = sorted(map.keys())
    markedFinal = True
    while markedFinal == True:
        markedFinal = False
        for token in tokenIds:
            for exId in sorted(map[token].keys()): # should be sorted to be consistent
                example = map[token][exId][2]
                if example == None: # named entity
                    continue
                final = True
                counts = []
                if example[3].has_key("tt"):
                    if example[3]["tt"].find(",") != -1:
                        for id in example[3]["tt"].split(","):
                            final = final and isFinal(id, map)
                            counts.append( getCount(id, map) )
                    else:
                        final = final and isFinal(example[3]["tt"], map)
                        counts.append( getCount(example[3]["tt"], map) )
                if example[3].has_key("ct"):
                    final = final and isFinal(example[3]["ct"], map)
                    counts.append( getCount(example[3]["ct"], map) )
                #if counts == [0]:
                #    counts = [1]
                if map[token][exId][1] != final:
                    assert map[token][exId][1] == False
                    markedFinal = True
                    map[token][exId][1] = final
                    if len(counts) == 0:
                        combinations = 0
                    else:
                        combinations = 1
                        for c in counts:
                            combinations *= c
                    map[token][exId][0] = combinations

def buildEntityNodes(map, sentenceObject, entityCount, classSet, classIds, predictionsByExample):
    sentenceId = sentenceObject.sentence.get("id")
    entityNodes = []
    tokenIds = sorted(map.keys())
    for token in tokenIds:
        for exId in sorted(map[token].keys()):
            example = map[token][exId][2]
            if example == None: # named entity
                continue
            prediction = predictionsByExample[example[0]]
            headToken = example[3]["et"]
            for tokenElement in sentenceObject.tokens:
                if tokenElement.get("id") == headToken:
                    headToken = tokenElement
                    break
            for i in range(map[token][exId][0]):
                entityElement = ET.Element("entity")
                map[token][exId][3].append(entityElement)
                entityNodes.append(entityElement)
                entityElement.attrib["isName"] = "False"
                
                entityElement.attrib["charOffset"] = headToken.get("charOffset") 
                entityElement.attrib["headOffset"] = headToken.get("charOffset")
                entityElement.attrib["text"] = headToken.get("text")
                entityElement.attrib["id"] = sentenceId + ".e" + str(entityCount)

                entityElement.attrib["type"] = classSet.getName(prediction[0]) #example[3]["type"]
                classWeights = prediction[1:]
                predictionString = ""
                for i in range(len(classWeights)):
                    if predictionString != "":
                        predictionString += ","
                    predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
                entityElement.attrib["predictions"] = predictionString
                
                entityCount += 1
    return entityNodes

def buildInteractions(map, sentenceElement, predictionsByExample):
    sentenceId = sentenceElement.get("id")
    interactions = []
    tokenIds = sorted(map.keys())
    for token in tokenIds:
        for exId in sorted(map[token].keys()):
            example = map[token][exId][2]
            if example == None: # named entity
                continue
            prediction = predictionsByExample[example[0]]
            themeNodes = []
            theme2Nodes = None
            if example[3].has_key("tt"):
                if example[3]["tt"].find(",") != -1:
                    splits = example[3]["tt"].split(",")
                    assert len(splits) == 2
                    themeNodes = getEntityNodes(splits[0], map)
                    theme2Nodes = getEntityNodes(splits[1], map)
                else:
                    themeNodes = getEntityNodes(example[3]["tt"], map)
            else:
                themeNodes = [None]
            if example[3].has_key("ct"):
                causeNodes = getEntityNodes(example[3]["ct"], map)
            else:
                causeNodes = [None]
            
            if theme2Nodes == None:
                argCombinations = combine.combine(themeNodes, causeNodes)
                rootIndex = 0
                #assert len(argCombinations) == len(map[token][exId][3]), (len(argCombinations), len(map[token][exId][3]), example[0], argCombinations)
                for combination in argCombinations:
                    if rootIndex >= len(map[token][exId][3]):
                        print >> sys.stderr, "Warning, all event duplicates not generated (possible cycle) for example", example[0]
                        break
                    rootElement = map[token][exId][3][rootIndex]
                    # add theme edge
                    if combination[0] != None:
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = rootElement.get("id")
                        pairElement.attrib["e2"] = combination[0].get("id")
                        pairElement.attrib["id"] = sentenceId + ".i" + str(len(interactions))
                        pairElement.attrib["type"] = "Theme"
                        interactions.append(pairElement)
                        #pairCount += 1
                    
                    # add cause edge
                    if combination[1] != None:
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = rootElement.get("id")
                        pairElement.attrib["e2"] = combination[1].get("id")
                        pairElement.attrib["id"] = sentenceId + ".i" + str(len(interactions))
                        pairElement.attrib["type"] = "Cause"
                        interactions.append(pairElement)
                        #pairCount += 1
                    
                    rootIndex += 1
            else:
                argCombinations = combine.combine(themeNodes, theme2Nodes)
                rootIndex = 0
                #assert len(argCombinations) == len(map[token][exId][3]), (len(argCombinations), len(map[token][exId][3]), example[0], argCombinations)
                for combination in argCombinations:
                    if rootIndex >= len(map[token][exId][3]):
                        print >> sys.stderr, "Warning, all Binding duplicates not generated (possible cycle) for example", example[0]
                        break
                    rootElement = map[token][exId][3][rootIndex]
                    # add theme edge
                    if combination[0] != None:
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = rootElement.get("id")
                        pairElement.attrib["e2"] = combination[0].get("id")
                        pairElement.attrib["id"] = sentenceId + ".i" + str(len(interactions))
                        pairElement.attrib["type"] = "Theme"
                        interactions.append(pairElement)
                        #pairCount += 1
                    
                    # add second theme edge
                    if combination[1] != None:
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = rootElement.get("id")
                        pairElement.attrib["e2"] = combination[1].get("id")
                        pairElement.attrib["id"] = sentenceId + ".i" + str(len(interactions))
                        pairElement.attrib["type"] = "Theme"
                        interactions.append(pairElement)
                        #pairCount += 1
                    
                    rootIndex += 1
    return interactions

def unmergeExamples(examples, predictionsByExample, classSet):
    for example in examples[:]:
        prediction = predictionsByExample[example[0]]
        if classSet.getName(prediction[0]).find("---") != -1:
            nameSplits = classSet.getName(prediction[0]).split("---")
            prediction[0] = classSet.getId(nameSplits[0], False)
            count = 1
            for nameSplit in nameSplits[1:]:
                newExample = example[:]
                newExample[0] += ".dupl" + str(count)
                examples.append(newExample)
                newPrediction = prediction[:]
                newPrediction[0] = classSet.getId(nameSplit, False)
                predictionsByExample[newExample[0]] = newPrediction
                count += 1
                    
def process(sentenceObject, examplesBySentence, classSet, classIds, predictionsByExample):
    sentenceElement = sentenceObject.sentence
    sentenceId = sentenceElement.get("id")
    entityElements = sentenceElement.findall("entity")
    # remove non-name entities
    if entityElements != None:
        for entityElement in entityElements:
            if entityElement.get("isName") == "False": # interaction word
                sentenceElement.remove(entityElement)

    # add new pairs
    entityElements = sentenceElement.findall("entity")
    entityCount = IDUtils.getNextFreeId(entityElements)
    
    if examplesBySentence.has_key(sentenceId):
        # split merged examples
        for example in examplesBySentence[sentenceId][:]:
            prediction = predictionsByExample[example[0]]
            if classSet.getName(prediction[0]).find("---") != -1:
                nameSplits = classSet.getName(prediction[0]).split("---")
                prediction[0] = classSet.getId(nameSplits[0], False)
                count = 1
                for nameSplit in nameSplits[1:]:
                    newExample = example[:]
                    newExample[0] += ".dupl" + str(count)
                    examplesBySentence[sentenceId].append(newExample)
                    newPrediction = prediction[:]
                    newPrediction[0] = classSet.getId(nameSplit, False)
                    predictionsByExample[newExample[0]] = newPrediction
                    count += 1
        
        # remove negatives
        examplesToKeep = []
        for example in examplesBySentence[sentenceId]:
            prediction = predictionsByExample[example[0]]
            if prediction[0] != 1:
                examplesToKeep.append(example)
        examplesBySentence[sentenceId] = examplesToKeep
        
        map = {}
        for token in sentenceObject.tokens:
            map[token.get("id")] = {}
        addExistingEntities(map, entityElements, sentenceObject)
        addExamples(map, examplesBySentence[sentenceId])
        markFinal(map)
        entities = buildEntityNodes(map, sentenceObject, entityCount, classSet, classIds, predictionsByExample)
        interactions = buildInteractions(map, sentenceObject.sentence, predictionsByExample)
        for entity in entities:
            sentenceElement.append(entity)
        for interaction in interactions:
            sentenceElement.append(interaction)