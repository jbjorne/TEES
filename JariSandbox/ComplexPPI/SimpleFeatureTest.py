import sys
import cElementTree as ET
from InteractionXML.CorpusElements import CorpusElements
from SentenceGraph import *
import GraphToSVG

featureIds = {}

def defFeature(featureName):
    global featureIds
    if not featureIds.has_key(featureName):
        featureIds[featureName] = len(featureIds)
    return featureIds[featureName]

def writeExamples(file, examples, featuresByExample):
    for example in examples:
        if example[1]:
            file.write("+1")
        else:
            file.write("-1")
        features = featuresByExample[example[0]]
        keys = features.keys()
        keys.sort()
        for key in keys:
            file.write(" "+str(key)+":"+str(features[key]))
        file.write(" # "+example[0]+"\n")

def getEntityText(entity):
#    print entity.attrib
#    if entity.attrib["isName"] == "True":
#        return "NAMED_ENT"
#    else:
#        return entity.attrib["text"]
    return entity.attrib["text"]

def buildFeatures(examples, graph):
    global featureIds
    featuresByExample = {}
    for example in examples:
        features = {}
        features[defFeature("terminus_text_"+getEntityText(example[2]))] = 1
        features[defFeature("terminus_POS_"+example[2].attrib["POS"])] = 1
        features[defFeature("terminus_text_"+getEntityText(example[3]))] = 1
        features[defFeature("terminus_POS_"+example[3].attrib["POS"])] = 1
        featuresByExample[example[0]] = features
    return featuresByExample

def defineExamples(sentence, graph):
    examples = []
    exampleIndex = 0
    for i in range(len(graph.tokens)-1):
        for j in range(i+1,len(graph.tokens)):
            t1 = graph.tokens[i]
            t2 = graph.tokens[j]
            hasDep = graph.dependencyGraph.has_edge(t1, t2) or graph.dependencyGraph.has_edge(t2, t1)
            hasInt = graph.interactionGraph.has_edge(t1, t2) or graph.interactionGraph.has_edge(t2, t1)
            if hasDep or hasInt:
                if hasDep and hasInt:
                    category = True
                elif hasDep and not hasInt:
                    category = False
                examples.append( (sentence.sentence.attrib["id"]+".x"+str(exampleIndex),category,t1,t2) )
                exampleIndex += 1
    return examples

if __name__=="__main__":
    defaultInteractionFilename = "Data/BioInferForComplexPPI.xml"
    
    print >> sys.stderr, "Loading corpus file", defaultInteractionFilename
    corpusTree = ET.parse(defaultInteractionFilename)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    keys = corpusElements.sentencesById.keys()
    keys.sort()
    outfile = open("Data/FeatureTest.txt","wt")
    for key in keys:
        print >> sys.stderr, "Processing sentence", key
        sentence = corpusElements.sentencesById[key]
        print >> sys.stderr, "Building graph"
        graph = SentenceGraph(sentence.tokens, sentence.dependencies)
        print >> sys.stderr, "Mapping interactions"
        graph.mapInteractions(sentence.entities, sentence.interactions)
        examples = defineExamples(sentence, graph)
        featuresByExample = buildFeatures(examples, graph)
        writeExamples(outfile,examples,featuresByExample)
    outfile.close()
