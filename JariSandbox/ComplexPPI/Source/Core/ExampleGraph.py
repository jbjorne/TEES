import combine

def ExampleGraph():
    def __init__(self, sentenceObject, examples, predictionsByExample):
        self.sentenceObject = sentenceObject
        self.tokens = sentenceObject.tokens # token elements
        self.tokenById = {}
        for token in tokens:
            self.tokenById[token.get("id")] = token
        self.headTokenToEntity = {} # token id -> list of entity elements
        for token in self.tokens:
            self.headTokenToEntity[token.get("id")] = []
        self.entityToArgToken = {} # entity id -> token element
        self.entityFinalStatus = {} # entity id -> true/false
        
        # new element creation
        self.newEntities = []
        self.interactions = []
        self.nextEntityId = 0
        
        self.clearSentenceElement()
        
    def clearSentenceElement(self):
        sentenceElement = self.sentenceObject.sentence
        entityElements = self.sentenceElement.findall("entity")
        # remove non-name entities
        if entityElements != None:
            for entityElement in entityElements:
                if entityElement.get("isName") == "False": # interaction word
                    sentenceElement.remove(entityElement)
    
    def getHeadToken(self, entity):
        headTokenOffset = entity.get("headOffset")
        headToken = None
        for tokenElement in self.tokens:
            if tokenElement.get("charOffset") == headTokenOffset:
                headToken = tokenElement
                break
        assert headToken != None
        return headToken
    
    def addExistingEntities(self, entities, sentenceObject):
        for entity in entities:
            if entity.get("isName") == "True":
                headToken = getHeadToken(entity)
                eTokId = headToken.get("id")
                self.headTokenToEntity[eTokId].append(entity)
                self.entityFinalStatus[entity.get("id")] = True
                # The first new entity id should be last existing id + 1
                idNumber = int(entity.get("id").rsplit(".e", 1)[-1])
                if idNumber >= self.nextEntityId:
                    self.nextEntityId = idNumber + 1
            
    def addExamples(self, examples, predictionsByExample):
        self.predictionsByExample = predictionsByExample
        for example in examples:
            entityElement = self.addEntityNode(example, predictionsByExample[example])
            entityId = entityElement.get("id")
            self.entityFinalStatus[entityId] = False
            self.entityToArgToken[entityId] = []
            self.headTokenToEntity[example[3]["et"]].append(entityElement)
            for argKey in ["ct","tt"]:
                if example[3].has_key(argKey):
                    if example[3][argKey].find(",") != -1:
                        self.entityToArgToken[entityId].extend( example[3][argKey].split(",") )
                    else:
                        self.entityToArgToken[entityId].append( example[3][argKey] )               
    
    def addEntityNode(self, example, prediction):
        entityElement = ET.Element("entity")
        entityElement.attrib["isName"] = "False"
        
        headToken = tokenById[example[3]["et"]]
        entityElement.attrib["charOffset"] = headToken.get("charOffset") 
        entityElement.attrib["headOffset"] = headToken.get("charOffset")
        entityElement.attrib["text"] = headToken.get("text")
        entityElement.attrib["id"] = sentenceId + ".e" + str(self.nextEntityId)
        self.nextEntityId += 1

        entityElement.attrib["type"] = self.classSet.getName(prediction[0]) #example[3]["type"]
        classWeights = prediction[1:]
        predictionString = ""
        for i in range(len(classWeights)):
            if predictionString != "":
                predictionString += ","
            predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
        entityElement.attrib["predictions"] = predictionString
        self.newEntities.append(entityElement)
        return entityElement
    
    def addArgumentEdge(self, entity, argToken, type):
        pairElement = ET.Element("interaction")
        pairElement.attrib["directed"] = "Unknown"
        pairElement.attrib["e1"] = rootElement.get("id")
        pairElement.attrib["e2"] = combination[0].get("id")
        pairElement.attrib["id"] = sentenceId + ".i" + str(len(interactions))
        pairElement.attrib["type"] = "Theme"
        self.interactions.append(pairElement)
    
    def process(self):
        nonFinalLeft = True
        while(nonFinalLeft):
            finalized = False
            for entity in self.newEntities:
                entityId = entity.get("id")
                if not self.entityFinalStatus[entityId]:
                    finalArg = True
                    for arg in self.entityToArgToken:
                        finalArg = True
                        for entity2 in self.headTokenToEntity[arg]:
                            if entity2 == entity: # don't count the self-interaction
                                continue
                            if self.entityFinalStatus[entityId] != True:
                                finalArg = False
                                break
                        if not finalArg:
                            break
                    if finalArg:
                        self.finalizeEntity(entity)
                        finalized = True
            # Break cycles
            nonFinalLeft = False
            for i in range(len(self.newEntities)):
                entity = self.newEntities[i]
                if not self.entityFinalStatus[entity.get("id")]:
                    nonFinalLeft = True
                    break
            if nonFinalLeft and not finalized:
                self.entityFinalStatus[entity.get("id")] = True
    
    def finalizeEntity(self, entity):
        example = exampleByEntity[entity.get("id")]
        argTokens = []
        argTypes = []
        for argKey in ["ct","tt"]:
            if example[3].has_key(argKey):
                if example[3][argKey].find(",") != -1:
                    splits = example[3][argKey].split(",")
                    argTokens.extend( splits )
                    if argKey == "tt":
                        argTypes.extend( len(splits) * ["Theme"] )
                    else:
                        argTypes.extend( len(splits) * ["Cause"] )
                else:
                    argTokens.append( example[3][argKey] )                
                    if argKey == "tt":
                        argTypes.append("Theme")
                    else:
                        argTypes.append("Cause")
        argNodes = []
        for argToken in argTokens:
            for argNode in headTokenToEntity[argToken]:
                if self.entityFinalStatus[argNode.get("id")] != False: # avoid self-interaction 
                    argNodes.append(argNode)
        combinations = combine.combine(*argNodes)
        # get existing event entities
        existingEntities = []
        for entity in headTokenToEntity[example[3]["et"]]:
            if entity.get("type") == self.predictionsByExample[example[0]][0]:
                existingEntities.append(entity)
        # add arguments and make new event entities as needed
        for i in range(len(combinations)):
            if i > len(existingEntities) - 1:
                existingEntities.append( self.addEntityNode() )
            eventEntity = existingEntities[i]
            for j in len(combination):
                self.addArgumentEdge(eventEntity, combination[j], argTypes[j])
            # Mark as final
            self.entityFinalStatus[eventEntity] = True
    
    