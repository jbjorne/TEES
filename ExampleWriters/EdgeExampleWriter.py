import sys
from SentenceExampleWriter import SentenceExampleWriter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class EdgeExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "edge"
        self.removeEdges = True
        SentenceExampleWriter.__init__(self)
    
#    def processClassLabel(self, label, intEl):
#        splits = label.rsplit(":", 1)
#        intEl.set("type", splits[0])
#        if len(splits) > 0:
#            intType = splits[1]
#            if "(" in intType:
#                intType, roles = intType.split("(")
#                roles = roles[:-1] # remove closing parenthesis
#                e1Role, e2Role = roles.split(",")
#                intEl.set("e1Role", e1Role)
#                intEl.set("e2Role", e2Role)
#            assert intType in ("Arg", "Rel")
#            if intType == "Arg":
#                intEl.set("event", "True")

    def getEntityByIdMap(self, sentenceElement):
        entityElements = sentenceElement.findall("entity")
        entityById = {}
        for entityElement in entityElements:
            eId = entityElement.get("id")
            assert eId not in entityById, eId
            entityById[eId] = entityElement
        return entityById

    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None, exampleStyle=None, structureAnalyzer=None):        
        self.assertSameSentence(examples)
        
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
        if self.removeEdges:
            removed = self.removeChildren(sentenceElement, ["pair", "interaction"])
        
        entityById = self.getEntityByIdMap(sentenceElement)
        
        keepNeg = False
        if exampleStyle != None and "keep_neg" in exampleStyle and exampleStyle["keep_neg"]:
            keepNeg = True
        
        causeAfterTheme = False
        pairCount = 0
        for example in examples:
            if example[3].has_key("causeAfterTheme"):
                causeAfterTheme = True
            prediction = predictionsByExample[example[0]]
            predictionString = self.getPredictionStrengthString(prediction, classSet, classIds)
            #iTypes = self.getElementTypes(prediction, classSet, classIds)
            #eventTypes = example[3]["event"].split("---")
            #assert len(iTypes) == len(eventTypes), (iTypes, eventTypes)
            #for i in range(len(iTypes)): # split merged classes
            e1Id = example[3]["e1"]
            e2Id = example[3]["e2"]
            e1 = entityById[e1Id]
            e2 = entityById[e2Id]
            # directed examples are the default from edge example generation, in which case the directedness
            # of an interaction is defined by the structure analysis. Setting edge example generation as
            # undirected will override this.
            directedExample = example[3]["directed"]
            for iType in self.getElementTypes(prediction, classSet, classIds): # split merged classes
                # Keep negatives if requested
                validatedNeg = False
                if keepNeg:
                    if iType != "neg" and iType not in structureAnalyzer.getValidEdgeTypes(e1.get("type"), e2.get("type"), forceUndirected=not directedExample):
                        iType = "neg"
                        validatedNeg = True
                elif iType == "neg":
                    self.counts["removed-neg"] += 1
                    continue # skip edge element generation
                
                # Add only structurally valid edges (and negatives let through by keep_neg)
                if iType == "neg" or iType in structureAnalyzer.getValidEdgeTypes(e1.get("type"), e2.get("type"), forceUndirected=not directedExample):
                    #iType = iTypes[i]
                    pairElement = ET.Element("interaction")
                    if not directedExample:
                        pairElement.set("directed", "False")
                    elif iType == "neg" or structureAnalyzer.isDirected(iType):
                        pairElement.set("directed", "True")
                    if iType != "neg":
                        if structureAnalyzer.isEventArgument(iType): #eventTypes[i] == "True":
                            pairElement.set("event", "True")
                            siteOfTypes = structureAnalyzer.getArgSiteOfTypes(e1.get("type"), iType)
                            if len(siteOfTypes) > 0:
                                pairElement.set("siteOfTypes", ",".join(sorted(list(siteOfTypes))))
                        else:
                            entityRoles = structureAnalyzer.getRelationRoles(iType)
                            if entityRoles != None:
                                pairElement.set("e1Role", entityRoles[0])
                                pairElement.set("e2Role", entityRoles[1])
                    pairElement.set("e1", e1Id)
                    if "e1DuplicateIds" in example[3] and str(example[3]["e1DuplicateIds"]).strip() != "":
                        pairElement.set("e1DuplicateIds", example[3]["e1DuplicateIds"])
                    pairElement.set("e2", e2Id)
                    if "e2DuplicateIds" in example[3] and str(example[3]["e2DuplicateIds"]).strip() != "":
                        pairElement.set("e2DuplicateIds", example[3]["e2DuplicateIds"])
                    if validatedNeg:
                        pairElement.set("validatedNeg", "True") # a non-negative prediction made negative by structural limits
                    pairElement.set("id", sentenceId + ".i" + str(pairCount))
                    pairElement.set("type", iType)
                    #self.processClassLabel(iType, pairElement)
                    pairElement.set("conf", predictionString)
                    sentenceElement.append(pairElement)
                    pairCount += 1
                else:
                    self.counts["invalid-" + iType] += 1
        
        # Re-attach original themes, if needed
        if causeAfterTheme:
            for interaction in removed:
                if interaction.get("type") == "Theme":
                    interaction.set("id", sentenceId + ".i" + str(pairCount))
                    sentenceElement.append(interaction)
                    pairCount += 1
  
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
