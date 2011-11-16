"""
Edge Examples
"""
__version__ = "$Revision: 1.1 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder
from FeatureBuilders.BioInferOntologyFeatureBuilder import BioInferOntologyFeatureBuilder
from FeatureBuilders.NodalidaFeatureBuilder import NodalidaFeatureBuilder
from FeatureBuilders.BacteriaRenamingFeatureBuilder import BacteriaRenamingFeatureBuilder
from FeatureBuilders.RELFeatureBuilder import RELFeatureBuilder
#import Graph.networkx_v10rc1 as NX10
from Core.SimpleGraph import Graph
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
#IF LOCAL
import Utils.BioInfer.OntologyUtils as OntologyUtils
from Utils.ProgressCounter import ProgressCounter
#ENDIF
import Range
import types
import Core.SentenceGraph as SentenceGraph

class IntersentenceEdgeExampleBuilder(ExampleBuilder):
    """
    This example builder makes edge examples, i.e. examples describing
    the event arguments.
    """
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
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        self.types = types

#    @classmethod
#    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
#        """
#        An interface for running the example builder without needing to create a class
#        """
#        classSet, featureSet = cls.getIdSets(idFileTag)
#        if style != None:
#            e = MultiEdgeExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
#        else:
#            e = MultiEdgeExampleBuilder(classSet=classSet, featureSet=featureSet)
#        sentences = cls.getSentences(input, parse, tokenization)
#        e.buildExamplesForSentences(sentences, output, idFileTag)

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        """
        An interface for running the example builder without needing to create a class
        """
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = IntersentenceEdgeExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
        else:
            e = IntersentenceEdgeExampleBuilder(classSet=classSet, featureSet=featureSet)
        # Load documents
        if type(input) != types.ListType:
            # Load corpus and make sentence graphs
            corpusElements = SentenceGraph.loadCorpus(input, parse, tokenization, False, True)
            
        else: # assume input is already a list of sentences
            assert(removeNameInfo == False)
            return input
        # run examplebuilder
        e.buildExamplesForDocuments(corpusElements.documentSentences, output, idFileTag)

    def buildExamplesForDocuments(self, documentSentences, output, idFileTag=None):            
        examples = []
        counter = ProgressCounter(len(documentSentences), "Build examples")
        
        #calculatePredictedRange(self, sentences)
        
        outfile = open(output, "wt")
        exampleCount = 0
        for document in documentSentences:
            counter.update(1, "Building examples ("+document[0].sentence.get("id")+"): ")
            examples = self.buildExamples(document)
            exampleCount += len(examples)
            #examples = self.preProcessExamples(examples)
            ExampleUtils.appendExamples(examples, outfile)
        outfile.close()
    
        print >> sys.stderr, "Examples built:", exampleCount
        print >> sys.stderr, "Features:", len(self.featureSet.getNames())
        #IF LOCAL
        if self.exampleStats.getExampleCount() > 0:
            self.exampleStats.printStats()
        #ENDIF
        # Save Ids
        if idFileTag != None: 
            print >> sys.stderr, "Saving class names to", idFileTag + ".class_names"
            self.classSet.write(idFileTag + ".class_names")
            print >> sys.stderr, "Saving feature names to", idFileTag + ".feature_names"
            self.featureSet.write(idFileTag + ".feature_names")
            
    def getCategoryName(self, sentence1, sentence2, e1, e2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        e1Id = e1.get("id")
        e2Id = e2.get("id")
        allInteractions = sentence1.interSentenceInteractions + sentence2.interSentenceInteractions
        interactions = []
        #if len(allInteractions) > 0:
        #    print len(allInteractions)
        for interaction in allInteractions:
            if interaction.get("e1") == e1Id and interaction.get("e2") == e2Id:
                interactions.append(interaction)
        types = set()
        for interaction in interactions:
            types.add(interaction.get("type"))
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
    
    def isPotentialCOInteraction(self, e1, e2):
        if e1.get("type") == "Exp" and e2.get("type") == "Exp":
            return True
        else:
            return False
            
    def buildExamples(self, documentSentences):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        examples = []
        exampleIndex = 0
        
        for documentSentence in documentSentences:
            if documentSentence.sentenceGraph != None:
                documentSentence.sentenceGraph.undirected = documentSentence.sentenceGraph.dependencyGraph.toUndirected()
                documentSentence.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)
                documentSentence.triggerFeatureBuilder.useNonNameEntities = True
                documentSentence.triggerFeatureBuilder.initSentence(documentSentence.sentenceGraph)
        
        # Generate examples based on interactions between entities or interactions between tokens
        maxDistance = 1
        for sentence1Index in range(len(documentSentences)):
            sentence1 = documentSentences[sentence1Index]
            if sentence1.sentenceGraph == None:
                continue
            for sentence2Index in range(sentence1Index+1, min(sentence1Index+1+maxDistance, len(documentSentences))):
                sentence2 = documentSentences[sentence2Index]
                if sentence2.sentenceGraph == None:
                    continue
                if "entities" in self.styles:
                    loopRange1 = len(sentence1.sentenceGraph.entities)
                    loopRange2 = len(sentence2.sentenceGraph.entities)
                else:
                    loopRange = len(sentenceGraph.tokens)
                for i in range(loopRange1):
                    for j in range(loopRange2):
                        eI = None
                        eJ = None
                        if "entities" in self.styles:
                            eI = sentence1.sentenceGraph.entities[i]
                            eJ = sentence2.sentenceGraph.entities[j]
                            tI = sentence1.sentenceGraph.entityHeadTokenByEntity[eI]
                            tJ = sentence2.sentenceGraph.entityHeadTokenByEntity[eJ]
                            #if "no_ne_interactions" in self.styles and eI.get("isName") == "True" and eJ.get("isName") == "True":
                            #    continue
                            if eI.get("type") == "neg" or eJ.get("type") == "neg":
                                continue
                        else:
                            tI = sentenceGraph.tokens[i]
                            tJ = sentenceGraph.tokens[j]
                        # only consider paths between entities (NOTE! entities, not only named entities)
                        if "headsOnly" in self.styles:
                            if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                                continue
                        
                        if "directed" in self.styles:
                            # define forward
                            if "entities" in self.styles:
                                categoryName = self.getCategoryName(sentence1, sentence2, eI, eJ, True)
                            else:
                                categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, True)
                            # make forward
                            self.exampleStats.beginExample(categoryName)
                            makeExample = True
                            if ("co_limits" in self.styles) and not self.isPotentialCOInteraction(eI, eJ):
                                makeExample = False
                                self.exampleStats.filter("co_limits")
                            if makeExample:
                                examples.append( self.buildExample(sentence1, sentence2, categoryName, exampleIndex, eI, eJ) )
                                exampleIndex += 1
                            self.exampleStats.endExample()
                            
                            # define reverse
                            if "entities" in self.styles:
                                categoryName = self.getCategoryName(sentence2, sentence1, eJ, eI, True)
                            else:
                                categoryName = self.getCategoryNameFromTokens(sentenceGraph, tJ, tI, True)
                            # make reverse
                            self.exampleStats.beginExample(categoryName)
                            makeExample = True
                            if ("co_limits" in self.styles) and not self.isPotentialCOInteraction(eJ, eI):
                                makeExample = False
                                self.exampleStats.filter("co_limits")
                            if makeExample:
                                examples.append( self.buildExample(sentence2, sentence1, categoryName, exampleIndex, eJ, eI) )
                                exampleIndex += 1
                            self.exampleStats.endExample()
                        else:
                            if "entities" in self.styles:
                                categoryName = self.getCategoryName(sentenceGraph, eI, eJ, False)
                            else:
                                categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, False)
                            self.exampleStats.beginExample(categoryName)
                            forwardExample = self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ)
                            if not "graph_kernel" in self.styles:
                                reverseExample = self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI)
                                forwardExample[2].update(reverseExample[2])
                            examples.append(forwardExample)
                            exampleIndex += 1
                            self.exampleStats.endExample()
        
        return examples
    
    def getRootToken(self, sentenceGraph, token, visited=None, level=0):
        if visited == None: visited = set()
        inEdges = sentenceGraph.dependencyGraph.getInEdges(token)
        rv = None
        for inEdge in inEdges:
            if inEdge not in visited:
                visited.add(inEdge)
                rvNew = self.getRootToken(sentenceGraph, inEdge[0], visited, level+1)
                if rv == None or rvNew[1] > rv[1]:
                    rv = rvNew
        if rv == None:
            return (token, level)
        else:
            return rv
    
    def buildExample(self, sentence1, sentence2, categoryName, exampleIndex, entity1=None, entity2=None):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        # define features
        features = {}
        e1Token = sentence1.sentenceGraph.entityHeadTokenByEntity[entity1]
        e2Token = sentence2.sentenceGraph.entityHeadTokenByEntity[entity2]
        e1RootToken = self.getRootToken(sentence1.sentenceGraph, e1Token)[0]
        e2RootToken = self.getRootToken(sentence2.sentenceGraph, e2Token)[0]
        e1Path = sentence1.sentenceGraph.undirected.getPaths(e1Token, e1RootToken)
        e2Path = sentence2.sentenceGraph.undirected.getPaths(e2RootToken, e2Token)
        if len(e1Path) > 0: e1Path = e1Path[0]
        else: e1Path = [e1Token, e1RootToken]
        if len(e2Path) > 0: e2Path = e2Path[0]
        else: e2Path = [e2RootToken, e2Token]
        # build features
        if "trigger_features" in self.styles: # F 85.52 -> 85.55
            sentence1.triggerFeatureBuilder.setFeatureVector(features)
            sentence1.triggerFeatureBuilder.tag = "trg1_"
            sentence1.triggerFeatureBuilder.buildFeatures(e1Token)
            sentence1.triggerFeatureBuilder.setFeatureVector(None)
            sentence2.triggerFeatureBuilder.setFeatureVector(features)
            sentence2.triggerFeatureBuilder.tag = "trg2_"
            sentence2.triggerFeatureBuilder.buildFeatures(e2Token)
            sentence2.triggerFeatureBuilder.setFeatureVector(None)
        if "entity_type" in self.styles:
            features[self.featureSet.getId("e1_"+entity1.get("type"))] = 1
            features[self.featureSet.getId("e2_"+entity2.get("type"))] = 1
            features[self.featureSet.getId("distance_"+str(len(e1Path) + len(e2Path)))] = 1
        if not "no_dependency" in self.styles:
            for pair in ([e1Path, "e1Edge_", entity1, None, sentence1], [e2Path, "e2Edge_", None, entity2, sentence2]):
                self.multiEdgeFeatureBuilder.tag = pair[1]
                self.multiEdgeFeatureBuilder.setFeatureVector(features, pair[2], pair[3])
                #self.multiEdgeFeatureBuilder.buildStructureFeatures(sentenceGraph, paths) # remove for fast
                if not "disable_entity_features" in self.styles:
                    self.multiEdgeFeatureBuilder.buildEntityFeatures(pair[4].sentenceGraph)
                self.multiEdgeFeatureBuilder.buildPathLengthFeatures(pair[0])
                if not "disable_terminus_features" in self.styles:
                    self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(pair[0], pair[4].sentenceGraph) # remove for fast
                if not "disable_single_element_features" in self.styles:
                    self.multiEdgeFeatureBuilder.buildSingleElementFeatures(pair[0], pair[4].sentenceGraph)
                if not "disable_ngram_features" in self.styles:
                    #print "NGrams"
                    self.multiEdgeFeatureBuilder.buildPathGrams(2, pair[0], pair[4].sentenceGraph) # remove for fast
                    self.multiEdgeFeatureBuilder.buildPathGrams(3, pair[0], pair[4].sentenceGraph) # remove for fast
                    self.multiEdgeFeatureBuilder.buildPathGrams(4, pair[0], pair[4].sentenceGraph) # remove for fast
                #self.buildEdgeCombinations(path, edges, sentenceGraph, features) # remove for fast
                #if edges != None:
                #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[0], edges[0][1]+edges[1][0], "t1", sentenceGraph) # remove for fast
                #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[-1], edges[len(path)-1][len(path)-2]+edges[len(path)-2][len(path)-1], "t2", sentenceGraph) # remove for fast
                if not "disable_path_edge_features" in self.styles:
                    self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(pair[0], pair[4].sentenceGraph)
                self.multiEdgeFeatureBuilder.buildSentenceFeatures(pair[4].sentenceGraph)
                self.multiEdgeFeatureBuilder.setFeatureVector(None)
#            if not "no_linear" in self.styles:
#                self.tokenFeatureBuilder.setFeatureVector(features)
#                for i in range(len(sentenceGraph.tokens)):
#                    if sentenceGraph.tokens[i] == token1:
#                        token1Index = i
#                    if sentenceGraph.tokens[i] == token2:
#                        token2Index = i
#                linearPreTag = "linfw_"
#                if token1Index > token2Index: 
#                    token1Index, token2Index = token2Index, token1Index
#                    linearPreTag = "linrv_"
#                self.tokenFeatureBuilder.buildLinearOrderFeatures(token1Index, sentenceGraph, 2, 2, preTag="linTok1")
#                self.tokenFeatureBuilder.buildLinearOrderFeatures(token2Index, sentenceGraph, 2, 2, preTag="linTok2")
            # Before, middle, after
#                self.tokenFeatureBuilder.buildTokenGrams(0, token1Index-1, sentenceGraph, "bf")
#                self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, "bw")
#                self.tokenFeatureBuilder.buildTokenGrams(token2Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, "af")
            # before-middle, middle, middle-after
#                    self.tokenFeatureBuilder.buildTokenGrams(0, token2Index-1, sentenceGraph, linearPreTag+"bf", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, linearPreTag+"bw", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, linearPreTag+"af", max=2)
#                self.tokenFeatureBuilder.setFeatureVector(None)
#            if "random" in self.styles:
#                self.randomFeatureBuilder.setFeatureVector(features)
#                self.randomFeatureBuilder.buildRandomFeatures(100, 0.01)
#                self.randomFeatureBuilder.setFeatureVector(None)
        # define extra attributes
        extra = {"xtype":"edge","type":"i","t1":e1Token.get("id"),"t2":e2Token.get("id")}
        if entity1 != None:
            #extra["e1"] = entity1
            extra["e1"] = entity1.get("id")
        if entity2 != None:
            #extra["e2"] = entity2
            extra["e2"] = entity2.get("id")
        extra["categoryName"] = categoryName    
        # make example
        if "binary" in self.styles:
            if categoryName != "neg":
                category = 1
            else:
                category = -1
            categoryName = "i"
        else:
            category = self.classSet.getId(categoryName)
        
        return (sentence1.sentence.get("id")+".x"+str(exampleIndex),category,features,extra)