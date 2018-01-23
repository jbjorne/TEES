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

    ###########################################################################
    # Example Labels
    ###########################################################################
    
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