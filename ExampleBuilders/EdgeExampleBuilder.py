"""
Edge Examples
"""

import sys, os
from ExampleBuilders.FeatureBuilders.OntoBiotopeFeatureBuilder import OntoBiotopeFeatureBuilder
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilders.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder
from FeatureBuilders.BioInferOntologyFeatureBuilder import BioInferOntologyFeatureBuilder
from FeatureBuilders.NodalidaFeatureBuilder import NodalidaFeatureBuilder
from FeatureBuilders.BacteriaRenamingFeatureBuilder import BacteriaRenamingFeatureBuilder
from FeatureBuilders.RELFeatureBuilder import RELFeatureBuilder
from FeatureBuilders.DrugFeatureBuilder import DrugFeatureBuilder
from FeatureBuilders.EVEXFeatureBuilder import EVEXFeatureBuilder
from FeatureBuilders.GiulianoFeatureBuilder import GiulianoFeatureBuilder
from FeatureBuilders.OntoBiotopeFeatureBuilder import OntoBiotopeFeatureBuilder
from FeatureBuilders.WordNetFeatureBuilder import WordNetFeatureBuilder
from FeatureBuilders.WordVectorFeatureBuilder import WordVectorFeatureBuilder
#import Graph.networkx_v10rc1 as NX10
from Core.SimpleGraph import Graph
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
import Utils.Range as Range
from multiprocessing import Process
import itertools

# For gold mapping
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML

class EdgeExampleBuilder(ExampleBuilder):
    """
    This example builder makes edge examples, i.e. examples describing
    the event arguments.
    """
    def __init__(self, style=None, types=[], featureSet=None, classSet=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        assert( classSet.getId("neg") == 1 or (len(classSet.Ids)== 2 and classSet.getId("neg") == -1) )
        
        # Basic style = trigger_features:typed:directed:no_linear:entities:auto_limits:noMasking:maxFeatures
        self._setDefaultParameters([
            "directed", "undirected", "headsOnly", "graph_kernel", "noAnnType", "mask_nodes", "limit_features",
            "no_auto_limits", "co_features", "genia_features", "bi_features", #"genia_limits", "epi_limits", "id_limits", "rel_limits", "bb_limits", "bi_limits", "co_limits",
            "genia_task1", "ontology", "nodalida", "bacteria_renaming", "no_trigger_features", "rel_features",
            "drugbank_features", "ddi_mtmx", "evex", "giuliano", "random", "themeOnly", "causeOnly", "no_path", "token_nodes", 
            "skip_extra_triggers", "headsOnly", "graph_kernel", "no_task", "no_dependency", 
            "disable_entity_features", "disable_terminus_features", "disable_single_element_features", 
            "disable_ngram_features", "disable_path_edge_features", "linear_features", "subset", "binary", "pos_only",
            "entity_type", "filter_shortest_path", "maskTypeAsProtein", "keep_neg", "metamap", 
            "sdb_merge", "sdb_features", "ontobiotope_features", "no_self_loops", "full_entities",
            "no_features", "wordnet", "wordvector", "se10t8_undirected", "filter_types", "doc_extra",
            "entity_extra"])
        self.styles = self.getParameters(style)
        #if style == None: # no parameters given
        #    style["typed"] = style["directed"] = style["headsOnly"] = True
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet, self.styles)
        # NOTE Temporarily re-enabling predicted range
        #self.multiEdgeFeatureBuilder.definePredictedValueRange([], None)
        if self.styles["graph_kernel"]:
            from FeatureBuilders.GraphKernelFeatureBuilder import GraphKernelFeatureBuilder
            self.graphKernelFeatureBuilder = GraphKernelFeatureBuilder(self.featureSet)
        if self.styles["noAnnType"]:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if self.styles["mask_nodes"]:
            self.multiEdgeFeatureBuilder.maskNamedEntities = True
        else:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if not self.styles["limit_features"]:
            self.multiEdgeFeatureBuilder.maximum = True
        if self.styles["genia_task1"]:
            self.multiEdgeFeatureBuilder.filterAnnTypes.add("Entity")
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        if self.styles["ontology"]:
            self.multiEdgeFeatureBuilder.ontologyFeatureBuilder = BioInferOntologyFeatureBuilder(self.featureSet)
        if self.styles["ontobiotope_features"]:
            self.ontobiotopeFeatureBuilder = OntoBiotopeFeatureBuilder(self.featureSet)
        if self.styles["nodalida"]:
            self.nodalidaFeatureBuilder = NodalidaFeatureBuilder(self.featureSet)
        if self.styles["bacteria_renaming"]:
            self.bacteriaRenamingFeatureBuilder = BacteriaRenamingFeatureBuilder(self.featureSet)
        if not self.styles["no_trigger_features"]:
            self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet, self.styles)
            self.triggerFeatureBuilder.useNonNameEntities = True
            if self.styles["noAnnType"]:
                self.triggerFeatureBuilder.noAnnType = True
            if self.styles["genia_task1"]:
                self.triggerFeatureBuilder.filterAnnTypes.add("Entity")
            #self.bioinferOntologies = OntologyUtils.loadOntologies(OntologyUtils.g_bioInferFileName)
        if self.styles["rel_features"]:
            self.relFeatureBuilder = RELFeatureBuilder(featureSet)
        if self.styles["drugbank_features"]:
            self.drugFeatureBuilder = DrugFeatureBuilder(featureSet)
        if self.styles["evex"]:
            self.evexFeatureBuilder = EVEXFeatureBuilder(featureSet)
        if self.styles["wordnet"]:
            self.wordNetFeatureBuilder = WordNetFeatureBuilder(featureSet)
        if self.styles["wordvector"]:
            self.wordVectorFeatureBuilder = WordVectorFeatureBuilder(featureSet, self.styles)
        if self.styles["giuliano"]:
            self.giulianoFeatureBuilder = GiulianoFeatureBuilder(featureSet)
        self.types = types
        if self.styles["random"]:
            from FeatureBuilders.RandomFeatureBuilder import RandomFeatureBuilder
            self.randomFeatureBuilder = RandomFeatureBuilder(self.featureSet)
    
    def definePredictedValueRange(self, sentences, elementName):
        self.multiEdgeFeatureBuilder.definePredictedValueRange(sentences, elementName)                        
    
    def getPredictedValueRange(self):
        return self.multiEdgeFeatureBuilder.predictedRange
    
    def filterEdgesByType(self, edges, typesToInclude):
        if len(typesToInclude) == 0:
            return edges
        edgesToKeep = []
        for edge in edges:
            if edge.get("type") in typesToInclude:
                edgesToKeep.append(edge)
        return edgesToKeep
    
    def getCategoryNameFromTokens(self, sentenceGraph, t1, t2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        types = set()
        intEdges = sentenceGraph.interactionGraph.getEdges(t1, t2)
        if not directed:
            intEdges = intEdges + sentenceGraph.interactionGraph.getEdges(t2, t1)
        for intEdge in intEdges:
            types.add(intEdge[2].get("type"))
        types = list(types)
        types.sort()
        categoryName = ""
        for name in types:
            if categoryName != "":
                categoryName += "---"
            categoryName += name
        if categoryName != "":
            return categoryName
        else:
            return "neg"
        
    def getCategoryName(self, sentenceGraph, e1, e2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        interactions = sentenceGraph.getInteractions(e1, e2, True)
        if not directed and not self.styles["se10t8_undirected"]:
            interactions = interactions + sentenceGraph.getInteractions(e2, e1, True)
        
        types = set()
        for interaction in interactions:
            types.add(interaction[2].get("type"))
        types = list(types)
        types.sort()
        categoryName = ""
        for name in types:
            if self.styles["causeOnly"] and name != "Cause":
                continue
            if self.styles["themeOnly"] and name != "Theme":
                continue
            if categoryName != "":
                categoryName += "---"
            if self.styles["sdb_merge"]:
                name = self.mergeForSeeDev(name, self.structureAnalyzer)
            categoryName += name
        if categoryName != "":
            return categoryName
        else:
            return "neg"

    def getBISuperType(self, eType):
        if eType in ["GeneProduct", "Protein", "ProteinFamily", "PolymeraseComplex"]:
            return "ProteinEntity"
        elif eType in ["Gene", "GeneFamily", "GeneComplex", "Regulon", "Site", "Promoter"]:
            return "GeneEntity"
        else:
            return None
    
    def getSeeDevSuperTypes(self, eType):
        if eType in ("Gene", "Gene_Family", "Box", "Promoter"):
            return ("DNA", "Molecule")
        elif eType == "RNA":
            return ("RNA", "DNA_Product", "Molecule")
        elif eType in ("Protein", "Protein_Family", "Protein_Complex", "Protein_Domain"):
            return ("Amino_acid_sequence", "DNA_Product", "Molecule")
        elif eType == "Hormone":
            return ("Molecule",)
        elif eType in ("Regulatory_Network", "Pathway"):
            return ("Dynamic_process",)
        elif eType in ("Genotype", "Tissue", "Development_Phase"):
            return ("Biological_context", "Context")
        elif eType == "Environmental_Factor":
            return ("Context",)
        else:
            raise Exception("Unknown SeeDev type '" + str(eType) + "'")
    
    def mergeForSeeDev(self, categoryName, structureAnalyzer):
        if categoryName in structureAnalyzer.typeMap["forward"]:
            return structureAnalyzer.typeMap["forward"][categoryName]
        return categoryName
#         for tag in ("Regulates", "Exists", "Interacts", "Is", "Occurs"):
#             if categoryName.startswith(tag):
#                 categoryName = tag
#                 break
#         return categoryName
    
    def processCorpus(self, input, output, gold=None, append=False, allowNewIds=True, structureAnalyzer=None):
        if self.styles["sdb_merge"]:
            structureAnalyzer.determineNonOverlappingTypes()
            self.structureAnalyzer = structureAnalyzer
        ExampleBuilder.processCorpus(self, input, output, gold, append, allowNewIds, structureAnalyzer)
    
    def isValidInteraction(self, e1, e2, structureAnalyzer,forceUndirected=False):
        return len(structureAnalyzer.getValidEdgeTypes(e1.get("type"), e2.get("type"), forceUndirected=forceUndirected)) > 0

    def getGoldCategoryName(self, goldGraph, entityToGold, e1, e2, directed=True):
        if len(entityToGold[e1]) > 0 and len(entityToGold[e2]) > 0:
            return self.getCategoryName(goldGraph, entityToGold[e1][0], entityToGold[e2][0], directed=directed)
        else:
            return "neg"
    
    def filterEdge(self, edge, edgeTypes):
        import types
        assert edgeTypes != None
        if type(edgeTypes) not in [types.ListType, types.TupleType]:
            edgeTypes = [edgeTypes]
        if edge[2].get("type") in edgeTypes:
            return True
        else:
            return False
    
    def keepExample(self, e1, e2, categoryName, isDirected, structureAnalyzer):
        makeExample = True
        if (not self.styles["no_auto_limits"]) and not self.isValidInteraction(e1, e2, structureAnalyzer, forceUndirected=not isDirected):
            makeExample = False
            self.exampleStats.filter("auto_limits")
        if self.styles["genia_task1"] and (e1.get("type") == "Entity" or e2.get("type") == "Entity"):
            makeExample = False
            self.exampleStats.filter("genia_task1")
        if self.styles["pos_only"] and categoryName == "neg":
            makeExample = False
            self.exampleStats.filter("pos_only")
        if self.styles["no_self_loops"] and ((e1 == e2) or (e1.get("headOffset") == e2.get("headOffset"))):
            makeExample = False
            self.exampleStats.filter("no_self_loops")
        return makeExample
    
    def getExampleCategoryName(self, e1=None, e2=None, t1=None, t2=None, sentenceGraph=None, goldGraph=None, entityToGold=None, isDirected=True, structureAnalyzer=None):
        if self.styles["token_nodes"]:
            categoryName = self.getCategoryNameFromTokens(sentenceGraph, t1, t2, isDirected)
        else:
            categoryName = self.getCategoryName(sentenceGraph, e1, e2, isDirected)
            if goldGraph != None:
                categoryName = self.getGoldCategoryName(goldGraph, entityToGold, e1, e2, isDirected)
        if self.styles["filter_types"] != None and categoryName in self.styles["filter_types"]:
            categoryName = "neg"
        if self.styles["se10t8_undirected"]:
            assert e1.get("id").endswith(".e1")
            assert e2.get("id").endswith(".e2")
        #if self.styles["sdb_merge"]:
        #    categoryName = self.mergeForSeeDev(categoryName, structureAnalyzer)
        return categoryName
                
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        #examples = []
        exampleIndex = 0
        # example directionality
        if self.styles["directed"] == None and self.styles["undirected"] == None: # determine directedness from corpus
            examplesAreDirected = structureAnalyzer.hasDirectedTargets() if structureAnalyzer != None else True
        elif self.styles["directed"]:
            assert self.styles["undirected"] in [None, False]
            examplesAreDirected = True
        elif self.styles["undirected"]:
            assert self.styles["directed"] in [None, False]
            examplesAreDirected = False
        
        if not self.styles["no_trigger_features"]: 
            self.triggerFeatureBuilder.initSentence(sentenceGraph)
        if self.styles["evex"]: 
            self.evexFeatureBuilder.initSentence(sentenceGraph)
#         if self.styles["sdb_merge"]:
#             self.determineNonOverlappingTypes(structureAnalyzer)
            
        # Filter entities, if needed
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        entityToDuplicates = sentenceGraph.mergedEntityToDuplicates
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # Connect to optional gold graph
        entityToGold = None
        if goldGraph != None:
            entityToGold = EvaluateInteractionXML.mapEntities(entities, goldGraph.entities)
        
        paths = None
        if not self.styles["no_path"]:
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            paths = undirected
            if self.styles["filter_shortest_path"] != None: # For DDI use filter_shortest_path=conj_and
                paths.resetAnalyses() # just in case
                paths.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        # Generate examples based on interactions between entities or interactions between tokens
        if self.styles["token_nodes"]:
            loopRange = len(sentenceGraph.tokens)
        else:
            loopRange = len(entities)
        for i in range(loopRange-1):
            for j in range(i+1,loopRange):
                eI = None
                eJ = None
                if self.styles["token_nodes"]:
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                else:
                    eI = entities[i]
                    eJ = entities[j]
                    tI = sentenceGraph.entityHeadTokenByEntity[eI]
                    tJ = sentenceGraph.entityHeadTokenByEntity[eJ]
                    if eI.get("type") == "neg" or eJ.get("type") == "neg":
                        continue
                    if self.styles["skip_extra_triggers"]:
                        if eI.get("source") != None or eJ.get("source") != None:
                            continue
                # only consider paths between entities (NOTE! entities, not only named entities)
                if self.styles["headsOnly"]:
                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                        continue
                
                examples = self.buildExamplesForPair(tI, tJ, paths, sentenceGraph, goldGraph, entityToGold, eI, eJ, structureAnalyzer, examplesAreDirected)
                for categoryName, features, extra in examples:
                    # make example
                    if self.styles["binary"]:
                        if categoryName != "neg":
                            category = 1
                        else:
                            category = -1
                        extra["categoryName"] = "i"
                    else:
                        category = self.classSet.getId(categoryName)
                    example = [sentenceGraph.getSentenceId()+".x"+str(exampleIndex), category, features, extra]
                    ExampleUtils.appendExamples([example], outfile)
                    exampleIndex += 1

        return exampleIndex
    
    def buildExamplesForPair(self, token1, token2, paths, sentenceGraph, goldGraph, entityToGold, entity1=None, entity2=None, structureAnalyzer=None, isDirected=True):
        # define forward
        categoryName = self.getExampleCategoryName(entity1, entity2, token1, token2, sentenceGraph, goldGraph, entityToGold, isDirected, structureAnalyzer=structureAnalyzer)
        # make forward
        forwardExample = None
        self.exampleStats.beginExample(categoryName)
        if self.keepExample(entity1, entity2, categoryName, isDirected, structureAnalyzer):
            forwardExample = self.buildExample(token1, token2, paths, sentenceGraph, categoryName, entity1, entity2, structureAnalyzer, isDirected)
        
        if isDirected: # build a separate reverse example (if that is valid)
            self.exampleStats.endExample() # end forward example
            # define reverse
            categoryName = self.getExampleCategoryName(entity2, entity1, token2, token1, sentenceGraph, goldGraph, entityToGold, True, structureAnalyzer=structureAnalyzer)
            # make reverse
            self.exampleStats.beginExample(categoryName)
            reverseExample = None
            if self.keepExample(entity2, entity1, categoryName, True, structureAnalyzer):
                reverseExample = self.buildExample(token2, token1, paths, sentenceGraph, categoryName, entity2, entity1, structureAnalyzer, isDirected)
            self.exampleStats.endExample()
            return filter(None, [forwardExample, reverseExample])
        elif self.styles["se10t8_undirected"]: # undirected example with a directed type
            self.exampleStats.endExample()
            return [forwardExample]
        elif forwardExample != None: # merge features from the reverse example to the forward one
            reverseExample = self.buildExample(token2, token1, paths, sentenceGraph, categoryName, entity2, entity1, structureAnalyzer, isDirected)
            forwardExample[1].update(reverseExample[1])
            self.exampleStats.endExample() # end merged example
            return [forwardExample]
        else: # undirected example that was filtered
            self.exampleStats.endExample() # end merged example
            return []
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, entity1=None, entity2=None, structureAnalyzer=None, isDirected=True):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        # define features
        if not self.styles["no_path"]:
            path = paths.getPaths(token1, token2)
            if len(path) > 0:
                path = path[0]
                #pathExists = True
            else:
                path = [token1, token2]
                #pathExists = False
        else:
            path = [token1, token2]
            #pathExists = False
        
        features = {}
        if not self.styles["no_features"]:
            features = self.buildFeatures(sentenceGraph, entity1, entity2, token1, token2, path)
        
        # define extra attributes
        if int(path[0].get("charOffset").split("-")[0]) < int(path[-1].get("charOffset").split("-")[0]):
            extra = {"xtype":"edge","type":"i","t1":path[0].get("id"),"t2":path[-1].get("id")}
            extra["deprev"] = False
        else:
            extra = {"xtype":"edge","type":"i","t1":path[-1].get("id"),"t2":path[0].get("id")}
            extra["deprev"] = True
        if entity1 != None:
            extra["e1"] = entity1.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e1DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity1]])
        if entity2 != None:
            extra["e2"] = entity2.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e2DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity2]])
        extra["categoryName"] = categoryName
        if self.styles["bacteria_renaming"]:
            if entity1.get("text") != None and entity1.get("text") != "":
                extra["e1t"] = entity1.get("text").replace(" ", "---").replace(":","-COL-")
            if entity2.get("text") != None and entity2.get("text") != "":
                extra["e2t"] = entity2.get("text").replace(" ", "---").replace(":","-COL-")
        if self.styles["doc_extra"]:
            if hasattr(sentenceGraph, "documentElement") and sentenceGraph.documentElement.get("origId") != None:
                extra["DOID"] = sentenceGraph.documentElement.get("origId")
        if self.styles["entity_extra"]:
            if entity1.get("origId") != None: extra["e1OID"] = entity1.get("origId")
            if entity2.get("origId") != None: extra["e2OID"] = entity2.get("origId")
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId 
        extra["directed"] = str(isDirected)
        if self.styles["sdb_merge"]:
            extra["sdb_merge"] = "True"
            #print extra
        
        return (categoryName, features, extra)
        
    
    def buildFeatures(self, sentenceGraph, entity1, entity2, token1, token2, path):
        features = {} 
        if not self.styles["no_trigger_features"]: # F 85.52 -> 85.55
            self.triggerFeatureBuilder.setFeatureVector(features)
            self.triggerFeatureBuilder.tag = "trg1_"
            self.triggerFeatureBuilder.buildFeatures(token1)
            self.triggerFeatureBuilder.tag = "trg2_"
            self.triggerFeatureBuilder.buildFeatures(token2)
            self.triggerFeatureBuilder.setFeatureVector(None)
        # REL features
        if self.styles["rel_features"] and not self.styles["no_task"]:
            self.relFeatureBuilder.setFeatureVector(features)
            self.relFeatureBuilder.tag = "rel1_"
            self.relFeatureBuilder.buildAllFeatures(sentenceGraph.tokens, sentenceGraph.tokens.index(token1))
            self.relFeatureBuilder.tag = "rel2_"
            self.relFeatureBuilder.buildAllFeatures(sentenceGraph.tokens, sentenceGraph.tokens.index(token2))
            self.relFeatureBuilder.setFeatureVector(None)
        if self.styles["bacteria_renaming"] and not self.styles["no_task"]:
            self.bacteriaRenamingFeatureBuilder.setFeatureVector(features)
            self.bacteriaRenamingFeatureBuilder.buildPairFeatures(entity1, entity2)
            #self.bacteriaRenamingFeatureBuilder.buildSubstringFeatures(entity1, entity2) # decreases perf. 74.76 -> 72.41
            self.bacteriaRenamingFeatureBuilder.setFeatureVector(None)
        if self.styles["co_features"] and not self.styles["no_task"]:
            e1Offset = Range.charOffsetToSingleTuple(entity1.get("charOffset"))
            e2Offset = Range.charOffsetToSingleTuple(entity2.get("charOffset"))
            if Range.contains(e1Offset, e2Offset):
                features[self.featureSet.getId("e1_contains_e2")] = 1
                if entity2.get("given") == "True":
                    features[self.featureSet.getId("e1_contains_e2name")] = 1
            if Range.contains(e2Offset, e1Offset):
                features[self.featureSet.getId("e2_contains_e1")] = 1
                if entity1.get("given") == "True":
                    features[self.featureSet.getId("e2_contains_e1name")] = 1
        if self.styles["drugbank_features"]:
            self.drugFeatureBuilder.setFeatureVector(features)
            self.drugFeatureBuilder.tag = "ddi_"
            self.drugFeatureBuilder.buildPairFeatures(entity1, entity2)  
            if self.styles["ddi_mtmx"]:
                self.drugFeatureBuilder.buildMTMXFeatures(entity1, entity2)
            self.drugFeatureBuilder.setFeatureVector(None)
        if self.styles["graph_kernel"]:
            self.graphKernelFeatureBuilder.setFeatureVector(features, entity1, entity2)
            self.graphKernelFeatureBuilder.buildGraphKernelFeatures(sentenceGraph, path)
            self.graphKernelFeatureBuilder.setFeatureVector(None)
        if self.styles["entity_type"]:
            e1Type = self.multiEdgeFeatureBuilder.getEntityType(entity1)
            e2Type = self.multiEdgeFeatureBuilder.getEntityType(entity2)
            features[self.featureSet.getId("e1_"+e1Type)] = 1
            features[self.featureSet.getId("e2_"+e2Type)] = 1
            features[self.featureSet.getId("distance_"+str(len(path)))] = 1
        if not self.styles["no_dependency"]:
            #print "Dep features"
            self.multiEdgeFeatureBuilder.setFeatureVector(features, entity1, entity2)
            #self.multiEdgeFeatureBuilder.buildStructureFeatures(sentenceGraph, paths) # remove for fast
            if not self.styles["disable_entity_features"]:
                self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
            self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
            if not self.styles["disable_terminus_features"]:
                self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
            if not self.styles["disable_single_element_features"]:
                self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, sentenceGraph)
            if not self.styles["disable_ngram_features"]:
                #print "NGrams"
                self.multiEdgeFeatureBuilder.buildPathGrams(2, path, sentenceGraph) # remove for fast
                self.multiEdgeFeatureBuilder.buildPathGrams(3, path, sentenceGraph) # remove for fast
                self.multiEdgeFeatureBuilder.buildPathGrams(4, path, sentenceGraph) # remove for fast
            #self.buildEdgeCombinations(path, edges, sentenceGraph, features) # remove for fast
            #if edges != None:
            #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[0], edges[0][1]+edges[1][0], "t1", sentenceGraph) # remove for fast
            #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[-1], edges[len(path)-1][len(path)-2]+edges[len(path)-2][len(path)-1], "t2", sentenceGraph) # remove for fast
            if not self.styles["disable_path_edge_features"]:
                self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, sentenceGraph)
            self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
            self.multiEdgeFeatureBuilder.setFeatureVector(None)
        if self.styles["nodalida"]:
            self.nodalidaFeatureBuilder.setFeatureVector(features, entity1, entity2)
            shortestPaths = self.nodalidaFeatureBuilder.buildShortestPaths(sentenceGraph.dependencyGraph, path)
            print shortestPaths
            if len(shortestPaths) > 0:
                self.nodalidaFeatureBuilder.buildNGrams(shortestPaths, sentenceGraph)
            self.nodalidaFeatureBuilder.setFeatureVector(None)
        if self.styles["linear_features"]:
            self.tokenFeatureBuilder.setFeatureVector(features)
            for i in range(len(sentenceGraph.tokens)):
                if sentenceGraph.tokens[i] == token1:
                    token1Index = i
                if sentenceGraph.tokens[i] == token2:
                    token2Index = i
            linearPreTag = "linfw_"
            if token1Index > token2Index: 
                token1Index, token2Index = token2Index, token1Index
                linearPreTag = "linrv_"
            self.tokenFeatureBuilder.buildLinearOrderFeatures(token1Index, sentenceGraph, 2, 2, preTag="linTok1")
            self.tokenFeatureBuilder.buildLinearOrderFeatures(token2Index, sentenceGraph, 2, 2, preTag="linTok2")
            # Before, middle, after
#                self.tokenFeatureBuilder.buildTokenGrams(0, token1Index-1, sentenceGraph, "bf")
#                self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, "bw")
#                self.tokenFeatureBuilder.buildTokenGrams(token2Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, "af")
            # before-middle, middle, middle-after
#                    self.tokenFeatureBuilder.buildTokenGrams(0, token2Index-1, sentenceGraph, linearPreTag+"bf", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, linearPreTag+"bw", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, linearPreTag+"af", max=2)
            self.tokenFeatureBuilder.setFeatureVector(None)
        if self.styles["random"]:
            self.randomFeatureBuilder.setFeatureVector(features)
            self.randomFeatureBuilder.buildRandomFeatures(100, 0.01)
            self.randomFeatureBuilder.setFeatureVector(None)
        if self.styles["genia_features"] and not self.styles["no_task"]:
            e1Type = entity1.get("type")
            e2Type = entity2.get("type")
            assert(entity1.get("given") in (None, "False"))
            if entity2.get("given") == "True":
                features[self.featureSet.getId("GENIA_target_protein")] = 1
            else:
                features[self.featureSet.getId("GENIA_nested_event")] = 1
            if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
                if entity2.get("given") == "True":
                    features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
                else:
                    features[self.featureSet.getId("GENIA_regulation_of_event")] = 1
        if self.styles["bi_features"]:
            # Make features based on entity types
            e1Type = entity1.get("type")
            e2Type = entity2.get("type")
            e1SuperType = str(self.getBISuperType(e1Type))
            e2SuperType = str(self.getBISuperType(e2Type))
            features[self.featureSet.getId("BI_e1_"+e1Type)] = 1
            features[self.featureSet.getId("BI_e2_"+e2Type)] = 1
            features[self.featureSet.getId("BI_e1sup_"+e1SuperType)] = 1
            features[self.featureSet.getId("BI_e2sup_"+e2SuperType)] = 1
            features[self.featureSet.getId("BI_e1e2_"+e1Type+"_"+e2Type)] = 1
            features[self.featureSet.getId("BI_e1e2sup_"+e1SuperType+"_"+e2SuperType)] = 1
        if self.styles["sdb_features"]:
            e1Type = entity1.get("type")
            e2Type = entity2.get("type")
            features[self.featureSet.getId("SDB_e1_"+e1Type)] = 1
            features[self.featureSet.getId("SDB_e2_"+e2Type)] = 1
            features[self.featureSet.getId("SDB_e1e2_"+e1Type+"_"+e2Type)] = 1
            if e1Type == e2Type:
                features[self.featureSet.getId("SDB_e1e2_equal")] = 1
                features[self.featureSet.getId("SDB_e1e2_equal_" + e1Type)] = 1
            e1SuperTypes = str(self.getSeeDevSuperTypes(e1Type))
            e2SuperTypes = str(self.getSeeDevSuperTypes(e2Type))
            for e1SuperType in e1SuperTypes:
                for e2SuperType in e2SuperTypes:
                    features[self.featureSet.getId("SDB_e1sup_"+e1SuperType)] = 1
                    features[self.featureSet.getId("SDB_e2sup_"+e2SuperType)] = 1
                    features[self.featureSet.getId("SDB_e1e2sup_"+e1SuperType+"_"+e2SuperType)] = 1
                    if e1SuperType == e2SuperType:
                        features[self.featureSet.getId("SDB_e1e2sup_equal")] = 1
                        features[self.featureSet.getId("SDB_e1e2sup_equal_" + e1SuperType)] = 1
        if self.styles["ontobiotope_features"]:
            self.ontobiotopeFeatureBuilder.setFeatureVector(features)
            self.ontobiotopeFeatureBuilder.buildOBOFeaturesForEntityPair(entity1, entity2)
            self.ontobiotopeFeatureBuilder.setFeatureVector(None)
        if self.styles["full_entities"]:
            e1Text = entity1.get("text").lower()
            e2Text = entity2.get("text").lower()
            features[self.featureSet.getId("FULL_e1_"+e1Text)] = 1
            features[self.featureSet.getId("FULL_e2_"+e2Text)] = 1
            for ep1 in e1Text.split():
                for ep2 in e2Text.split():
                    features[self.featureSet.getId("FULL_e1_"+ep1)] = 1
                    features[self.featureSet.getId("FULL_e2_"+ep2)] = 1
                    features[self.featureSet.getId("FULL_e1e2_"+ep1+"_"+ep2)] = 1
        if self.styles["evex"]:
            self.evexFeatureBuilder.setFeatureVector(features, entity1, entity2)
            self.evexFeatureBuilder.buildEdgeFeatures(entity1, entity2, token1, token2, path, sentenceGraph)
            self.evexFeatureBuilder.setFeatureVector(None)
        if self.styles["wordnet"]:
            self.wordNetFeatureBuilder.setFeatureVector(features, entity1, entity2)
            self.wordNetFeatureBuilder.buildFeaturesForEntityPair(token1, token2)
            self.wordNetFeatureBuilder.buildLinearFeatures(token1, sentenceGraph.tokens, tag="t1_")
            self.wordNetFeatureBuilder.buildLinearFeatures(token2, sentenceGraph.tokens, tag="t2_")
            self.wordNetFeatureBuilder.buildPathFeatures(path)
            self.wordNetFeatureBuilder.setFeatureVector(None)
        if self.styles["wordvector"]:
            self.wordVectorFeatureBuilder.setFeatureVector(features, entity1, entity2)
            self.wordVectorFeatureBuilder.buildFeatures(token1, "t1_")
            self.wordVectorFeatureBuilder.buildFeatures(token2, "t2_")
            self.wordVectorFeatureBuilder.buildLinearFeatures(token1, sentenceGraph.tokens, tag="t1_")
            self.wordVectorFeatureBuilder.buildLinearFeatures(token2, sentenceGraph.tokens, tag="t2_")
            self.wordVectorFeatureBuilder.buildPathFeatures(path)
            self.wordVectorFeatureBuilder.buildFBAFeatures(sentenceGraph.tokens, sentenceGraph.tokens.index(token1), sentenceGraph.tokens.index(token2))
            self.wordVectorFeatureBuilder.setFeatureVector(None)
        if self.styles["giuliano"]:
            self.giulianoFeatureBuilder.setFeatureVector(features, entity1, entity2)
            self.giulianoFeatureBuilder.buildEdgeFeatures(entity1, entity2, token1, token2, path, sentenceGraph)
            self.giulianoFeatureBuilder.setFeatureVector(None)
        
        return features
