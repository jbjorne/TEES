import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
import networkx as NX

class EventExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","directed","headsOnly"], length=None, types=[], featureSet=None, classSet=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        self.styles = style
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        if "noAnnType" in self.styles:
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
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = EventExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
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
    
    def isPotentialGeniaInteraction(self, e1, e2):
        if e1.get("isName") == "True" and e2.get("isName") == "True":
            return False
        elif e1.get("isName") == "True" and e2.get("isName") == "False":
            return False
        else:
            return True
    
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
    
    def isEvent(self, sentenceGraph, eventNode, themeNodes, causeNodes):
        goldThemeNodes, goldCauseNodes = self.getArgumentEntities(sentenceGraph, eventNode)
        for node in themeNodes:
            if node != None and node not in goldThemeNodes:
                return False
        for node in causeNodes:
            if node != None and node not in goldCauseNodes:
                return False
        return True
                        
    def buildExamples(self, sentenceGraph):
        eventNodes = []
        nameNodes = []
        for entity in sentenceGraph.entities:
            if entity.get("type") == "neg":
                continue
            if entity.get("isName") == "True":
                nameNodes.append(entity)
            else:
                eventNodes.append(entity)
        allNodes = eventNodes + nameNodes
        
        examples = []
        exampleIndex = 0
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        
        for eventNode in eventNodes:
            eventType = eventNode.get("type")
            if eventType in ["Gene_expression","Transcription","Protein_catabolism","Localization","Phosphorylation"]:
                for nameNode in nameNodes:
                    if self.isPotentialGeniaInteraction(eventNode, nameNode):
                        examples.append( self.buildExample(exampleIndex, sentenceGraph, paths, eventNode, nameNode) )
                        exampleIndex += 1
            elif eventType in ["Regulation","Positive_regulation","Negative_regulation"]:
                continue
                #combinations = combine.combine(allNodes, allNodes)
                #for combination in combinations:
                #    buildExample(eventNode, combination[0], combination[1])
            elif eventType in ["Binding"]:
                continue
            else:
                assert False, eventType
        
        return examples
    
    def buildExample(self, exampleIndex, sentenceGraph, paths, eventNode, themeNode, causeNode=None):
        features = {}
        
        if self.isEvent(sentenceGraph, eventNode, [themeNode], [causeNode]):
            category = self.classSet.getId("pos")
        else:
            category = self.classSet.getId("neg")
        
        self.buildArgumentFeatures(sentenceGraph, paths, features, eventNode, themeNode, "theme_")
        if causeNode != None:
            self.buildArgumentFeatures(sentenceGraph, paths, features, eventNode, themeNode, "cause_")
        
        # Common features
#        eventType = eventNode.get("type")
#        e2Type = entity2.get("type")
#        assert(entity1.get("isName") == "False")
#        if entity2.get("isName") == "True":
#            features[self.featureSet.getId("GENIA_target_protein")] = 1
#        else:
#            features[self.featureSet.getId("GENIA_nested_event")] = 1
#        if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
#            if entity2.get("isName") == "True":
#                features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
#            else:
#                features[self.featureSet.getId("GENIA_regulation_of_event")] = 1

        # define extra attributes
        extra = {"xtype":"event","type":eventNode.get("type")}
        extra["e"] = eventNode.get("id")
        eventToken = sentenceGraph.entityHeadTokenByEntity[eventNode]
        extra["et"] = eventToken.get("id")
        extra["t"] = themeNode.get("id")
        themeToken = sentenceGraph.entityHeadTokenByEntity[themeNode]
        extra["tt"] = themeToken.get("id")
        if causeNode != None:
            extra["c"] = causeNode.get("id")
            extra["c"] = causeToken.get("id")
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId       
        # make example
        #assert (category == 1 or category == -1)        
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)
    
    def buildArgumentFeatures(self, sentenceGraph, paths, features, eventNode, argNode, tag):
        eventToken = sentenceGraph.entityHeadTokenByEntity[eventNode]
        argToken = sentenceGraph.entityHeadTokenByEntity[argNode]
        if eventToken != argToken and paths.has_key(eventToken) and paths[eventToken].has_key(argToken):
            path = paths[eventToken][argToken]
            edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
        else:
            path = [eventToken, argToken]
            edges = None
        
        self.multiEdgeFeatureBuilder.tag = tag
        self.multiEdgeFeatureBuilder.setFeatureVector(features, eventNode, argNode)
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