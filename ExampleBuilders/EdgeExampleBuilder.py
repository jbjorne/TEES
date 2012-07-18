"""
Edge Examples
"""

import sys, os
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
#import Graph.networkx_v10rc1 as NX10
from Core.SimpleGraph import Graph
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
import Utils.Range as Range
from multiprocessing import Process

# For gold mapping
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML

class EdgeExampleBuilder(ExampleBuilder):
    """
    This example builder makes edge examples, i.e. examples describing
    the event arguments.
    """
    def __init__(self, style=None, length=None, types=[], featureSet=None, classSet=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 or (len(classSet.Ids)== 2 and classSet.getId("neg") == -1) )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        
        self._setDefaultParameters([
            "typed", "directed", "headsOnly", "graph_kernel", "noAnnType", "noMasking", "maxFeatures",
            "genia_limits", "epi_limits", "id_limits", "rel_limits", "bb_limits", "bi_limits", "co_limits",
            "genia_task1", "ontology", "nodalida", "bacteria_renaming", "trigger_features", "rel_features",
            "ddi_features", "ddi_mtmx", "evex", "giuliano", "random", "themeOnly", "causeOnly", "no_path", "entities", 
            "skip_extra_triggers", "headsOnly", "graph_kernel", "trigger_features", "no_task", "no_dependency", 
            "disable_entity_features", "disable_terminus_features", "disable_single_element_features", 
            "disable_ngram_features", "disable_path_edge_features", "no_linear", "subset", "binary", "pos_only",
            "entity_type", "filter_shortest_path", "maskTypeAsProtein"])
        self.styles = self.getParameters(style)
        if style == None: # no parameters given
            style["typed"] = style["directed"] = style["headsOnly"] = True
#        self.styles = style
#        if "selftrain_group" in self.styles:
#            self.selfTrainGroups = set()
#            if "selftrain_group-1" in self.styles:
#                self.selfTrainGroups.add("-1")
#            if "selftrain_group0" in self.styles:
#                self.selfTrainGroups.add("0")
#            if "selftrain_group1" in self.styles:
#                self.selfTrainGroups.add("1")
#            if "selftrain_group2" in self.styles:
#                self.selfTrainGroups.add("2")
#            if "selftrain_group3" in self.styles:
#                self.selfTrainGroups.add("3")
#            print >> sys.stderr, "Self-train-groups:", self.selfTrainGroups
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet, self.styles)
        # NOTE Temporarily re-enabling predicted range
        #self.multiEdgeFeatureBuilder.definePredictedValueRange([], None)
        if self.styles["graph_kernel"]:
            from FeatureBuilders.GraphKernelFeatureBuilder import GraphKernelFeatureBuilder
            self.graphKernelFeatureBuilder = GraphKernelFeatureBuilder(self.featureSet)
        if self.styles["noAnnType"]:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if self.styles["noMasking"]:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if self.styles["maxFeatures"]:
			self.multiEdgeFeatureBuilder.maximum = True
        if self.styles["genia_task1"]:
            self.multiEdgeFeatureBuilder.filterAnnTypes.add("Entity")
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        if self.styles["ontology"]:
            self.multiEdgeFeatureBuilder.ontologyFeatureBuilder = BioInferOntologyFeatureBuilder(self.featureSet)
        if self.styles["nodalida"]:
            self.nodalidaFeatureBuilder = NodalidaFeatureBuilder(self.featureSet)
        if self.styles["bacteria_renaming"]:
            self.bacteriaRenamingFeatureBuilder = BacteriaRenamingFeatureBuilder(self.featureSet)
        if self.styles["trigger_features"]:
            self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet, self.styles)
            self.triggerFeatureBuilder.useNonNameEntities = True
            if self.styles["genia_task1"]:
                self.triggerFeatureBuilder.filterAnnTypes.add("Entity")
            #self.bioinferOntologies = OntologyUtils.loadOntologies(OntologyUtils.g_bioInferFileName)
        if self.styles["rel_features"]:
            self.relFeatureBuilder = RELFeatureBuilder(featureSet)
        if self.styles["ddi_features"]:
            self.drugFeatureBuilder = DrugFeatureBuilder(featureSet)
        if self.styles["evex"]:
            self.evexFeatureBuilder = EVEXFeatureBuilder(featureSet)
        if self.styles["giuliano"]:
            self.giulianoFeatureBuilder = GiulianoFeatureBuilder(featureSet)
        self.pathLengths = length
        assert(self.pathLengths == None)
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
#        if sentenceGraph.interactionGraph.has_edge(t1, t2):
#            intEdges = sentenceGraph.interactionGraph.get_edge_data(t1, t2, default={})
#            # NOTE: Only works if keys are ordered integers
#            for i in range(len(intEdges)):
#                types.add(intEdges[i]["element"].get("type"))
#        if (not directed) and sentenceGraph.interactionGraph.has_edge(t2, t1):
#            intEdges = sentenceGraph.interactionGraph.get_edge(t2, t1, default={})
#            # NOTE: Only works if keys are ordered integers
#            for i in range(len(intEdges)):
#                types.add(intEdges[i]["element"].get("type"))
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
        
    def getCategoryName(self, sentenceGraph, e1, e2, directed=True, duplicateEntities=None):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
#        interactions = []
#        e1s = [e1]
#        if duplicateEntities != None and e1 in duplicateEntities:
#            e1s += duplicateEntities[e1]
#        e2s = [e2]
#        if duplicateEntities != None and e2 in duplicateEntities:
#            e2s += duplicateEntities[e2]
#        for entity1 in e1s:
#            for entity2 in e2s:
#                interactions = interactions + sentenceGraph.getInteractions(entity1, entity2)
#                if not directed:
#                    interactions = interactions + sentenceGraph.getInteractions(entity2, entity1)
        interactions = sentenceGraph.getInteractions(e1, e2, True)
        if not directed:
            interactions = interactions + sentenceGraph.getInteractions(e2, e1, True)
        #print interactions
        
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
            categoryName += name
        if categoryName != "":
            return categoryName
        else:
            return "neg"
    
    def isPotentialRELInteraction(self, e1, e2):
        if e1.get("type") == "Protein" and e2.get("type") == "Entity":
            return True
        else:
            return False

    def isPotentialBBInteraction(self, e1, e2, sentenceGraph):
        #if e1.get("type") == "Bacterium" and e2.get("type") in ["Host", "HostPart", "Geographical", "Environmental", "Food", "Medical", "Soil", "Water"]:
        # Note: "Environment" type is misspelled as "Environmental" in the BB-task documentation
        if e1.get("type") == "Bacterium" and e2.get("type") in ["Host", "HostPart", "Geographical", "Environment", "Food", "Medical", "Soil", "Water"]:
            return True
        elif e1.get("type") == "Host" and e2.get("type") == "HostPart":
            return True
        else:
            return False
    
    def getBISuperType(self, eType):
        if eType in ["GeneProduct", "Protein", "ProteinFamily", "PolymeraseComplex"]:
            return "ProteinEntity"
        elif eType in ["Gene", "GeneFamily", "GeneComplex", "Regulon", "Site", "Promoter"]:
            return "GeneEntity"
        else:
            return None
    
    def isPotentialBIInteraction(self, e1, e2, sentenceGraph, stats):
        e1Type = e1.get("type")
        e1SuperType = self.getBISuperType(e1Type)
        e2Type = e2.get("type")
        e2SuperType = self.getBISuperType(e2Type)
        
        tag = "(" + e1Type + "/" + e2Type + ")"
        if e1Type == "Regulon":
            if e2SuperType in ["GeneEntity", "ProteinEntity"]:
                return True
        if e1SuperType == "ProteinEntity":
            if e2Type in ["Site", "Promoter", "Gene", "GeneComplex"]:
                return True
        if e1Type in ["Action", "Transcription", "Expression"]:
            return True
        if e1Type == "Site":
            if e2SuperType == "GeneEntity":
                return True
        if e1Type == "Promoter":
            if e2SuperType in ["GeneEntity", "ProteinEntity"]:
                return True
        if e1SuperType in ["GeneEntity", "ProteinEntity"]:
            if e2SuperType in ["GeneEntity", "ProteinEntity"]:
                return True
        stats.filter("bi_limits") #+tag)
        return False

    def isPotentialEPIInteraction(self, e1, e2, sentenceGraph):
        if e1.get("type") != "Catalysis":
            if e1.get("type") in ["Protein", "Entity"]:
                return False
            elif e2.get("type") in ["Protein", "Entity"]:
                return True
            else:
                return False
        else: # Catalysis
            if e2.get("type") != "Entity":
                return True
            else:
                return False
        assert False, (e1.get("type"), e2.get("type"))

    def isPotentialIDInteraction(self, e1, e2, sentenceGraph):
        e1Type = e1.get("type")
        e2Type = e2.get("type")
        e1IsCore = e1Type in ["Protein", "Regulon-operon", "Two-component-system", "Chemical", "Organism"]
        e2IsCore = e2Type in ["Protein", "Regulon-operon", "Two-component-system", "Chemical", "Organism"]
        if e1IsCore:
            return False
        elif e1Type in ["Gene_expression", "Transcription"]:
            if e2Type in ["Protein", "Regulon-operon"]:
                return True
            else:
                return False
        elif e1Type in ["Protein_catabolism", "Phosphorylation"]:
            if e2Type == "Protein":
                return True
            else:
                return False
        elif e1Type == "Localization":
            if e2IsCore or e2Type == "Entity":
                return True
            else:
                return False
        elif e1Type in ["Binding", "Process"]:
            if e2IsCore:
                return True
            else:
                return False
        elif "egulation" in e1Type:
            if e2Type != "Entity":
                return True
            else:
                return False
        elif e1Type == "Entity":
            if e2IsCore:
                return True
            else:
                return False
        assert False, (e1Type, e2Type)
    
    def isPotentialCOInteraction(self, e1, e2, sentenceGraph):
        if e1.get("type") == "Exp" and e2.get("type") == "Exp":
            anaphoraTok = sentenceGraph.entityHeadTokenByEntity[e1]
            antecedentTok = sentenceGraph.entityHeadTokenByEntity[e2]
            antecedentTokenFound = False
            for token in sentenceGraph.tokens:
                if token == antecedentTok:
                    antecedentTokenFound = True
                if token == anaphoraTok: # if, not elif, to take into accoutn cases where e1Tok == e2Tok
                    if antecedentTokenFound:
                        return True
                    else:
                        return False
            assert False
        elif e1.get("type") == "Exp" and e2.get("type") == "Protein":
            return True
        else:
            return False
    
    def isPotentialGeniaInteraction(self, e1, e2):
        e1Type = e1.get("type")
        e2Type = e2.get("type")
        if e1Type == "Protein":
            return False
        elif e1Type in ["Entity", "Gene_expression", "Transcription", "Protein_catabolism", "Phosphorylation", "Binding"]:
            if e2Type == "Protein":
                return True
            else:
                return False
        elif e1Type == "Localization":
            if e2Type in ["Protein", "Entity"]:
                return True
            else:
                return False
        elif "egulation" in e1Type:
            if e2Type != "Entity":
                return True
            else:
                return False
        assert False, (e1Type, e2Type)

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
                
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        #examples = []
        exampleIndex = 0
        
        if self.styles["trigger_features"]: 
            self.triggerFeatureBuilder.initSentence(sentenceGraph)
        if self.styles["evex"]: 
            self.evexFeatureBuilder.initSentence(sentenceGraph)
            
        # Filter entities, if needed
        #mergedIds = None
        #duplicateEntities = None
        #entities = sentenceGraph.entities
        #entities, mergedIds, duplicateEntities = self.mergeEntities(sentenceGraph, False) # "no_duplicates" in self.styles)
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        entityToDuplicates = sentenceGraph.mergedEntityToDuplicates
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # Connect to optional gold graph
        if goldGraph != None:
            entityToGold = EvaluateInteractionXML.mapEntities(entities, goldGraph.entities)
        
        paths = None
        if not self.styles["no_path"]:
            ##undirected = sentenceGraph.getUndirectedDependencyGraph()
            #undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
            ###undirected = sentenceGraph.dependencyGraph.to_undirected()
            ####undirected = NX10.MultiGraph(sentenceGraph.dependencyGraph) This didn't work
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            #paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
            paths = undirected
            if self.styles["filter_shortest_path"] != None: # For DDI use filter_shortest_path=conj_and
                paths.resetAnalyses() # just in case
                paths.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        #for edge in sentenceGraph.dependencyGraph.edges:
        #    assert edge[2] != None
        #for edge in undirected.edges:
        #    assert edge[2] != None
        #if sentenceGraph.sentenceElement.get("id") == "GENIA.d70.s5":
        #    print [(x[0].get("id"), x[1].get("id"), x[2].get("id")) for x in sentenceGraph.dependencyGraph.edges]
        
        # Generate examples based on interactions between entities or interactions between tokens
        if self.styles["entities"]:
            loopRange = len(entities)
        else:
            loopRange = len(sentenceGraph.tokens)
        for i in range(loopRange-1):
            for j in range(i+1,loopRange):
                eI = None
                eJ = None
                if self.styles["entities"]:
                    eI = entities[i]
                    eJ = entities[j]
                    tI = sentenceGraph.entityHeadTokenByEntity[eI]
                    tJ = sentenceGraph.entityHeadTokenByEntity[eJ]
                    #if "no_ne_interactions" in self.styles and eI.get("isName") == "True" and eJ.get("isName") == "True":
                    #    continue
                    if eI.get("type") == "neg" or eJ.get("type") == "neg":
                        continue
                    if self.styles["skip_extra_triggers"]:
                        if eI.get("source") != None or eJ.get("source") != None:
                            continue
                else:
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                # only consider paths between entities (NOTE! entities, not only named entities)
                if self.styles["headsOnly"]:
                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                        continue
                
                if self.styles["directed"]:
                    # define forward
                    if self.styles["entities"]:
                        categoryName = self.getCategoryName(sentenceGraph, eI, eJ, True)
                        if goldGraph != None:
                            categoryName = self.getGoldCategoryName(goldGraph, entityToGold, eI, eJ, True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, True)
                    # make forward
                    self.exampleStats.beginExample(categoryName)
                    makeExample = True
                    if self.styles["genia_limits"] and not self.isPotentialGeniaInteraction(eI, eJ):
                        makeExample = False
                        self.exampleStats.filter("genia_limits")
                    if self.styles["genia_task1"] and (eI.get("type") == "Entity" or eJ.get("type") == "Entity"):
                        makeExample = False
                        self.exampleStats.filter("genia_task1")
                    if self.styles["rel_limits"] and not self.isPotentialRELInteraction(eI, eJ):
                        makeExample = False
                        self.exampleStats.filter("rel_limits")
                    if self.styles["co_limits"] and not self.isPotentialCOInteraction(eI, eJ, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("co_limits")
                    if self.styles["bb_limits"] and not self.isPotentialBBInteraction(eI, eJ, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("bb_limits")
                        if categoryName != "neg":
                            self.exampleStats.filter("bb_limits(" + categoryName + ":" + eI.get("type") + "/" + eJ.get("type") + ")")
                    if self.styles["bi_limits"] and not self.isPotentialBIInteraction(eI, eJ, sentenceGraph, self.exampleStats):
                        makeExample = False
                        #self.exampleStats.filter("bi_limits")
                    if self.styles["epi_limits"] and not self.isPotentialEPIInteraction(eI, eJ, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("epi_limits")
                    if self.styles["id_limits"] and not self.isPotentialIDInteraction(eI, eJ, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("id_limits")
#                    if self.styles["selftrain_limits"] and (eI.get("selftrain") == "False" or eJ.get("selftrain") == "False"):
#                        makeExample = False
#                        self.exampleStats.filter("selftrain_limits")
#                    if self.styles["selftrain_group"] and (eI.get("selftraingroup") not in self.selfTrainGroups or eJ.get("selftraingroup") not in self.selfTrainGroups):
#                        makeExample = False
#                        self.exampleStats.filter("selftrain_group")
                    if self.styles["pos_only"] and categoryName == "neg":
                        makeExample = False
                        self.exampleStats.filter("pos_only")
                    if makeExample:
                        #examples.append( self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ) )
                        ExampleUtils.appendExamples([self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ)], outfile)
                        exampleIndex += 1
                    self.exampleStats.endExample()
                    
                    # define reverse
                    if self.styles["entities"]:
                        categoryName = self.getCategoryName(sentenceGraph, eJ, eI, True)
                        if goldGraph != None:
                            categoryName = self.getGoldCategoryName(goldGraph, entityToGold, eJ, eI, True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tJ, tI, True)
                    # make reverse
                    self.exampleStats.beginExample(categoryName)
                    makeExample = True
                    if self.styles["genia_limits"] and not self.isPotentialGeniaInteraction(eJ, eI):
                        makeExample = False
                        self.exampleStats.filter("genia_limits")
                    if self.styles["genia_task1"] and (eI.get("type") == "Entity" or eJ.get("type") == "Entity"):
                        makeExample = False
                        self.exampleStats.filter("genia_task1")
                    if self.styles["rel_limits"] and not self.isPotentialRELInteraction(eJ, eI):
                        makeExample = False
                        self.exampleStats.filter("rel_limits")
                    if self.styles["co_limits"] and not self.isPotentialCOInteraction(eJ, eI, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("co_limits")
                    if self.styles["bb_limits"] and not self.isPotentialBBInteraction(eJ, eI, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("bb_limits")
                        if categoryName != "neg":
                            self.exampleStats.filter("bb_limits(" + categoryName + ":" + eJ.get("type") + "/" + eI.get("type") + ")")
                    if self.styles["bi_limits"] and not self.isPotentialBIInteraction(eJ, eI, sentenceGraph, self.exampleStats):
                        makeExample = False
                        #self.exampleStats.filter("bi_limits")
                    if self.styles["epi_limits"] and not self.isPotentialEPIInteraction(eJ, eI, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("epi_limits")
                    if self.styles["id_limits"] and not self.isPotentialIDInteraction(eJ, eI, sentenceGraph):
                        makeExample = False
                        self.exampleStats.filter("id_limits")
#                    if self.styles["selftrain_limits"] and (eI.get("selftrain") == "False" or eJ.get("selftrain") == "False"):
#                        makeExample = False
#                        self.exampleStats.filter("selftrain_limits")
#                    if self.styles["selftrain_group"] and (eI.get("selftraingroup") not in self.selfTrainGroups or eJ.get("selftraingroup") not in self.selfTrainGroups):
#                        makeExample = False
#                        self.exampleStats.filter("selftrain_group")
                    if self.styles["pos_only"] and categoryName == "neg":
                        makeExample = False
                        self.exampleStats.filter("pos_only")
                    if makeExample:
                        #examples.append( self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI) )
                        ExampleUtils.appendExamples([self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI)], outfile)
                        exampleIndex += 1
                    self.exampleStats.endExample()
                else:
                    if self.styles["entities"]:
                        categoryName = self.getCategoryName(sentenceGraph, eI, eJ, directed=False)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, directed=False)
                    self.exampleStats.beginExample(categoryName)
                    forwardExample = self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ)
                    if not self.styles["graph_kernel"]:
                        reverseExample = self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI)
                        forwardExample[2].update(reverseExample[2])
                    #examples.append(forwardExample)
                    ExampleUtils.appendExamples([forwardExample], outfile)
                    exampleIndex += 1
                    self.exampleStats.endExample()
        
        #return examples
        return exampleIndex
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, exampleIndex, entity1=None, entity2=None):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        # dummy return for speed testing
        #return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),1,{},{})
    
        # define features
        features = {}
        if True: #token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
            #if token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
            #    path = paths[token1][token2]
            #else:
            #    path = [token1, token2]
            if not self.styles["no_path"]:
                # directedPath reduces performance by 0.01 pp
                #directedPath = sentenceGraph.dependencyGraph.getPaths(token1, token2)
                #if len(directedPath) == 0:
                #    directedPath = sentenceGraph.dependencyGraph.getPaths(token2, token1)
                #    for dp in directedPath:
                #        dp.reverse()
                #if len(directedPath) == 0:
                #    path = paths.getPaths(token1, token2)
                #else:
                #    path = directedPath
                
                path = paths.getPaths(token1, token2)
                if len(path) > 0:
                    #if len(path) > 1:
                    #    print len(path)
                    path = path[0]
                    pathExists = True
                else:
                    path = [token1, token2]
                    pathExists = False
            else:
                path = [token1, token2]
                pathExists = False
            #print token1.get("id"), token2.get("id")
            assert(self.pathLengths == None)
            if self.pathLengths == None or len(path)-1 in self.pathLengths:
#                if not "no_ontology" in self.styles:
#                    self.ontologyFeatureBuilder.setFeatureVector(features)
#                    self.ontologyFeatureBuilder.buildOntologyFeaturesForPath(sentenceGraph, path)
#                    self.ontologyFeatureBuilder.setFeatureVector(None)
                if self.styles["trigger_features"]: # F 85.52 -> 85.55
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
                if self.styles["co_limits"] and not self.styles["no_task"]:
                    e1Offset = Range.charOffsetToSingleTuple(entity1.get("charOffset"))
                    e2Offset = Range.charOffsetToSingleTuple(entity2.get("charOffset"))
                    if Range.contains(e1Offset, e2Offset):
                        features[self.featureSet.getId("e1_contains_e2")] = 1
                        if entity2.get("isName") == "True":
                            features[self.featureSet.getId("e1_contains_e2name")] = 1
                    if Range.contains(e2Offset, e1Offset):
                        features[self.featureSet.getId("e2_contains_e1")] = 1
                        if entity1.get("isName") == "True":
                            features[self.featureSet.getId("e2_contains_e1name")] = 1
                if self.styles["ddi_features"]:
                    self.drugFeatureBuilder.setFeatureVector(features)
                    self.drugFeatureBuilder.tag = "ddi_"
                    self.drugFeatureBuilder.buildPairFeatures(entity1, entity2)  
                    if self.styles["ddi_mtmx"]:
                        self.drugFeatureBuilder.buildMTMXFeatures(entity1, entity2)
                    self.drugFeatureBuilder.setFeatureVector(None)
                #if "graph_kernel" in self.styles or not "no_dependency" in self.styles:
                #    #print "Getting edges"
                #    if token1 != token2 and pathExists:
                #        #print "g1"
                #        edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
                #        #print "g2"
                #    else:
                #        edges = None
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
                if not self.styles["no_linear"]:
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
                if self.styles["genia_limits"] and not self.styles["no_task"]:
                    e1Type = entity1.get("type")
                    e2Type = entity2.get("type")
                    assert(entity1.get("isName") == "False")
                    if entity2.get("isName") == "True":
                        features[self.featureSet.getId("GENIA_target_protein")] = 1
                    else:
                        features[self.featureSet.getId("GENIA_nested_event")] = 1
                    if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
                        if entity2.get("isName") == "True":
                            features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
                        else:
                            features[self.featureSet.getId("GENIA_regulation_of_event")] = 1
                if self.styles["bi_limits"]:
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
                if self.styles["evex"]:
                    self.evexFeatureBuilder.setFeatureVector(features, entity1, entity2)
                    self.evexFeatureBuilder.buildEdgeFeatures(entity1, entity2, token1, token2, path, sentenceGraph)
                    self.evexFeatureBuilder.setFeatureVector(None)
                if self.styles["giuliano"]:
                    self.giulianoFeatureBuilder.setFeatureVector(features, entity1, entity2)
                    self.giulianoFeatureBuilder.buildEdgeFeatures(entity1, entity2, token1, token2, path, sentenceGraph)
                    self.giulianoFeatureBuilder.setFeatureVector(None)
            else:
                features[self.featureSet.getId("always_negative")] = 1
                if self.styles["subset"]:
                    features[self.featureSet.getId("out_of_scope")] = 1
        else:
            features[self.featureSet.getId("always_negative")] = 1
            if self.styles["subset"]:
                features[self.featureSet.getId("out_of_scope")] = 1
            path = [token1, token2]
        # define extra attributes
        #if int(path[0].get("id").split("_")[-1]) < int(path[-1].get("id").split("_")[-1]):
        if int(path[0].get("charOffset").split("-")[0]) < int(path[-1].get("charOffset").split("-")[0]):
            #extra = {"xtype":"edge","type":"i","t1":path[0],"t2":path[-1]}
            extra = {"xtype":"edge","type":"i","t1":path[0].get("id"),"t2":path[-1].get("id")}
            extra["deprev"] = False
        else:
            #extra = {"xtype":"edge","type":"i","t1":path[-1],"t2":path[0]}
            extra = {"xtype":"edge","type":"i","t1":path[-1].get("id"),"t2":path[0].get("id")}
            extra["deprev"] = True
        if entity1 != None:
            #extra["e1"] = entity1
            extra["e1"] = entity1.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                #extra["e1GoldIds"] = mergedEntityIds[entity1]
                extra["e1DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity1]])
        if entity2 != None:
            #extra["e2"] = entity2
            extra["e2"] = entity2.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e2DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity2]])
                #extra["e2GoldIds"] = mergedEntityIds[entity2]
        extra["categoryName"] = categoryName
        if self.styles["bacteria_renaming"]:
            if entity1.get("text") != None and entity1.get("text") != "":
                extra["e1t"] = entity1.get("text").replace(" ", "---").replace(":","-COL-")
            if entity2.get("text") != None and entity2.get("text") != "":
                extra["e2t"] = entity2.get("text").replace(" ", "---").replace(":","-COL-")
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId       
        # make example
        if self.styles["binary"]:
            if categoryName != "neg":
                category = 1
            else:
                category = -1
            categoryName = "i"
        else:
            category = self.classSet.getId(categoryName)
        
        # NOTE: temporarily disable for replicating 110310 experiment
        #features[self.featureSet.getId("extra_constant")] = 1
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)