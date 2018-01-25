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

    ###########################################################################
    # Example Generation
    ###########################################################################
        
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        exampleIndex = 0
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
        entityToDuplicates = sentenceGraph.mergedEntityToDuplicates
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # Connect to optional gold graph
        entityToGold = None
        if goldGraph != None:
            entityToGold = EvaluateInteractionXML.mapEntities(entities, goldGraph.entities)
        
        paths = None
        if not self.styles.get("no_path"):
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            paths = undirected
            if self.styles.get("filter_shortest_path") != None: # For DDI use filter_shortest_path=conj_and
                paths.resetAnalyses() # just in case
                paths.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        tokens = sorted([(Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in sentenceGraph.tokens])
        tokenIndexById = {tokens[i][1].get("id"):i for i in range(len(tokens))}
        
        # Generate examples based on interactions between entities or interactions between tokens
        if self.styles.get("token_nodes"):
            loopRange = len(sentenceGraph.tokens)
        else:
            loopRange = len(entities)
        for i in range(loopRange-1):
            for j in range(i+1,loopRange):
                eI = None
                eJ = None
                if self.styles.get("token_nodes"):
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
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
                    exampleIndex += self.buildExample(tI, tJ, eI, eJ, exampleIndex)
                    exampleIndex += self.buildExample(tJ, tI, eJ, eI, exampleIndex)
                else:
                    if tokenIndexById(tI.get("id")) > tokenIndexById(tI.get("id")):
                        tI, tJ = tJ, tI
                        eI, eJ = eJ, eI
                    exampleIndex += self.buildExample(tI, tJ, paths, sentenceGraph, eI, eJ)
        return exampleIndex
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, entity1=None, entity2=None, structureAnalyzer=None, isDirected=True):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        labels = self.getExampleLabels(entity1, entity2, token1, token2, sentenceGraph, goldGraph, entityToGold, isDirected, structureAnalyzer=structureAnalyzer)
        
        self.exampleStats.beginExample("---".join(labels))
        
        t1Index = tokenIndexById(token1.get("id"))
        t2Index = tokenIndexById(token2.get("id"))
        span = abs(t1Index - t2Index)
        if span > maxSpan:
            self.exampleStats.filter("span")
            self.exampleStats.endExample()
            return None
        
        begin = min(t1Index, t2Index) - 5
        
        features = {x:[] for x in self.embeddings.keys()}
        windowIndex = 0
        for i in range(begin, begin + exampleSpan):
            if i >= 0 and i < numTokens:
                token = sentenceGraph.tokens[j]
                #if self.debugGold:
                #    features["gold"].append(self.embeddings["gold"].getIndex(",".join(labels[j]), "[out]"))
                features["words"].append(wordIndices[j])
                features["positions"].append(self.embeddings["positions"].getIndex(str(t1Distance) + "_" + str(t2Distance), "[out]"))
                features["entities"].append(self.embeddings["named_entities"].getIndex("1" if (sentenceGraph.tokenIsEntityHead[token] and sentenceGraph.tokenIsName[token2]) else "0", "[out]"))
                features["POS"].append(self.embeddings["POS"].getIndex(token.get("POS"), "[out]"))
                self.addPathEmbedding(token, token2, sentenceGraph.dependencyGraph, undirected, edgeCounts, features)
            else:
                tokens.append(None)
                for featureGroup in featureGroups:
                    features[featureGroup].append(self.embeddings[featureGroup].getIndex("[pad]"))
            windowIndex += 1
        
        # define extra attributes
        extra = {}
        if entity1 != None:
            extra["e1"] = entity1.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e1DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity1]])
        if entity2 != None:
            extra["e2"] = entity2.get("id")
            if sentenceGraph.mergedEntityToDuplicates != None:
                extra["e2DuplicateIds"] = ",".join([x.get("id") for x in sentenceGraph.mergedEntityToDuplicates[entity2]])
        extra["categoryName"] = categoryName
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
        return {"id":sentenceGraph.getSentenceId()+".x"+str(exampleIndex), "labels":labels, "features":features, "extra":extra}

    ###########################################################################
    # Example Labels
    ###########################################################################
    
    def getExampleLabels(self, e1=None, e2=None, t1=None, t2=None, sentenceGraph=None, goldGraph=None, entityToGold=None, isDirected=True, structureAnalyzer=None, useNeg=False):
        if self.styles.get("token_nodes"):
            labels = self.getLabelsFromTokens(sentenceGraph, t1, t2, isDirected)
        else:
            labels = self.getLabels(sentenceGraph, e1, e2, isDirected)
            if goldGraph != None:
                labels = self.getGoldCategoryName(goldGraph, entityToGold, e1, e2, isDirected)
        if len(labels) == 0 and useNeg:
            labels.add("neg")
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
        if not directed and not self.styles["se10t8_undirected"]:
            interactions = interactions + sentenceGraph.getInteractions(e2, e1, True)
        
        labels = set()
        for interaction in interactions:
            labels.add(interaction[2].get("type"))
        return sorted(labels)