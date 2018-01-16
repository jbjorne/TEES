import sys, os
from Detector import Detector
import itertools
from ExampleBuilders.KerasExampleBuilder import KerasExampleBuilder
from Core.SentenceGraph import getCorpusIterator
import numpy as np
import xml.etree.ElementTree as ET
import Utils.ElementTreeUtils as ETUtils
from Core.IdSet import IdSet
import Utils.Parameters
import Utils.STFormat
import gzip
from collections import OrderedDict
import json
from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D
from keras.models import Model, Sequential, load_model
from keras.layers.normalization import BatchNormalization
from keras.layers.core import Activation, Reshape, Permute, Dropout, Flatten
from keras.optimizers import SGD, Adam
from keras.layers.local import LocallyConnected2D
from keras.layers.wrappers import TimeDistributed
from keras.callbacks import EarlyStopping, ModelCheckpoint
from Detectors import SingleStageDetector
import Utils.Settings as Settings
from keras.layers.embeddings import Embedding
from keras.layers import merge
from keras.layers.merge import Concatenate
import keras.backend as K
from itertools import product, chain
from functools import partial
from numpy import reshape
from collections import defaultdict
import types
import sklearn.metrics
import sklearn
from Utils.ProgressCounter import ProgressCounter
from ExampleBuilders.ExampleStats import ExampleStats
from Utils.Libraries.wvlib_light.lwvlib import WV
import numpy
from sklearn.preprocessing.label import MultiLabelBinarizer
from sklearn.utils.class_weight import compute_sample_weight,\
    compute_class_weight
from sklearn.metrics.classification import classification_report
from keras.layers import Conv1D
from keras.layers.pooling import MaxPooling1D, GlobalMaxPooling1D
import shutil
from Evaluators import EvaluateInteractionXML
from Core import ExampleUtils
from Utils import Parameters
from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

# ###############################################################################
# import tensorflow as tf
# import random as rn
# # The below is necessary in Python 3.2.3 onwards to
# # have reproducible behavior for certain hash-based operations.
# # See these references for further details:
# # https://docs.python.org/3.4/using/cmdline.html#envvar-PYTHONHASHSEED
# # https://github.com/keras-team/keras/issues/2280#issuecomment-306959926
# os.environ['PYTHONHASHSEED'] = '0'
# # The below is necessary for starting Numpy generated random numbers
# # in a well-defined initial state.
# numpy.random.seed(42)
# # The below is necessary for starting core Python generated random numbers
# # in a well-defined state.
# rn.seed(12345)
# # Force TensorFlow to use single thread.
# # Multiple threads are a potential source of
# # non-reproducible results.
# # For further details, see: https://stackoverflow.com/questions/42022950/which-seeds-have-to-be-set-where-to-realize-100-reproducibility-of-training-res
# session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
# # The below tf.set_random_seed() will make random number generation
# # in the TensorFlow backend have a well-defined initial state.
# # For further details, see: https://www.tensorflow.org/api_docs/python/tf/set_random_seed
# tf.set_random_seed(1234)
# sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
# K.set_session(sess)
# ###############################################################################

def normalized(a, axis=-1, order=2):
    l2 = numpy.atleast_1d(numpy.linalg.norm(a, order, axis))
    l2[l2==0] = 1
    return a / numpy.expand_dims(l2, axis)

def f1ScoreMetric(y_true, y_pred):
    return sklearn.metrics.f1_score(y_true, y_pred, average="micro")

class Embeddings():
    def __init__(self, name=None, dimVector=None, wordVectorPath=None, wvMem=100000, wvMap=10000000, keys=None):
        self._reset(name, dimVector, wordVectorPath, wvMem, wvMap, keys)
    
    def _reset(self, name, dimVector=None, wvPath=None, wvMem=100000, wvMap=10000000, keys=None, embeddingIndex=None):
        self.name = name
        self.embeddings = [] if embeddingIndex == None else None
        self.embeddingIndex = {} if embeddingIndex == None else embeddingIndex
        self.keyByIndex = {} if embeddingIndex == None else {embeddingIndex[x]:x for x in embeddingIndex.keys()}
        self.wvPath = wvPath
        self.wvMem = wvMem
        self.wvMap = wvMap
        self.wv = None
        if self.wvPath != None:
            print >> sys.stderr, "Loading word vectors", (wvMem, wvMap), "from", self.wvPath
            self.wv = WV.load(self.wvPath, wvMem, wvMap)
            assert dimVector == None or dimVector == self.wv.size
            self.dimVector = self.wv.size
        else:
            self.dimVector = dimVector if dimVector != None else 32
        self.initialKeys = [] if keys == None else keys
        #self.initialKeysInitialized = False
        for key in self.initialKeys:
            self._addEmbedding(key, numpy.zeros(self.dimVector))
    
    def _loadIndices(self, embeddingIndex):
        self.embeddingIndex = embeddingIndex
    
    def serialize(self):
        if self.wvPath != None:
            return {"name":self.name, "dimVector":self.dimVector, "wvPath":self.wvPath, "wvMem":self.wvMem, "wvMap":self.wvMap, "index":self.embeddingIndex}
        else:
            return {"name":self.name, "dimVector":self.dimVector, "index":self.embeddingIndex}
    
    def deserialize(self, obj):
        self._reset(obj["name"], obj.get("dimVector"), obj.get("wvPath"), obj.get("wvMem"), obj.get("wvMap"), None, obj.get("index"))
        return self
    
    def releaseWV(self):
        self.wv = None
    
    def _addEmbedding(self, key, vector):
        index = len(self.embeddings)
        assert key not in self.embeddingIndex
        assert index not in self.keyByIndex
        self.embeddingIndex[key] = len(self.embeddings)
        self.keyByIndex[index] = key
        self.embeddings.append(vector)
    
    def getKey(self, index):
        return self.keyByIndex[index]
    
    def getIndex(self, key, default=None):
        if key not in self.embeddingIndex:
            if self.wv != None:
                vector = self.wv.w_to_normv(key)
                if vector is not None:
                    #self.embeddingIndex[key] = len(self.embeddings)
                    #self.embeddings.append(vector)
                    self._addEmbedding(key, vector)
#                     if not self.initialKeysInitialized:
#                         for initialKey in self.initialKeys:
#                             assert self.embeddings[self.embeddingIndex[initialKey]] is None
#                             self.embeddings[self.embeddingIndex[initialKey]] = numpy.zeros(vector.size)
#                         self.initialKeysInitialized = True
            elif self.embeddings != None:
                self._addEmbedding(key, numpy.ones(self.dimVector)) #normalized(numpy.random.uniform(-1.0, 1.0, self.dimVector)))
        return self.embeddingIndex[key] if key in self.embeddingIndex else self.embeddingIndex[default]
    
    def makeLayers(self, dimExample, name, trainable=True):
        self.inputLayer = Input(shape=(dimExample,), name=name)
        self.embeddingLayer = Embedding(len(self.embeddings), 
                              self.embeddings[0].size, 
                              weights=[self.getEmbeddingMatrix(name)], 
                              input_length=dimExample,
                              trainable=trainable,
                              name=name + "_embeddings")(self.inputLayer)
        return self.inputLayer, self.embeddingLayer
    
    def getEmbeddingMatrix(self, name):
        print >> sys.stderr, "Making Embedding Matrix", name, (len(self.embeddings), self.embeddings[0].size), self.embeddingIndex.keys()[0:50], self.embeddings[-1]
        dimWordVector = len(self.embeddings[0])
        numWordVectors = len(self.embeddings)
        embedding_matrix = np.zeros((numWordVectors, dimWordVector))
        for i in range(len(self.embeddings)):
            embedding_matrix[i] = self.embeddings[i]
        return embedding_matrix

class KerasEntityDetector(Detector):
    """
    The KerasDetector replaces the default SVM-based learning with a pipeline where
    sentences from the XML corpora are converted into adjacency matrix examples which
    are used to train the Keras model defined in the KerasDetector.
    """

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "entity-"
        self.exampleWriter = EntityExampleWriter()
        self.evaluator = AveragingMultiClassEvaluator
        #self.EXAMPLE_LENGTH = 1 #None #130
        self.exampleLength = -1
        self.debugGold = False
    
    ###########################################################################
    # Main Pipeline Interface
    ###########################################################################
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None,
              workDir=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES", "MODEL"], fromStep, toStep)
        if self.checkStep("ANALYZE"):
            # General training initialization done at the beginning of the first state
            self.model = self.initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters-train")])
            self.saveStr(self.tag+"parse", parse, self.model)
            if task != None:
                self.saveStr(self.tag+"task", task, self.model)
            # Perform structure analysis
            self.structureAnalyzer.analyze([optData, trainData], self.model)
            print >> sys.stderr, self.structureAnalyzer.toString()
        self.styles = Utils.Parameters.get(exampleStyle)
        self.pathDepth = int(self.styles.get("path", 3))
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        exampleFiles = {"devel":self.workDir+self.tag+"opt-examples.json.gz", "train":self.workDir+self.tag+"train-examples.json.gz"}
        if self.checkStep("EXAMPLES"): # Generate the adjacency matrices
            self.buildExamples(self.model, ["devel", "train"], [optData, trainData], [exampleFiles["devel"], exampleFiles["train"]], saveIdsToModel=True)
        #print self.examples["devel"][0:2]
        self.showExample(self.examples["devel"][0])
        if self.checkStep("MODEL"): # Define and train the Keras model
            self.defineModel()
            self.fitModel()
        if workDir != None:
            self.setWorkDir("")
        self.exitState()
    
    def classify(self, data, model, output, parse=None, task=None, goldData=None, workDir=None, fromStep=None, omitSteps=None, validate=False):
        self.enterState(self.STATE_CLASSIFY)
        self.setWorkDir(workDir)
        if workDir == None:
            self.setTempWorkDir()
        model = self.openModel(model, "r")
        if parse == None: parse = self.getStr(self.tag+"parse", model)
        workOutputTag = os.path.join(self.workDir, os.path.basename(output) + "-")
        xml = self.classifyToXML(data, model, None, workOutputTag, 
            model.get(self.tag+"classifier-model", defaultIfNotExist=None), goldData, parse, float(model.getStr("recallAdjustParameter", defaultIfNotExist=1.0)))
        if (validate):
            self.structureAnalyzer.load(model)
            self.structureAnalyzer.validate(xml)
            ETUtils.write(xml, output+"-pred.xml.gz")
        else:
            shutil.copy2(workOutputTag+self.tag+"pred.xml.gz", output+"-pred.xml.gz")
        EvaluateInteractionXML.run(self.evaluator, xml, data, parse)
#         stParams = self.getBioNLPSharedTaskParams(self.bioNLPSTParams, model)
#         if stParams.get("convert"): #self.useBioNLPSTFormat:
#             extension = ".zip" if (stParams["convert"] == "zip") else ".tar.gz" 
#             Utils.STFormat.ConvertXML.toSTFormat(xml, output+"-events" + extension, outputTag=stParams["a2Tag"], writeExtra=(stParams["scores"] == True))
#             if stParams["evaluate"]: #self.stEvaluator != None:
#                 if task == None: 
#                     task = self.getStr(self.tag+"task", model)
#                 self.stEvaluator.evaluate(output+"-events" + extension, task)
        self.deleteTempWorkDir()
        self.exitState()
    
    def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, goldData=None, parse=None, recallAdjust=None, compressExamples=True, exampleStyle=None, useExistingExamples=False):
        model = self.openModel(model, "r")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        if not useExistingExamples:
            self.buildExamples(model, ["classification"], [data], [exampleFileName], [goldData], parse=parse, exampleStyle=exampleStyle)
        examples = self.examples["classification"]
        if classifierModel == None:
            classifierModel = model.get(self.tag + "model.hdf5")
        labelSet = IdSet(filename = model.get(self.tag + "labels.ids", False), locked=True)
        labelNames = [None] * len(labelSet.Ids)
        for label in labelSet.Ids:
            labelNames[labelSet.Ids[label]] = label
        print >> sys.stderr, "Classification labels", labelNames
        labels, _ = self.vectorizeLabels(examples, ["classification"], labelNames)
        features = self.vectorizeFeatures(examples, ["classification"])
        predictions, confidences = self.predict(labels["classification"], features["classification"], labelNames, classifierModel)
        if exampleStyle == None:
            exampleStyle = Parameters.get(model.getStr(self.tag+"example-style")) # no checking, but these should already have passed the ExampleBuilder
        self.structureAnalyzer.load(model)
        outExamples = []
        outPredictions = []
        for pred, conf, example in zip(predictions, confidences, examples):
            outExamples.append([example["id"], None, None, example["extra"]])
            outPredictions.append({"prediction":pred, "confidence":conf})
        return self.exampleWriter.write(outExamples, outPredictions, data, tag+self.tag+"pred.xml.gz", labelSet, parse, exampleStyle=exampleStyle, structureAnalyzer=self.structureAnalyzer)
    
    ###########################################################################
    # Example Generation
    ###########################################################################
    
    def getElementCounts(self, filename):
        if type(filename) in types.StringTypes:
            return {}
        print >> sys.stderr, "Counting elements:",
        if filename.endswith(".gz"):
            f = gzip.open(filename, "rt")
        else:
            f = open(filename, "rt")
        counts = {"documents":0, "sentences":0}
        for line in f:
            if "<document" in line:
                counts["documents"] += 1
            elif "<sentence" in line:
                counts["sentences"] += 1
        f.close()
        print >> sys.stderr, counts
        return counts
        
    def processCorpus(self, input, examples, gold=None, parse=None, tokenization=None):
        self.exampleStats = ExampleStats()
        #print >> sys.stderr, "Saving examples to", output
        # Create intermediate paths if needed
        #if os.path.dirname(output) != "" and not os.path.exists(os.path.dirname(output)):
        #    os.makedirs(os.path.dirname(output))
        # Open output file
        #outfile = gzip.open(output, "wt") if output.endswith(".gz") else open(output, "wt")
        
        # Build examples
        self.exampleCount = 0
        if type(input) in types.StringTypes:
            self.elementCounts = self.getElementCounts(input)
            self.progress = ProgressCounter(self.elementCounts.get("sentences"), "Build examples")
        
        removeIntersentenceInteractions = True
        inputIterator = getCorpusIterator(input, None, parse, tokenization, removeIntersentenceInteractions=removeIntersentenceInteractions)            
        goldIterator = []
        if gold != None:
            goldIterator = getCorpusIterator(gold, None, parse, tokenization, removeIntersentenceInteractions=removeIntersentenceInteractions)
        for inputSentences, goldSentences in itertools.izip_longest(inputIterator, goldIterator, fillvalue=None):
            if gold != None:
                assert goldSentences != None and inputSentences != None
            self.processDocument(inputSentences, goldSentences, examples)
        #outfile.close()
        self.progress.endUpdate()
        
        # Show statistics
        print >> sys.stderr, "Examples built:", self.exampleCount
        #print >> sys.stderr, "Features:", len(self.featureSet.getNames())
        #print >> sys.stderr, "Classes:", len(self.classSet.getNames())
        #print >> sys.stderr, "Style:", Utils.Parameters.toString(self.getParameters(self.styles))
        if self.exampleStats.getExampleCount() > 0:
            self.exampleStats.printStats()
    
    def processDocument(self, sentences, goldSentences, examples):
        #calculatePredictedRange(self, sentences)            
        for i in range(len(sentences)):
            sentence = sentences[i]
            goldSentence = None
            if goldSentences != None:
                goldSentence = goldSentences[i]
            self.progress.update(1, "Building examples ("+sentence.sentence.get("id")+"): ")
            self.processSentence(sentence, examples, goldSentence)
    
    def processSentence(self, sentence, examples, goldSentence=None):
        # Process the sentence
        if sentence.sentenceGraph != None:
            self.exampleCount += self.buildExamplesFromGraph(sentence.sentenceGraph, examples, goldSentence.sentenceGraph if goldSentence != None else None)
    
    def addPathEmbedding(self, token1, token2, dirGraph, undirGraph, edgeCounts, features):
        if self.pathDepth <= 0:
            return

        if token1 == token2:
            keys = ["[d0]"] * self.pathDepth
        else:
            paths = undirGraph.getPaths(token1, token2)
            path = paths[0] if len(paths) > 0 else None
            if path != None and len(path) <= self.pathDepth + 1:
                #key = "d" + str(len(paths[0]) - 1)
                walks = dirGraph.getWalks(path)
                walk = walks[0]
                keys = [] #pattern = []
                for i in range(len(path)-1): # len(pathTokens) == len(walk)
                    edge = walk[i]
                    if edge[0] == path[i]:
                        keys.append(edge[2].get("type") + ">")
                    else:
                        assert edge[1] == path[i]
                        keys.append(edge[2].get("type") + "<")
                while len(keys) < self.pathDepth:
                    keys.append("[N/A]")
                #key = "|".join(pattern)
            elif edgeCounts[token2] > 0: #len(graph.getInEdges(token2) + graph.getOutEdges(token2)) > 0:
                keys = ["[dMax]"] * self.pathDepth
            else:
                keys = ["[unconnected]"] * self.pathDepth
        for i in range(self.pathDepth):
            features["path" + str(i)].append(self.embeddings["path" + str(i)].getIndex(keys[i], "[out]"))
    
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        """
        Build one example for each token of the sentence
        """       
        exampleIndex = 0
        
        # determine (manually or automatically) the setting for whether sentences with no given entities should be skipped
        buildForNameless = False
        if self.structureAnalyzer and not self.structureAnalyzer.hasGroupClass("GIVEN", "ENTITY"): # no given entities points to no separate NER program being used
            buildForNameless = True
        if self.styles.get("build_for_nameless"): # manually force the setting
            buildForNameless = True
        if self.styles.get("skip_for_nameless"): # manually force the setting
            buildForNameless = False
        
        # determine whether sentences with no given entities should be skipped
        namedEntityHeadTokens = []
        if not self.styles.get("names"):
            namedEntityCount = 0
            for entity in sentenceGraph.entities:
                if entity.get("given") == "True": # known data which can be used for features
                    namedEntityCount += 1
            namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
            # NOTE!!! This will change the number of examples and omit
            # all triggers (positive and negative) from sentences which
            # have no NE:s, possibly giving a too-optimistic performance
            # value. Such sentences can still have triggers from intersentence
            # interactions, but as such events cannot be recovered anyway,
            # looking for these triggers would be pointless.
            if namedEntityCount == 0 and not buildForNameless: # no names, no need for triggers
                return 0 #[]
            
            if self.styles.get("pos_pairs"):
                namedEntityHeadTokens = self.getNamedEntityHeadTokens(sentenceGraph)
        else:
            for key in sentenceGraph.tokenIsName.keys():
                sentenceGraph.tokenIsName[key] = False

        #outfile.write("[")
        # Prepare the indices
        numTokens = len(sentenceGraph.tokens)
        indices = [self.embeddings["words"].getIndex(sentenceGraph.tokens[i].get("text").lower(), "[out]") for i in range(numTokens)]
        labels, entityIds = zip(*[self.getEntityTypes(sentenceGraph.tokenIsEntityHead[sentenceGraph.tokens[i]]) for i in range(numTokens)])
        self.exampleLength = int(self.styles.get("el", 21)) #31 #9 #21 #5 #3 #9 #19 #21 #9 #5 #exampleLength = self.EXAMPLE_LENGTH if self.EXAMPLE_LENGTH != None else numTokens
#         for i in range(numTokens):
#             if i < numTokens:
#                 token = sentenceGraph.tokens[i]
#                 text = token.get("text").lower()
#                 if text not in self.embeddingIndex:
#                     vector = self.wv.w_to_normv(text)
#                     if vector is not None:
#                         self.embeddingIndex[text] = len(self.embeddings)
#                         self.embeddings.append(vector)
#                         if self.embeddings[0] is None: # initialize the out-of-vocabulary vector
#                             self.embeddings[0] = numpy.zeros(vector.size)
#                             self.embeddings[1] = numpy.zeros(vector.size)
#                 index = self.embeddingIndex[text] if text in self.embeddingIndex else self.embeddingIndex["[out]"]
#             else:
#                 index = self.embeddingIndex["[padding]"]
#             indices.append(index)

        
        #undirected = None
        #edgeCounts = None
        #if "paths" in self.embeddings:
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
                #features["binary"].append([])
                #features["binary"][-1].append(1 if i == j else 0)
                if j >= 0 and j < numTokens:
                    token2 = sentenceGraph.tokens[j]
                    tokens.append(token2)
                    if self.debugGold:
                        features["gold"].append(self.embeddings["gold"].getIndex(",".join(labels[j]), "[out]"))
                    features["words"].append(indices[j])
                    features["positions"].append(self.embeddings["positions"].getIndex(windowIndex, "[out]"))
                    features["named_entities"].append(self.embeddings["named_entities"].getIndex(1 if (sentenceGraph.tokenIsEntityHead[token2] and sentenceGraph.tokenIsName[token2]) else 0, "[out]"))
                    features["POS"].append(self.embeddings["POS"].getIndex(token2.get("POS"), "[out]"))
                    self.addPathEmbedding(token, token2, sentenceGraph.dependencyGraph, undirected, edgeCounts, features)
                    #features["binary"][-1].append(1 if sentenceGraph.tokenIsName[sentenceGraph.tokens[j]] else 0)
                else:
                    tokens.append(None)
                    for featureGroup in featureGroups:
                        features[featureGroup].append(self.embeddings[featureGroup].getIndex("[pad]"))
                    #features["binary"][-1].append(0)
                windowIndex += 1
            
            extra = {"xtype":"token","t":token.get("id")}
            if entityIds[i] != None:
                extra["goldIds"] = "/".join(entityIds[i]) # The entities to which this example corresponds
            examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(exampleIndex), "labels":labels[i], "features":features, "tokens":tokens, "extra":extra}) #, "extra":{"eIds":entityIds}}
            #outfile.write("\n")
            #if exampleIndex > 0:
            #    outfile.write(",")
            #outfile.write(json.dumps(example))
            exampleIndex += 1
            self.exampleStats.endExample()
        #outfile.write("\n]")
        #return examples
        return exampleIndex
    
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
    
    def showExample(self, example, showKeys=True):
        features = example["features"]
        featureGroups = sorted(features.keys())
        exampleLength = len(features[featureGroups[0]])
        print >> sys.stderr, example["id"]
        print >> sys.stderr, ["index"] + featureGroups
        for i in range(exampleLength):
            line = [i]
            for group in featureGroups:
                feature = features[group][i]
                if group in self.embeddings and showKeys:
                    feature = self.embeddings[group].getKey(feature)
                line.append(feature)
            print >> sys.stderr, line
    
    ###########################################################################
    # Main Pipeline Steps
    ###########################################################################
    
    def buildExamples(self, model, setNames, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False, parse=None):
        """
        Runs the KerasExampleBuilder for the input XML files and saves the generated adjacency matrices
        into JSON files.
        """
        if exampleStyle == None:
            exampleStyle = model.getStr(self.tag+"example-style")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.structureAnalyzer.load(model)
        modelChanged = False
        # Load word vectors
        embeddingsPath = model.get(self.tag + "embeddings.json", False, None)
        if embeddingsPath != None:
            print >> sys.stderr, "Loading embedding indices from", embeddingsPath
            self.embeddings = self.loadEmbeddings(embeddingsPath)
        else:
            print >> sys.stderr, "Initialized embedding indices"
            self.embeddings = {}
            wordVectorPath = self.styles.get("wv", Settings.W2VFILE)
            wv_mem = int(self.styles.get("wv_mem", 100000))
            wv_map = int(self.styles.get("wv_map", 10000000))
            initVectors = ["[out]", "[pad]"]
            self.embeddings["words"] = Embeddings("words", None, wordVectorPath, wv_mem, wv_map, initVectors)
            dimEmbeddings = int(self.styles.get("de", 8)) #8 #32
            self.embeddings["positions"] = Embeddings("positions", dimEmbeddings, keys=initVectors)
            self.embeddings["named_entities"] = Embeddings("named_entities", dimEmbeddings, keys=initVectors)
            self.embeddings["POS"] = Embeddings("POS", dimEmbeddings, keys=initVectors)
            for i in range(self.pathDepth):
                self.embeddings["path" + str(i)] = Embeddings("path" + str(i), dimEmbeddings, keys=initVectors)
            if self.debugGold:
                self.embeddings["gold"] = Embeddings("gold", dimEmbeddings, keys=initVectors)
        # Make example for all input files
        self.examples = {x:[] for x in setNames}
        for setName, data, gold in itertools.izip_longest(setNames, datas, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName #, "to file", output 
            self.processCorpus(data, self.examples[setName], gold, parse)          
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if saveIdsToModel:
            print >> sys.stderr, "Saving embedding indices"
            self.saveEmbeddings(self.embeddings, model.get(self.tag + "embeddings.json", True))
            modelChanged = True
        if modelChanged:
            model.save()
        self.embeddings["words"].releaseWV()
    
    def saveEmbeddings(self, embeddings, outPath):
        with open(outPath, "wt") as f:
            json.dump([embeddings[x].serialize() for x in sorted(embeddings.keys())], f)
    
    def loadEmbeddings(self, inPath):
        embeddings = {}
        with open(inPath, "rt") as f:
            for obj in json.load(f):
                emb = Embeddings().deserialize(obj)
                embeddings[emb.name] = emb
        return embeddings
    
#     def makeEmbeddingMatrix(self, vectors):
#         dimWordVector = len(vectors[0])
#         numWordVectors = len(vectors)
#         embedding_matrix = np.zeros((numWordVectors, dimWordVector))
#         for i in range(len(vectors)):
#             embedding_matrix[i] = vectors[i]
#         return embedding_matrix
    
    def defineModel(self):
        """
        Defines the Keras model and compiles it.
        """
#         print >> sys.stderr, "Making Embedding Matrix"
#         embedding_matrix = self.makeEmbeddingMatrix(self.embeddings)
#         print >> sys.stderr, "Vocabulary size:", len(self.embeddings)
#         print >> sys.stderr, "Embedding size:", self.embeddings[0].size
        
        labelSet = set()
        for dataSet in ("train", "devel"):
            for example in self.examples[dataSet]:
                for label in example["labels"]:
                    labelSet.add(label)
        
        # The Embeddings
#         x1 = inputLayer1 = Input(shape=(self.exampleLength,), name='indices')
#         x1 = Embedding(len(self.embeddings), 
#                   self.embeddings[0].size, 
#                   weights=[embedding_matrix], 
#                   input_length=self.exampleLength,
#                   trainable=True)(inputLayer1)
        #wordsInput, wordsEmbedding = self.embeddings["words"].getInputLayer(trainable=True, name="indices")
        embNames = sorted(self.embeddings.keys())
        for embName in embNames:
            self.embeddings[embName].makeLayers(self.exampleLength, embName, embName != "words")
        # Other Features
        #x2 = inputLayer2 = Input(shape=(self.exampleLength,2), name='binary')
        # Merge the inputs
        merged_features = merge([self.embeddings[x].embeddingLayer for x in embNames], mode='concat', name="merged_features")
        merged_features = Dropout(float(self.styles.get("do", 0.1)))(merged_features)
        
#         # Main network
#         x = Conv1D(64, 11, activation='relu')(x)
#         x = Conv1D(64, 4, activation='relu')(x)
#         #x = MaxPooling1D(3)(x)
#         x = Conv1D(64, 4, activation='relu')(x)
#         #x = MaxPooling1D(3)(x)
#         #x = Conv1D(256, 3, activation='relu')(x)
#         #x = MaxPooling1D(3)(x)

        if self.styles.get("kernels") != "skip":
            convOutputs = []
            kernelSizes = [int(x) for x in self.styles.get("kernels", [1, 3, 5, 7])]
            numFilters = int(self.styles.get("nf", 32)) #32 #64
            for kernel in kernelSizes:
                subnet = Conv1D(numFilters, kernel, activation='relu', name='conv_' + str(kernel))(merged_features)
                #subnet = Conv1D(numFilters, kernel, activation='relu', name='conv2_' + str(kernel))(subnet)
                subnet = MaxPooling1D(pool_length=self.exampleLength - kernel + 1, name='maxpool_' + str(kernel))(subnet)
                #subnet = GlobalMaxPooling1D(name='maxpool_' + str(kernel))(subnet)
                subnet = Flatten(name='flat_' + str(kernel))(subnet)
                convOutputs.append(subnet)       
            layer = merge(convOutputs, mode='concat')
            layer = Dropout(float(self.styles.get("do", 0.1)))(layer)
        else:
            layer = Flatten()(merged_features)
        
        # Classification layers
        layer = Dense(int(self.styles.get("dense", 400)), activation='relu')(layer) #layer = Dense(800, activation='relu')(layer)
        layer = Dense(len(labelSet), activation='sigmoid')(layer)
        
        self.kerasModel = Model([self.embeddings[x].inputLayer for x in embNames], layer)
        
        learningRate = float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"] #, f1ScoreMetric]
        self.kerasModel.compile(optimizer=optimizer, loss="binary_crossentropy", metrics=metrics)
        
        self.kerasModel.summary()
   
    def fitModel(self):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """
        
        labels, labelNames = self.vectorizeLabels(self.examples, ["train", "devel"])
#         print >> sys.stderr, "Vectorizing labels"
#         mlb = MultiLabelBinarizer()
#         labels = {}
#         for dataSet in ("train", "devel"):
#             labels[dataSet] = [x["labels"] for x in self.examples[dataSet]]
#         mlb.fit_transform(labels["train"] + labels["devel"])
#         for dataSet in ("train", "devel"):
#             labels[dataSet] = numpy.array(mlb.transform(labels[dataSet]))
        
        print >> sys.stderr, "Labels:", labelNames
        labelWeights = {}
        for i in range(len(labelNames)):
            labelWeights[i] = 1.0 if labelNames[i] != "neg" else 0.001
        print >> sys.stderr, "Label weights:", labelWeights
        labelSet = IdSet(idDict={labelNames[i]:i for i in range(len(labelNames))})
        labelFileName = self.model.get(self.tag + "labels.ids", True)
        print >> sys.stderr, "Saving class names to", labelFileName
        labelSet.write(labelFileName)
        #print >> sys.stderr, compute_sample_weight("balanced", [{i:x[i] for i in x} for x in labels["train"]])
        #labelWeights = {x[0]:x[1] for x in enumerate(compute_class_weight("balanced", np.unique(labels["train"]), labels["train"]))}
        #print >> sys.stderr, "Label weights:", labelWeights
        
        features = self.vectorizeFeatures(self.examples, ("train", "devel"))
#         featureGroups = sorted(self.examples["train"][0]["features"].keys())
#         print >> sys.stderr, [((x.get("text"), x.get("POS")) if x != None else None) for x  in self.examples["train"][0]["tokens"]]
#         print >> sys.stderr, "Vectorizing features:", featureGroups
#         features = {"train":{}, "devel":{}}
#         for featureGroup in featureGroups:
#             for dataSet in ("train", "devel"):
#                 if self.exampleLength != None:
#                     for example in self.examples[dataSet]:
#                         assert len(example["features"][featureGroup]) == self.exampleLength, example
#                 features[dataSet][featureGroup] = numpy.array([x["features"][featureGroup] for x in self.examples[dataSet]])
#             print >> sys.stderr, featureGroup, features["train"][featureGroup].shape, features["train"][featureGroup][0]
        
#         if self.exampleLength != None:
#             for dataSet in ("train", "devel"):
#                 for example in self.examples[dataSet]:
#                     for fType in ("indices", "binary"):
#                         assert len(example["features"][fType]) == self.exampleLength, example
#         features = {"train":{}, "devel":{}}
#         for dataSet in ("train", "devel"):
#             features[dataSet]["indices"] = numpy.array([x["features"]["indices"] for x in self.examples[dataSet]])
#             features[dataSet]["binary"] = numpy.array([x["features"]["binary"] for x in self.examples[dataSet]])
#         
#         for fType in ("indices", "binary"):
#             print fType, features["train"][fType].shape, features["train"][fType][0]
        
        print >> sys.stderr, "Fitting model"
        patience = int(self.styles.get("patience", 10))
        print >> sys.stderr, "Early stopping patience:", patience
        es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
        bestModelPath = self.model.get(self.tag + "model.hdf5", True) #self.workDir + self.tag + 'model.hdf5'
        cp_cb = ModelCheckpoint(filepath=bestModelPath, save_best_only=True, verbose=1)
        self.kerasModel.fit(features["train"], labels["train"], #[sourceData], self.arrays["train"]["target"],
            epochs=100 if not "epochs" in self.styles else int(self.styles["epochs"]),
            batch_size=64,
            shuffle=True,
            validation_data=(features["devel"], labels["devel"]),
            class_weight=labelWeights,
            callbacks=[es_cb, cp_cb])
        self.kerasModel = None
        
        print >> sys.stderr, "Predicting devel examples"
        bestModelPath = self.model.get(self.tag + "model.hdf5", True)
        self.predict(labels["devel"], features["devel"], labelNames, bestModelPath)
        
#         scores = sklearn.metrics.precision_recall_fscore_support(labels["devel"], predictions, average=None)
#         for i in range(len(mlb.classes_)):
#             print mlb.classes_[i], "prfs =", (scores[0][i], scores[1][i], scores[2][i], scores[3][i])
#         posLabels = [x for x in range(len(mlb.classes_)) if mlb.classes_[x] != "neg"]
#         print mlb.classes_, posLabels
#         micro = sklearn.metrics.precision_recall_fscore_support(labels["devel"], predictions, labels=posLabels,  average="micro")
#         print "micro =", micro
#         print(classification_report(labels["devel"], predictions, target_names=mlb.classes_))
#         print(classification_report(labels["devel"], predictions, target_names=[x for x in mlb.classes_ if x != "neg"], labels=posLabels))
#         #for prediction, gold in predictions, labels["devel"]:
#         #    print prediction
        self.model.save()
        self.examples = None
    
    def vectorizeLabels(self, examples, dataSets, labelNames=None):
        print >> sys.stderr, "Vectorizing labels"
        mlb = MultiLabelBinarizer(labelNames)
        labels = {}
        for dataSet in dataSets:
            labels[dataSet] = [x["labels"] for x in self.examples[dataSet]]
        if labelNames == None:
            mlb.fit_transform(chain.from_iterable([labels[x] for x in dataSets]))
        else:
            mlb.fit(None)
            assert [x for x in mlb.classes_] == labelNames, (mlb.classes_, labelNames)
        for dataSet in dataSets:
            labels[dataSet] = numpy.array(mlb.transform(labels[dataSet]))
        return labels, mlb.classes_
    
    def vectorizeFeatures(self, examples, dataSets):
        featureGroups = sorted(self.examples[dataSets[0]][0]["features"].keys())
        print >> sys.stderr, [((x.get("text"), x.get("POS")) if x != None else None) for x  in self.examples[dataSets[0]][0]["tokens"]]
        print >> sys.stderr, "Vectorizing features:", featureGroups
        features = {x:{} for x in dataSets}
        for featureGroup in featureGroups:
            for dataSet in dataSets:
                if self.exampleLength != None:
                    for example in self.examples[dataSet]:
                        assert len(example["features"][featureGroup]) == self.exampleLength, example
                features[dataSet][featureGroup] = numpy.array([x["features"][featureGroup] for x in self.examples[dataSet]])
            print >> sys.stderr, featureGroup, features[dataSets[0]][featureGroup].shape, features[dataSets[0]][featureGroup][0]
        return features
    
    def predict(self, labels, features, labelNames, kerasModelPath):
        print >> sys.stderr, "Predicting devel examples"
        kerasModel = load_model(kerasModelPath)
        confidences = kerasModel.predict(features, 64, 1)
        
        predictions = numpy.copy(confidences)
        for i in range(len(confidences)):
            for j in range(len(confidences[i])):
                predictions[i][j] = 1 if confidences[i][j] > 0.5 else 0
        print confidences[0], predictions[0], (confidences.shape, predictions.shape)
        
        self.evaluate(labels, predictions, labelNames)
        return predictions, confidences
    
    def evaluate(self, labels, predictions, labelNames):
        print "Evaluating, labels =", labelNames
        scores = sklearn.metrics.precision_recall_fscore_support(labels, predictions, average=None)
        for i in range(len(labelNames)):
            print labelNames[i], "prfs =", (scores[0][i], scores[1][i], scores[2][i], scores[3][i])
        micro = sklearn.metrics.precision_recall_fscore_support(labels, predictions,  average="micro")
        print "micro prfs = ", micro
        if micro[2] != 0.0:
            print(classification_report(labels, predictions, target_names=labelNames))
