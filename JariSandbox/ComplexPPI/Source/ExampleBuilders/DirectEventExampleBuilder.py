import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from Core.Gazetteer import Gazetteer
import networkx as NX
import combine

class DirectEventExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","directed","headsOnly"], length=None, types=[], featureSet=None, classSet=None, gazetteer=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        if gazetteer != None:
            print >> sys.stderr, "Loading gazetteer from", gazetteer
            self.gazetteer=Gazetteer.loadGztr(gazetteer)
        else:
            print >> sys.stderr, "No gazetteer loaded"
            self.gazetteer=None
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        self.styles = style
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        if True:#"noAnnType" in self.styles:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if "noMasking" in self.styles:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if "maxFeatures" in self.styles:
            self.multiEdgeFeatureBuilder.maximum = True
        #self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        #if "ontology" in self.styles:
        #    self.multiEdgeFeatureBuilder.ontologyFeatureBuilder = BioInferOntologyFeatureBuilder(self.featureSet)
        self.pathLengths = length
        assert(self.pathLengths == None)
        self.types = types
        
        #self.outFile = open("exampleTempFile.txt","wt")

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteer=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = DirectEventExampleBuilder(style=style, classSet=classSet, featureSet=featureSet, gazetteer=gazetteer)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
    
    def definePredictedValueRange(self, sentences, elementName):
        self.multiEdgeFeatureBuilder.definePredictedValueRange(sentences, elementName)                        
    
    def getPredictedValueRange(self):
        return self.multiEdgeFeatureBuilder.predictedRange
    
    def preProcessExamples(self, allExamples):
        if "normalize" in self.styles:
            print >> sys.stderr, " Normalizing feature vectors"
            ExampleUtils.normalizeFeatureVectors(allExamples)
        return allExamples   
    
#    def isPotentialGeniaInteraction(self, e1, e2):
#        if e1.get("isName") == "True" and e2.get("isName") == "True":
#            return False
#        elif e1.get("isName") == "True" and e2.get("isName") == "False":
#            return False
#        else:
#            return True
    
    def getArgumentEntities(self, sentenceGraph, entityNode):
        eId = entityNode.get("id")
        assert(eId != None)
        themeNodes = []
        causeNodes = []
        for edge in sentenceGraph.interactions:
            if edge.get("e1") == eId:
                edgeType = edge.get("type")
                assert(edgeType in ["Theme", "Cause"]), edgeType
                if edgeType == "Theme":
                    themeNodes.append( sentenceGraph.entitiesById[edge.get("e2")] )
                elif edgeType == "Cause":
                    causeNodes.append( sentenceGraph.entitiesById[edge.get("e2")] )
        return themeNodes, causeNodes
    
    def makeGSEvents(self, sentenceGraph):
        self.namedEntityHeadTokenIds = set()
        self.gsEvents = {} # [token]->[event-type]->[1-n argument sets]
        for token in sentenceGraph.tokens:
            self.gsEvents[token] = {}
        
        for entity in sentenceGraph.entities:
            if entity.get("type") == "neg":
                continue
            elif entity.get("isName") == "True":
                self.namedEntityHeadTokenIds.add(sentenceGraph.entityHeadTokenByEntity[entity].get("id"))
                continue
            
            eId = entity.get("id")
            eType = entity.get("type")
            arguments = set()
            for interaction in sentenceGraph.interactions:
                if interaction.get("e1") == eId:
                    e2 = sentenceGraph.entitiesById[interaction.get("e2")]
                    e2TokenId = sentenceGraph.entityHeadTokenByEntity[e2].get("id")
                    arguments.add( (interaction.get("type"), e2TokenId ) )
                    #arguments.add( (interaction.get("type"), interaction.get("e2") ) )
            eHeadToken = sentenceGraph.entityHeadTokenByEntity[entity]
            if not self.gsEvents[eHeadToken].has_key(eType):
                self.gsEvents[eHeadToken][eType] = []
            self.gsEvents[eHeadToken][eType].append(arguments)
    
    def getGSEventType(self, sentenceGraph, eHeadToken, themeTokens, causeTokens):
        #eHeadToken = sentenceGraph.entityHeadTokenByEntity[entity]
        #eType = entity.get("type")
        if len(self.gsEvents[eHeadToken]) == 0:
            return "neg"
            
        argumentSet = set()
        for themeNode in themeTokens:
            if themeNode != None:
                argumentSet.add( ("Theme", themeNode.get("id")) )
        for causeNode in causeTokens:
            if causeNode != None:
                argumentSet.add( ("Cause", causeNode.get("id")) )
        
        gsTypes = set()
        for eventType in sorted(self.gsEvents[eHeadToken].keys()):
            if argumentSet in self.gsEvents[eHeadToken][eventType]:
                gsTypes.add(eventType)
        
        if len(gsTypes) == 0:
            return "neg"
        elif len(gsTypes) == 1:
            return list(gsTypes)[0]
        else:
            gsTypes = sorted(list(gsTypes))
            string = gsTypes[0]
            for gsType in gsTypes[1:]:
                string += "---" + gsType
            return string
                        
    def buildExamples(self, sentenceGraph):
        self.makeGSEvents(sentenceGraph)
        
        examples = []
        exampleIndex = 0
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        
        eventTokens = []
        nameTokens = []
        for token in sentenceGraph.tokens:
            if token.get("id") in self.namedEntityHeadTokenIds:
                nameTokens.append(token)
            elif token.get("text").lower() in self.gazetteer:
                eventTokens.append(token)
        allTokens = eventTokens + nameTokens
        
        for token in eventTokens:
            gazCategories = self.gazetteer[token.get("text").lower()]
            #print token.get("text").lower(), gazCategories
            
            multiargument = False
            for key in gazCategories.keys():
                if key in ["Regulation","Positive_regulation","Negative_regulation"]:
                    multiargument = True
                    break
            
            if multiargument:
                combinations = combine.combine(allTokens+[None], allTokens+[None])
            else:
                combinations = []
                for t2 in allTokens:
                    combinations.append( (t2, None) )
                
            for combination in combinations:
                if combination[0] == combination[1]:
                    continue
                if combination[0] == token or combination[1] == token:
                    continue
                if combination[0] == None and combination[1] == None:
                    continue
                examples.append( self.buildExample(exampleIndex, sentenceGraph, paths, token, combination[0], combination[1]) )
                exampleIndex += 1 
        
        self.gsEvents = None
        return examples
    
    def buildExample(self, exampleIndex, sentenceGraph, paths, eventToken, themeToken, causeToken=None):
        features = {}
        self.features = features
        
        categoryName = self.getGSEventType(sentenceGraph, eventToken, [themeToken], [causeToken])
        category = self.classSet.getId(categoryName)
        
        potentialRegulation = False
        gazCategories = self.gazetteer[eventToken.get("text").lower()]
        for k,v in gazCategories.iteritems():
            self.setFeature("gaz_event_value_"+k, v)
            self.setFeature("gaz_event_"+k, 1)
            if k.find("egulation") != -1:
                potentialRegulation = True
        
        if themeToken != None:
            self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, themeToken, "theme_")
            themeEntity = None
            if sentenceGraph.entitiesByToken.has_key(themeToken):
                for themeEntity in sentenceGraph.entitiesByToken[themeToken]:
                    if themeEntity.get("isName") == "True":
                        self.setFeature("themeProtein", 1)
                        if potentialRegulation:
                            self.setFeature("regulationThemeProtein", 1)
                        break
            if not features.has_key("themeProtein"):
                self.setFeature("themeEvent", 1)
                self.setFeature("nestingEvent", 1)
                if potentialRegulation:
                    self.setFeature("regulationThemeEvent", 1)
        if causeToken != None:
            self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, causeToken, "cause_")
            causeEntity = None
            if sentenceGraph.entitiesByToken.has_key(causeToken):
                for causeEntity in sentenceGraph.entitiesByToken[causeToken]:
                    if causeEntity.get("isName") == "True":
                        self.setFeature("causeProtein", 1)
                        if potentialRegulation:
                            self.setFeature("regulationCauseProtein", 1)
                        break
            if not features.has_key("causeProtein"):
                self.setFeature("causeEvent", 1)
                self.setFeature("nestingEvent", 1)
                if potentialRegulation:
                    self.setFeature("regulationCauseEvent", 1)
        
        # Common features
#        if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
#            if entity2.get("isName") == "True":
#                features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
#            else:
#                features[self.featureSet.getId("GENIA_regulation_of_event")] = 1

        # define extra attributes
        extra = {"xtype":"event","type":categoryName}
        extra["et"] = eventToken.get("id")
        if themeToken != None:
            extra["tt"] = themeToken.get("id")
            if themeEntity != None:
                extra["t"] = themeEntity.get("id")
        if causeToken != None:
            extra["ct"] = causeToken.get("id")
            if causeEntity != None:
                extra["c"] = causeEntity.get("id")
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId       
        # make example
        #assert (category == 1 or category == -1)
        self.features = None      
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)
    
    def buildArgumentFeatures(self, sentenceGraph, paths, features, eventToken, argToken, tag):
        #eventToken = sentenceGraph.entityHeadTokenByEntity[eventNode]
        #argToken = sentenceGraph.entityHeadTokenByEntity[argNode]
        if eventToken != argToken and paths.has_key(eventToken) and paths[eventToken].has_key(argToken):
            path = paths[eventToken][argToken]
            edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
        else:
            path = [eventToken, argToken]
            edges = None
        
        self.multiEdgeFeatureBuilder.tag = tag
        self.multiEdgeFeatureBuilder.setFeatureVector(features, None, None)
        if not "disable_entity_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
        self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
        if not "disable_terminus_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
        if not "disable_single_element_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, edges, sentenceGraph)
        if not "disable_ngram_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildPathGrams(2, path, edges, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(3, path, edges, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(4, path, edges, sentenceGraph) # remove for fast
        if not "disable_path_edge_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, edges, sentenceGraph)
        self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
        self.multiEdgeFeatureBuilder.setFeatureVector(None)
        self.multiEdgeFeatureBuilder.tag = ""