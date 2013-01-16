import sys

def getCorpusIterator(input, output, parse=None, tokenization=None):
    import cElementTreeUtils as ETUtils
    from InteractionXML.SentenceElements import SentenceElements
    #import xml.etree.cElementTree as ElementTree
    
    etWriter = ETUtils.ETWriter(output)
    for eTuple in ETUtils.ETIteratorFromObj(input, ("start", "end")):
        element = eTuple[1]
        if eTuple[0] == "end" and element.tag == "document":
            sentences = []
            for sentenceElement in element.findall("sentence"):
                #print ElementTree.tostring(sentenceElement)
                sentence = SentenceElements(sentenceElement, parse, tokenization, removeIntersentenceInteractions=False)
                sentences.append(sentence)
            yield sentences
            etWriter.write(element)
        elif element.tag == "corpus":
            if eTuple[0] == "start":
                etWriter.begin(element)
            else:
                etWriter.end(element)
        if eTuple[0] == "end" and element.tag in ["document", "corpus"]:
            element.clear()
    etWriter.close()

class SentenceElements:
    def __init__(self, sentenceElement, parse=None, tokenization=None, removeIntersentenceInteractions=True, removeNameInfo=False, verbose=False):
        self.sentence = sentenceElement
        self.entities = []
        self.entitiesById = {}
        self.pairs = []
        self.interactions = []
        self.tokens = []
        self.dependencies = []
        
        self.parseElement = None
        self.tokenizationElement = None
        
        # Read entities
        entityElements = sentenceElement.findall("entity")
        if entityElements != None:
            entitiesToKeep = []
            for entityElement in entityElements:
                if entityElement.get("type") != "neg":
                    entitiesToKeep.append(entityElement)
            entityElements = entitiesToKeep
            self.entities = entityElements
            for entityElement in entityElements:
                if removeNameInfo:
                    entityElement.set("given","False")
                entityId = entityElement.get("id")
                if entityId == None:
                    raise Exception("entity element has no id")
                self.entitiesById[entityId] = entityElement
        
        # Read pairs and interactions
#        sentenceId = sentenceElement.get("id")
#        pairElements = sentenceElement.findall("pair")
#        if pairElements != None:
#            self.pairs = pairElements
#        if removeIntersentenceInteractions:
#            pairsToKeep = []
#            for pair in pairElements:
#                if pair.get("e1").rsplit(".",1)[0] == sentenceId and pair.get("e2").rsplit(".",1)[0] == sentenceId:
#                    pairsToKeep.append(pair)
#            self.pairs = pairsToKeep       
#        interactionElements = sentenceElement.findall("interaction")
#        if interactionElements != None:
#            self.interactions = interactionElements
#            self.interSentenceInteractions = []
#        if removeIntersentenceInteractions:
#            interactionsToKeep = []
#            for interaction in interactionElements:
#                e1rsplits = interaction.get("e1").count(".") - 2
#                e2rsplits = interaction.get("e2").count(".") - 2
#                if interaction.get("e1").rsplit(".",e1rsplits)[0] == sentenceId and interaction.get("e2").rsplit(".",e2rsplits)[0] == sentenceId:
#                    interactionsToKeep.append(interaction)
#                else:
#                    self.interSentenceInteractions.append(interaction)
#            self.interactions = interactionsToKeep
        
        self.pairs = sentenceElement.findall("pair")
        self.interactions = sentenceElement.findall("interaction")
        self.interSentenceInteractions = []
        if removeIntersentenceInteractions:
            for targetList in (self.interactions, self.pairs):
                for interaction in targetList[:]:
                    if interaction.get("e1") not in self.entitiesById or interaction.get("e2") not in self.entitiesById:
                        targetList.remove(interaction)
                        self.interSentenceInteractions.append(interaction)
        
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        analysesElement = sentenceElement.find("analyses")
        assert sentenceAnalysesElement == None or analysesElement == None, sentenceElement.get("id")
        if sentenceAnalysesElement == None:
            sentenceAnalysesElement = analysesElement
        if sentenceAnalysesElement != None:
            parsesElement = None
            if parse != None:
            #    parsesElement = sentenceAnalysesElement.find("parses")
            #if parsesElement != None:
                parseElements = [x for x in sentenceAnalysesElement.getiterator("parse")]
                #parseElements = parsesElement.findall("parse")
                if len(parseElements) > 0: # new format
                    self.parseElement = None
                    for element in parseElements:
                        if element.get("parser") == parse:
                            self.parseElement = element
                            break
                    if self.parseElement != None:
                        tokenization = self.parseElement.get("tokenizer")
                        tokenizationElements = [x for x in sentenceAnalysesElement.getiterator("tokenization")]
                        #tokenizationsElement = sentenceAnalysesElement.find("tokenizations")
                        #tokenizationElements = tokenizationsElement.findall("tokenization")
                        for element in tokenizationElements:
                            if element.get("tokenizer") == tokenization:
                                self.tokenizationElement = element
                                break             
                else: # old format
                    if parse != None:
                        self.parseElement = parsesElement.find(parse)
                    if tokenization != None:
                        tokenizationsElement = sentenceAnalysesElement.find("tokenizations")
                        if tokenizationsElement != None:
                            self.tokenizationElement = tokenizationsElement.find(tokenization)
                
                dependencyElements = None
                if self.parseElement != None:
                    dependencyElements = self.parseElement.findall("dependency")
                    if dependencyElements != None:
                        self.dependencies = dependencyElements
                else:
                    if verbose:
                        print >> sys.stderr, "Warning, parse", parse, "not found"
                if self.tokenizationElement != None:
                    tokenElements = self.tokenizationElement.findall("token")
                    if tokenElements != None:
                        self.tokens = tokenElements
                else:
                    if verbose:
                        print >> sys.stderr, "Warning, tokenization", tokenization, "not found"

    def getEntity(self, offset, offsetList, entityIds):
        index = 0
        for i in offsetList:
            if (offset[0] >= i[0] and offset[0] <= i[1]) or (i[0] >= offset[0] and i[0] <= offset[1]):
                #print offset, "list:", i
                return entityIds[index]
            index += 1
        return None
    
    def getEntityTokens(self):
        entityElements = self.entities
        entityOffsets = []
        entityOffsetIds = []
        entityTokens = {}
        for entityElement in entityElements:
            if not entityTokens.has_key(entityElement.get("id")):
                entityTokens[entityElement.get("id")] = []
            offsets = entityElement.get("charOffset").split(",")
            for i in offsets:
                offset = i.split("-")
                offset[0] = int(offset[0])
                offset[1] = int(offset[1])
                entityOffsets.append(offset)
                entityOffsetIds.append(entityElement.get("id"))
        
        for tokenElement in self.tokens:
            offset = tokenElement.get("charOffset").split("-")
            offset[0] = int(offset[0])
            offset[1] = int(offset[1])
            id = tokenElement.get("id")
            entityId = self.getEntity(offset, entityOffsets, entityOffsetIds)
            if not entityTokens.has_key(entityId):
                entityTokens[entityId] = []
            entityTokens[entityId].append(id)
    
        return entityTokens
