
class SentenceElements:
    def __init__(self, sentenceElement, parse, tokenization=None):
        self.sentence = sentenceElement
        self.entities = []
        self.entitiesById = {}
        self.pairs = []
        self.interactions = []
        self.tokens = []
        self.dependencies = []
        
        pairElements = sentenceElement.findall("pair")
        if pairElements != None:
            self.pairs = pairElements
        interactionElements = sentenceElement.findall("interaction")
        if interactionElements != None:
            self.interactions = interactionElements
        
        entityElements = sentenceElement.findall("entity")
        if entityElements != None:
            self.entities = entityElements
        for entityElement in entityElements:
            self.entitiesById[entityElement.attrib["id"]] = entityElement
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        parsesElement = sentenceAnalysesElement.find("parses")
        
        parseElements = parsesElement.findall("parse")
        if len(parseElements) > 0: # new format
            parseElement = None
            for element in parseElements:
                if element.attrib["parser"] == parse:
                    parseElement = element
                    break
            tokenization = parseElement.attrib["tokenizer"]
            tokenizationsElement = sentenceAnalysesElement.find("tokenizations")
            tokenizationElements = tokenizationsElement.findall("tokenization")
            for element in tokenizationElements:
                if element.attrib["tokenizer"] == tokenization:
                    tokenizationElement = element
                    break                
        else: # old format
            parseElement = parsesElement.find(parse)
            tokenizationsElement = sentenceAnalysesElement.find("tokenizations")
            tokenizationElement = tokenizationsElement.find(tokenization)
        
        dependencyElements = parseElement.findall("dependency")
        if dependencyElements != None:
            self.dependencies = dependencyElements
        tokenElements = tokenizationElement.findall("token")
        if tokenElements != None:
            self.tokens = tokenElements

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
