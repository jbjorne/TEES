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

class KerasEntityDetector(KerasDetectorBase):
    """
    The KerasDetector replaces the default SVM-based learning with a pipeline where
    sentences from the XML corpora are converted into adjacency matrix examples which
    are used to train the Keras model defined in the KerasDetector.
    """

    def __init__(self):
        KerasDetectorBase.__init__(self)
        self.tag = "entity-"
        self.exampleWriter = EntityExampleWriter()

    ###########################################################################
    # Example Generation
    ###########################################################################
        
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        """
        Build one example for each token of the sentence
        """
        # determine (manually or automatically) the setting for whether sentences with no given entities should be skipped
        buildForNameless = False
        if self.structureAnalyzer and not self.structureAnalyzer.hasGroupClass("GIVEN", "ENTITY"): # no given entities points to no separate NER program being used
            buildForNameless = True
        if self.styles.get("build_for_nameless"): # manually force the setting
            buildForNameless = True
        if self.styles.get("skip_for_nameless"): # manually force the setting
            buildForNameless = False
        
        # determine whether sentences with no given entities should be skipped
        if not self.styles.get("names"):
            namedEntityCount = 0
            for entity in sentenceGraph.entities:
                assert entity.get("given") in ("True", "False", None)
                if entity.get("given") == "True": # known data which can be used for features
                    namedEntityCount += 1
            # NOTE!!! This will change the number of examples and omit
            # all triggers (positive and negative) from sentences which
            # have no NE:s, possibly giving a too-optimistic performance
            # value. Such sentences can still have triggers from intersentence
            # interactions, but as such events cannot be recovered anyway,
            # looking for these triggers would be pointless.
            if namedEntityCount == 0 and not buildForNameless: # no names, no need for triggers
                return 0 #[]
        else:
            for key in sentenceGraph.tokenIsName.keys():
                sentenceGraph.tokenIsName[key] = False

        #outfile.write("[")
        # Prepare the indices
        numTokens = len(sentenceGraph.tokens)
        indices = [self.embeddings["words"].getIndex(sentenceGraph.tokens[i].get("text").lower(), "[out]") for i in range(numTokens)]
        labels, entityIds = zip(*[self.getEntityTypes(sentenceGraph.tokenIsEntityHead[sentenceGraph.tokens[i]]) for i in range(numTokens)])
        self.exampleLength = int(self.styles.get("el", 21)) #31 #9 #21 #5 #3 #9 #19 #21 #9 #5 #exampleLength = self.EXAMPLE_LENGTH if self.EXAMPLE_LENGTH != None else numTokens

        dg = sentenceGraph.dependencyGraph
        undirected = dg.toUndirected()
        edgeCounts = {x:len(dg.getInEdges(x) + dg.getOutEdges(x)) for x in sentenceGraph.tokens}
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]

            # CLASS
            #labels = self.getEntityTypes(sentenceGraph.tokenIsEntityHead[token])
            self.exampleStats.beginExample(",".join(labels[i]))
            
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token] and not self.styles.get("names") and not self.styles.get("all_tokens"):
                self.exampleStats.filter("name")
                self.exampleStats.endExample()
                continue
            
            tokens = []
            features = {x:[] for x in self.embeddings.keys()} #{"words":[], "positions":[], "named_entities":[], "POS":[], "gold":[]}
            featureGroups = sorted(features.keys())
            side = (self.exampleLength - 1) / 2
            windowIndex = 0
            for j in range(i - side, i + side + 1):
                if j >= 0 and j < numTokens:
                    token2 = sentenceGraph.tokens[j]
                    tokens.append(token2)
                    if self.debugGold:
                        features["gold"].append(self.embeddings["gold"].getIndex(",".join(labels[j]), "[out]"))
                    features["words"].append(indices[j])
                    features["positions"].append(self.embeddings["positions"].getIndex(str(windowIndex), "[out]"))
                    features["named_entities"].append(self.embeddings["named_entities"].getIndex("1" if (sentenceGraph.tokenIsEntityHead[token2] and sentenceGraph.tokenIsName[token2]) else "0", "[out]"))
                    features["POS"].append(self.embeddings["POS"].getIndex(token2.get("POS"), "[out]"))
                    self.addPathEmbedding(token, token2, sentenceGraph.dependencyGraph, undirected, edgeCounts, features)
                else:
                    tokens.append(None)
                    for featureGroup in featureGroups:
                        features[featureGroup].append(self.embeddings[featureGroup].getIndex("[pad]"))
                windowIndex += 1
            
            extra = {"xtype":"token","t":token.get("id")}
            if entityIds[i] != None:
                extra["goldIds"] = "/".join(entityIds[i]) # The entities to which this example corresponds
            examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(self.exampleIndex), "labels":labels[i], "features":features, "extra":extra}) #, "extra":{"eIds":entityIds}}
            self.exampleStats.endExample()
    
    def getEntityTypes(self, entities, useNeg=False):
        types = set()
        entityIds = set()
        for entity in entities:
            eType = entity.get("type")
            if entity.get("given") == "True" and self.styles.get("all_tokens"):
                continue
            if eType == "Entity" and self.styles.get("genia_task1"):
                continue
            else:
                types.add(eType)
                entityIds.add(entity.get("id"))
        if len(types) == 0 and useNeg:
            types.add("neg")
        return sorted(types), sorted(entityIds)
    
    def defineEmbeddings(self):
        print >> sys.stderr, "Defining embedding indices"
        embeddings = {}
        wordVectorPath = self.styles.get("wv", Settings.W2VFILE)
        wv_mem = int(self.styles.get("wv_mem", 100000))
        wv_map = int(self.styles.get("wv_map", 10000000))
        initVectors = ["[out]", "[pad]"]
        embeddings["words"] = EmbeddingIndex("words", None, wordVectorPath, wv_mem, wv_map, initVectors)
        dimEmbeddings = int(self.styles.get("de", 8)) #8 #32
        embeddings["positions"] = EmbeddingIndex("positions", dimEmbeddings, keys=initVectors)
        embeddings["named_entities"] = EmbeddingIndex("named_entities", dimEmbeddings, keys=initVectors, vocabularyType="POS")
        embeddings["POS"] = EmbeddingIndex("POS", dimEmbeddings, keys=initVectors)
        for i in range(self.pathDepth):
            embeddings["path" + str(i)] = EmbeddingIndex("path" + str(i), dimEmbeddings, keys=initVectors, vocabularyType="directed_dependencies")
        if self.debugGold:
            embeddings["gold"] = EmbeddingIndex("gold", dimEmbeddings, keys=initVectors)
        return embeddings