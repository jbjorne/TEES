import sys
from SentenceExampleWriter import SentenceExampleWriter
import Utils.InteractionXML.IDUtils as IDUtils
import Utils.InteractionXML.ExtendTriggers
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class EntityExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "token"
        self.insertWeights = False
        SentenceExampleWriter.__init__(self)
    
    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None, exampleStyle=None, structureAnalyzer=None):        
        self.assertSameSentence(examples)
        
        extensionRequested = False
        
        sentenceElement = sentenceObject.sentence
        sentenceId = sentenceElement.get("id")
        # detach analyses-element
        sentenceAnalysesElement = None
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        if sentenceAnalysesElement == None:
            sentenceAnalysesElement = sentenceElement.find("analyses")
        if sentenceAnalysesElement != None:
            sentenceElement.remove(sentenceAnalysesElement)
        # remove pairs and interactions
        interactions = self.removeChildren(sentenceElement, ["pair", "interaction"])
        # remove entities
        newEntityIdCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        nonNameEntities = self.removeNonNameEntities(sentenceElement)
        # remove named entities if needed
        if exampleStyle != None and "names" in exampleStyle and exampleStyle["names"]: # remove all entities, including names
            self.removeChildren(sentenceElement, ["entity"])
        
        # gold sentence elements
        goldEntityTypeByHeadOffset = {}
        goldEntityByHeadOffset = {}
        if goldSentence != None:
            for entity in goldSentence.entities:
                headOffset = entity.get("headOffset")
                if not goldEntityTypeByHeadOffset.has_key(headOffset):
                    goldEntityTypeByHeadOffset[headOffset] = []
                    goldEntityByHeadOffset[headOffset] = []
                goldEntityTypeByHeadOffset[headOffset].append(entity)
                goldEntityByHeadOffset[headOffset].append(entity)
            for key in goldEntityTypeByHeadOffset:
                goldEntityTypeByHeadOffset[key] =  self.getMergedEntityType(goldEntityTypeByHeadOffset[key])
            for token in sentenceObject.tokens:
                if not goldEntityTypeByHeadOffset.has_key(token.get("charOffset")):
                    goldEntityTypeByHeadOffset[token.get("charOffset")] = "neg"
            
        # add new pairs
        for example in examples:
            # Entity examplesalways refer to a single head token
            headTokenId = example[3]["t"]
            headToken = None
            for token in sentenceObject.tokens:
                if token.get("id") == headTokenId:
                    headToken = token
                    break
            assert headToken != None, example[3]
            # Determine if additional processing is requested
            unmergeEPINeg = None
            if "unmergeneg" in example[3] and example[3]["unmergeneg"] == "epi":
                unmergeEPINeg = headToken.get("text")
            if "trigex" in example[3] and example[3]["trigex"] == "bb":
                extensionRequested = True
            # Make entities for positive predictions
            prediction = predictionsByExample[example[0]]
            predictionString = self.getPredictionStrengthString(prediction, classSet, classIds)
            for eType in self.getElementTypes(prediction, classSet, classIds, unmergeEPINegText=unmergeEPINeg): # split merged classes
                entityElement = ET.Element("entity")
                #entityElement.set("given", "False")
                entityElement.set("charOffset", headToken.get("charOffset"))
                entityElement.set("headOffset", headToken.get("charOffset"))
                entityElement.set("text", headToken.get("text"))
                entityElement.set("id", sentenceId + ".e" + str(newEntityIdCount))
                entityElement.set("type", eType)
                entityElement.set("conf", predictionString)
                if structureAnalyzer.isEvent(eType):
                    entityElement.set("event", "True")
                #self.setElementType(entityElement, prediction, classSet, classIds, unmergeEPINeg=unmergeEPINeg)
                if self.insertWeights: # in other words, use gold types
                    headOffset = headToken.get("charOffset")
                    if goldEntityByHeadOffset.has_key(headOffset):
                        for entity in goldEntityByHeadOffset[headOffset]:
                            entity.set("conf", entityElement.get("conf") )
                if goldEntityTypeByHeadOffset.has_key(headToken.get("charOffset")):
                    entityElement.set("goldType", goldEntityTypeByHeadOffset[headToken.get("charOffset")])
                if "goldIds" in example[3]: # The entities for which this example was built
                    entityElement.set("goldIds", example[3]["goldIds"])
                if (entityElement.get("type") != "neg" and not goldEntityByHeadOffset.has_key(entityElement.get("headOffset"))) or not self.insertWeights:
                    newEntityIdCount += 1
                    sentenceElement.append(entityElement)
                elif entityElement.get("type") == "neg":
                    pass
                    #newEntityIdCount += 1
                    #sentenceElement.append(entityElement)
        
        # if only adding weights, re-attach interactions and gold entities
        if self.insertWeights:
            for entity in nonNameEntities:
                sentenceElement.append(entity)
            for interaction in interactions:
                sentenceElement.append(interaction)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
        
        # Extend bacteria triggers
        if extensionRequested:
            Utils.InteractionXML.ExtendTriggers.extend(sentenceElement, entityTypes=["Bacterium"])
    
    def getMergedEntityType(self, entities):
        """
        If a single token belongs to multiple entities of different types,
        a new, composite type is defined. This type is the alphabetically
        ordered types of these entities joined with '---'.
        """
        types = set()
        for entity in entities:
            types.add(entity.get("type"))
        types = list(types)
        types.sort()
        typeString = ""
        for type in types:
            if type == "Protein":
                continue
            if typeString != "":
                typeString += "---"
            typeString += type
        
        if typeString == "":
            return "neg"
        
        return typeString
