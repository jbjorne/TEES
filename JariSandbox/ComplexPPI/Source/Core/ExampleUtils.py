# example is a 3-tuple (or list) of the format: (id, class, features, extra). id is a string,
# class is an int (-1 or +1) and features is a dictionary of int:float -pairs, where
# the int is the feature id and the float is the feature value

import Split

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

def writeExamples(examples, filename, commentLines=None):
    f = open(filename,"wt")
    if commentLines != None:
        for commentLine in commentLines:
            f.write("# "+commentLine+"\n")
    for example in examples:
        f.write(str(example[1]))
        keys = example[2].keys()
        keys.sort()
        for key in keys:
            f.write(" " + str(key)+":"+str(example[2][key]))
        f.write(" # " + example[0] + "\n")
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

def writeToInteractionXML(classifications, corpusElements, outputFile):
    import sys
    print >> sys.stderr, "Writing output to Interaction XML"
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import cElementTree as ET
    import cElementTreeUtils as ETUtils
    
    print >> sys.stderr, "Grouping examples"
    classificationsBySentence = {}
    for classification in classifications:
        exampleId = classification[0][0]
        sentenceId = exampleId.rsplit(".",1)[0]
        if not classificationsBySentence.has_key(sentenceId):
            classificationsBySentence[sentenceId] = []
        classificationsBySentence[sentenceId].append(classification)
    
    print >> sys.stderr, "Processing sentence elements"
    sentenceElements = corpusElements.sentences
    for sentenceObject in sentenceElements:
        sentenceElement = sentenceObject.sentence
        sentenceId = sentenceElement.attrib["id"]
        # detach analyses
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
        # add new pairs
        pairCount = 0
        if classificationsBySentence.has_key(sentenceId):
            for classification in classificationsBySentence[sentenceId]:
                example = classification[0]
                pairElement = ET.Element("pair")
                #pairElement.attrib["origId"] = origId
                pairElement.attrib["type"] = example[3]["categoryName"]
                pairElement.attrib["directed"] = "True"
                pairElement.attrib["e1"] = example[3]["e1"].attrib["id"]
                pairElement.attrib["e2"] = example[3]["e2"].attrib["id"]
                pairElement.attrib["id"] = sentenceId + ".p" + str(pairCount)
                if classification[1] == "tp" or classification[1] == "fp":
                    pairElement.attrib["interaction"] = str(True)
                else:
                    pairElement.attrib["interaction"] = str(False)
                sentenceElement.append(pairElement)
                pairCount += 1
        # re-attach the analyses-element
#        if sentenceAnalysesElement != None:
#            sentenceElement.append(sentenceAnalysesElement)
    # Write corpus
    print >> sys.stderr, "Writing corpus to", outputFile
    ETUtils.write(corpusElements.rootElement, outputFile)
    