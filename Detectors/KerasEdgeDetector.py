import sys, os
import shutil
import gzip
import json
import itertools
import types
from Detector import Detector
from Core.SentenceGraph import getCorpusIterator
import Utils.ElementTreeUtils as ETUtils
from Core.IdSet import IdSet
import Utils.Parameters
import Utils.Settings as Settings
from Utils.EmbeddingIndex import EmbeddingIndex
from Utils.ProgressCounter import ProgressCounter
from ExampleBuilders.ExampleStats import ExampleStats
from Evaluators import EvaluateInteractionXML
from Utils import Parameters
from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import numpy
from keras.layers import Dense
from keras.models import Model, load_model
from keras.layers.core import Dropout, Flatten
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import merge
from itertools import chain
import sklearn.metrics
from sklearn.preprocessing.label import MultiLabelBinarizer
from sklearn.metrics.classification import classification_report
from keras.layers import Conv1D
from keras.layers.pooling import MaxPooling1D
from __builtin__ import isinstance
from Detectors.KerasDetectorBase import KerasDetectorBase
from ExampleWriters.EdgeExampleWriter import EdgeExampleWriter
import Utils.Range as Range

class KerasEdgeDetector(KerasDetectorBase):
    """
    The KerasDetector replaces the default SVM-based learning with a pipeline where
    sentences from the XML corpora are converted into adjacency matrix examples which
    are used to train the Keras model defined in the KerasDetector.
    """

    def __init__(self):
        KerasDetectorBase.__init__(self)
        self.tag = "edge-"
        self.exampleWriter = EdgeExampleWriter()
        #self.outsideLength = 5
        #self.exampleLength = 100
        
    ###########################################################################
    # Example Filtering
    ###########################################################################
    
    def isValidInteraction(self, e1, e2, structureAnalyzer,forceUndirected=False):
        return len(structureAnalyzer.getValidEdgeTypes(e1.get("type"), e2.get("type"), forceUndirected=forceUndirected)) > 0
    
    def keepExample(self, e1, e2, labels, isDirected, structureAnalyzer):
        makeExample = True
        if (not self.styles.get("no_auto_limits")) and not self.isValidInteraction(e1, e2, structureAnalyzer, forceUndirected=not isDirected):
            makeExample = False
            self.exampleStats.filter("auto_limits")
        if self.styles.get("genia_task1") and (e1.get("type") == "Entity" or e2.get("type") == "Entity"):
            makeExample = False
            self.exampleStats.filter("genia_task1")
        if self.styles.get("pos_only") and (len(labels) == 0 or (len(labels) == 1 and labels[0] == "neg")):
            makeExample = False
            self.exampleStats.filter("pos_only")
        if self.styles.get("no_self_loops") and ((e1 == e2) or (e1.get("headOffset") == e2.get("headOffset"))):
            makeExample = False
            self.exampleStats.filter("no_self_loops")
        return makeExample
    
    def keepDDI(self, token1, token2, entity1, entity2, tokens, tokenMap):
        e1Text = entity1.get("text").lower()
        e2Text = entity2.get("text").lower()
        if e1Text == e2Text:
            self.exampleStats.filter("entities_equal")
            return False
        e1Splits = e1Text.split()
        e2Splits = e2Text.split()
        if (len(e1Splits) == 1 and e1Splits[0] in e2Splits) or (len(e2Splits) == 1 and e2Splits[0] in e1Splits):
            self.exampleStats.filter("entity_substring")
            return False
        between = tokens[tokenMap[token1]["index"] + 1:tokenMap[token2]["index"]]
        if all([x.get("text") in (",", "(", ")", "or", "and", "-") for x in between]):
            self.exampleStats.filter("entities_list")
            return False
        return True

    ###########################################################################
    # Example Generation
    ###########################################################################
        
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        # example directionality
        if self.styles.get("directed") == None and self.styles.get("undirected") == None: # determine directedness from corpus
            examplesAreDirected = self.structureAnalyzer.hasDirectedTargets() if self.structureAnalyzer != None else True
        elif self.styles.get("directed"):
            assert self.styles.get("undirected") in [None, False]
            examplesAreDirected = True
        elif self.styles.get("undirected"):
            assert self.styles.get("directed") in [None, False]
            examplesAreDirected = False
            
        # Filter entities, if needed
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        #entityToDuplicates = sentenceGraph.mergedEntityToDuplicates
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # Connect to optional gold graph
        entityToGold = None
        if goldGraph != None:
            entityToGold = EvaluateInteractionXML.mapEntities(entities, goldGraph.entities)
        
#         paths = None
#         if not self.styles.get("no_path"):
#             undirected = sentenceGraph.dependencyGraph.toUndirected()
#             paths = undirected
#             if self.styles.get("filter_shortest_path") != None: # For DDI use filter_shortest_path=conj_and
#                 paths.resetAnalyses() # just in case
#                 paths.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})

        dg = sentenceGraph.dependencyGraph
        undirected = dg.toUndirected()
        edgeCounts = {x:len(dg.getInEdges(x) + dg.getOutEdges(x)) for x in sentenceGraph.tokens}
        
        # Pre-generate features for all tokens in the sentence
        tokenElements = sorted([(Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in sentenceGraph.tokens])
        tokens = []
        for i in range(len(tokenElements)):
            element = tokenElements[i][1]
            token = {"index":i, "element":element, "charOffset":tokenElements[i][0]}
            token["words"] = self.embeddings["words"].getIndex(element.get("text").lower(), "[out]")
            token["POS"] = self.embeddings["POS"].getIndex(element.get("POS"), "[out]")
            entityLabels = "---".join(sorted(set([x.get("type") for x in sentenceGraph.tokenIsEntityHead[sentenceGraph.tokens[i]]])))
            token["entities"] = self.embeddings["entities"].getIndex(entityLabels if entityLabels != "" else "[N/A]", "[out]")         
            tokens.append(token)
        tokenMap = {tokenElements[i][1]:tokens[i] for i in range(len(tokenElements))}
        
        # Generate examples based on interactions between entities or interactions between tokens
        if self.styles.get("token_nodes"):
            loopRange = len(tokens)
        else:
            loopRange = len(entities)
        for i in range(loopRange-1):
            for j in range(i+1,loopRange):
                eI = None
                eJ = None
                if self.styles.get("token_nodes"):
                    tI = tokens[i]["element"]
                    tJ = tokens[j]["element"]
                else:
                    eI = entities[i]
                    eJ = entities[j]
                    tI = sentenceGraph.entityHeadTokenByEntity[eI]
                    tJ = sentenceGraph.entityHeadTokenByEntity[eJ]
                    if eI.get("type") == "neg" or eJ.get("type") == "neg":
                        continue
                    if self.styles.get("skip_extra_triggers"):
                        if eI.get("source") != None or eJ.get("source") != None:
                            continue
                # only consider paths between entities (NOTE! entities, not only named entities)
                if self.styles.get("headsOnly"):
                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                        continue
                
                if examplesAreDirected:
                    self.buildExample(examples, tI, tJ, eI, eJ, tokens, tokenMap, sentenceGraph, goldGraph, entityToGold, undirected, edgeCounts)
                    self.buildExample(examples, tJ, tI, eJ, eI, tokens, tokenMap, sentenceGraph, goldGraph, entityToGold, undirected, edgeCounts)
                else:
                    if tokenMap[tJ]["index"] < tokenMap[tI]["index"]:
                        tI, tJ = tJ, tI
                        eI, eJ = eJ, eI
                    self.buildExample(examples, tI, tJ, eI, eJ, tokens, tokenMap, sentenceGraph, goldGraph, entityToGold, undirected, edgeCounts, False)
    
    def buildExample(self, examples, token1, token2, entity1, entity2, tokens, tokenMap, sentenceGraph, goldGraph, entityToGold, undirected, edgeCounts, isDirected=True):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        useNeg = "neg" in self.styles
        labels = self.getExampleLabels(entity1, entity2, token1, token2, sentenceGraph, goldGraph, entityToGold, isDirected, useNeg=useNeg)
        
        self.exampleStats.beginExample("---".join(labels))
        
        if not self.keepExample(entity1, entity2, labels, isDirected, self.structureAnalyzer):
            self.exampleStats.endExample()
            return
        
        if "ddi_filters" in self.styles and not self.keepDDI(token1, token2, entity1, entity2, tokens, tokenMap):
            self.exampleStats.endExample()
            return
        
        exampleLength = int(self.styles.get("el", -1)) if self.exampleLength == None else self.exampleLength
        if self.exampleLength == None:
            self.exampleLength = exampleLength
        outsideLength = int(self.styles.get("ol", 5))
        
        t1Index = tokenMap[token1]["index"]
        t2Index = tokenMap[token2]["index"]
#         span = abs(t1Index - t2Index)
#         if span + 2 * outsideLength > self.exampleLength:
#             self.exampleStats.filter("span")
#             self.exampleStats.endExample()
#             return None

        # define features
        paths = undirected.getPaths(token1, token2)
        if len(paths) == 0:
            path = [token1, token2]
            pathTokens = {token1:["[bgn]", "[gap]"], token2:["[gap]", "[end]"]}
        else:
            path = paths[0]
            pathTokens = {x:[None, None] for x in path}
            if len(path) == 2 and path[0] == path[1]: # self-loop
                assert token1 == token2
                pathTokens = {token1:["[bgn]", "[end]"]}
            else:
                pathTokens[path[0]][0] = "[bgn]"
                pathTokens[path[-1]][1] = "[end]"
                walks = sentenceGraph.dependencyGraph.getWalks(path)
                assert len(walks) > 0, ((len(paths), len(path)), [x.attrib for x in path], [entity1.attrib, entity2.attrib], [token1.attrib, token2.attrib])
                walk = walks[0]
                for i in range(len(path)-1): # len(pathTokens) == len(walk)
                    edge = walk[i]
                    if edge[0] == path[i]:
                        assert edge[1] == path[i + 1]
                        dep = edge[2].get("type") + ">"
                    else:
                        assert edge[0] == path[i + 1]
                        assert edge[1] == path[i]
                        dep = "<" + edge[2].get("type")
                    assert pathTokens[path[i]][1] == None, pathTokens
                    assert pathTokens[path[i + 1]][0] == None, pathTokens
                    pathTokens[path[i]][1] = dep
                    pathTokens[path[i + 1]][0] = dep
        #for path in paths:
        #for node in path:
        #    pathTokens.add(node)
        
        numTokens = len(tokens)
        begin = min(t1Index, t2Index) - outsideLength
        end = min(max(t1Index, t2Index) + 1 + outsideLength, numTokens)
        if exampleLength > 0 and end - begin > exampleLength:
            self.exampleStats.filter("span")
            self.exampleStats.endExample()
            return None
        rangeEnd = begin + exampleLength if exampleLength > 0 else end
        
        forward = t1Index < t2Index
        relTokens = []
        relMarker = "b" if forward else "a"
        for i in range(numTokens):
            if i == t1Index:
                relTokens.append("e1")
                relMarker = "m" if forward else "b"
            elif i == t2Index:
                relTokens.append("e2")
                relMarker = "a" if forward else "m"
            else:
                relTokens.append(relMarker)
        
        featureGroups = sorted(self.embeddings.keys())
        features = {x:[] for x in featureGroups}
        for i in range(begin, rangeEnd):
            if (i >= 0 and i < numTokens) and (i >= begin and i < end):
                token = tokens[i]
                #if self.debugGold:
                #    features["gold"].append(self.embeddings["gold"].getIndex(",".join(labels[j]), "[out]"))
                features["words"].append(token["words"])
                features["positions1"].append(self.embeddings["positions1"].getIndex(str(t1Index - i), "[out]"))
                features["positions2"].append(self.embeddings["positions2"].getIndex(str(t2Index - i), "[out]"))
                features["entities"].append(token["entities"])
                features["rel_token"].append(self.embeddings["rel_token"].getIndex(relTokens[i])) #"e1" if i == t1Index else ("e2" if i == t2Index else "N/A")))
                features["POS"].append(token["POS"])
                pathToken = pathTokens.get(token["element"])
                features["shortest_path"].append(self.embeddings["shortest_path"].getIndex("1" if pathToken != None else "0"))
                features["sp_in"].append(self.embeddings["sp_in"].getIndex(pathToken[0] if pathToken != None else "[N/A]"))
                features["sp_out"].append(self.embeddings["sp_out"].getIndex(pathToken[1] if pathToken != None else "[N/A]"))
                self.addPathEmbedding(token1, token["element"], sentenceGraph.dependencyGraph, undirected, edgeCounts, features, "path1_")
                self.addPathEmbedding(token2, token["element"], sentenceGraph.dependencyGraph, undirected, edgeCounts, features, "path2_")
            else:
                for featureGroup in featureGroups:
                    features[featureGroup].append(self.embeddings[featureGroup].getIndex("[pad]"))
        
        # define extra attributes
        extra = {"xtype":"edge", "type":"i", "t1":token1.get("id"), "t2":token2.get("id")}
        if entity1 != None:
            extra["e1"] = entity1.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e1DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity1]])
        if entity2 != None:
            extra["e2"] = entity2.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e2DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity2]])
        extra["categoryName"] = "---".join(labels)
        if self.styles.get("bacteria_renaming"):
            if entity1.get("text") != None and entity1.get("text") != "":
                extra["e1t"] = entity1.get("text").replace(" ", "---").replace(":","-COL-")
            if entity2.get("text") != None and entity2.get("text") != "":
                extra["e2t"] = entity2.get("text").replace(" ", "---").replace(":","-COL-")
        if self.styles.get("doc_extra"):
            if hasattr(sentenceGraph, "documentElement") and sentenceGraph.documentElement.get("origId") != None:
                extra["DOID"] = sentenceGraph.documentElement.get("origId")
        if self.styles.get("entity_extra"):
            if entity1.get("origId") != None: extra["e1OID"] = entity1.get("origId")
            if entity2.get("origId") != None: extra["e2OID"] = entity2.get("origId")
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId 
        extra["directed"] = str(isDirected)
        if self.styles.get("sdb_merge"):
            extra["sdb_merge"] = "True"
            #print extra
        
        self.exampleStats.endExample()
        examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(self.exampleIndex), "labels":labels, "features":features, "extra":extra})
        self.exampleIndex += 1
    
    def defineEmbeddings(self):
        print >> sys.stderr, "Defining embedding indices"
        embeddings = {}
        wordVectorPath = self.styles.get("wv", Settings.W2VFILE)
        wv_mem = int(self.styles.get("wv_mem", 100000))
        wv_map = int(self.styles.get("wv_map", 10000000))
        initVectors = ["[out]", "[pad]"]
        embeddings["words"] = EmbeddingIndex("words", None, wordVectorPath, wv_mem, wv_map, initVectors)
        dimEmbeddings = int(self.styles.get("de", 8)) #8 #32
        embeddings["positions1"] = EmbeddingIndex("positions1", dimEmbeddings, keys=initVectors)
        embeddings["positions2"] = EmbeddingIndex("positions2", dimEmbeddings, keys=initVectors)
        embeddings["entities"] = EmbeddingIndex("entities", dimEmbeddings, keys=initVectors)
        embeddings["rel_token"] = EmbeddingIndex("rel_token", dimEmbeddings, keys=initVectors)
        embeddings["POS"] = EmbeddingIndex("POS", dimEmbeddings, keys=initVectors, vocabularyType="POS")
        embeddings["shortest_path"] = EmbeddingIndex("shortest_path", dimEmbeddings, keys=initVectors)
        embeddings["sp_in"] = EmbeddingIndex("sp_in", dimEmbeddings, keys=initVectors, vocabularyType="directed_dependencies")
        embeddings["sp_out"] = EmbeddingIndex("sp_out", dimEmbeddings, keys=initVectors, vocabularyType="directed_dependencies")
        for i in range(self.pathDepth):
            for tag in ("path1_", "path2_"):
                embeddings[tag + str(i)] = EmbeddingIndex(tag + str(i), dimEmbeddings, keys=initVectors, vocabularyType="directed_dependencies")
        if self.debugGold:
            embeddings["gold"] = EmbeddingIndex("gold", dimEmbeddings, keys=initVectors)
        return embeddings

    ###########################################################################
    # Example Labels
    ###########################################################################
    
    def getExampleLabels(self, e1=None, e2=None, t1=None, t2=None, sentenceGraph=None, goldGraph=None, entityToGold=None, isDirected=True, structureAnalyzer=None, useNeg=False):
        if self.styles.get("token_nodes"):
            labels = self.getLabelsFromTokens(sentenceGraph, t1, t2, isDirected)
        else:
            labels = self.getLabels(sentenceGraph, e1, e2, isDirected)
            if goldGraph != None:
                labels = self.getGoldLabels(goldGraph, entityToGold, e1, e2, isDirected)
        if len(labels) == 0 and useNeg:
            labels.append("neg")
        return labels
    
    def getLabelsFromTokens(self, sentenceGraph, t1, t2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        labels = set()
        intEdges = sentenceGraph.interactionGraph.getEdges(t1, t2)
        if not directed:
            intEdges = intEdges + sentenceGraph.interactionGraph.getEdges(t2, t1)
        for intEdge in intEdges:
            labels.add(intEdge[2].get("type"))
        return sorted(labels)
        
    def getLabels(self, sentenceGraph, e1, e2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        interactions = sentenceGraph.getInteractions(e1, e2, True)
        if not directed and not self.styles.get("se10t8_undirected"):
            interactions = interactions + sentenceGraph.getInteractions(e2, e1, True)
        
        labels = set()
        for interaction in interactions:
            labels.add(interaction[2].get("type"))
        return sorted(labels)
    
    def getGoldLabels(self, goldGraph, entityToGold, e1, e2, directed=True):
        if len(entityToGold[e1]) > 0 and len(entityToGold[e2]) > 0:
            return self.getLabels(goldGraph, entityToGold[e1][0], entityToGold[e2][0], directed=directed)
        return []
