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
        if not self.styles.get("no_path"):
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            paths = undirected
            if self.styles.get("filter_shortest_path") != None: # For DDI use filter_shortest_path=conj_and
                paths.resetAnalyses() # just in case
                paths.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
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
                
                examples = self.buildExamplesForPair(tI, tJ, paths, sentenceGraph, goldGraph, entityToGold, eI, eJ, structureAnalyzer, examplesAreDirected)
                for categoryName, features, extra in examples:
                    # make example
                    if self.styles.get("binary"):
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
        if not self.styles.get("no_path"):
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
        
        return (categoryName, features, extra)

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