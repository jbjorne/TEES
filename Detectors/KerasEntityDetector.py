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
from itertools import product
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

class Embeddings():
    def __init__(self, dimVector=32, wordVectorPath=None, wvMem=100000, wvMap=10000000, keys=None):
        self.wv = None
        self.embeddings = []
        self.embeddingIndex = {}
        if wordVectorPath != None:
            print >> sys.stderr, "Loading word vectors", (wvMem, wvMap), "from", wordVectorPath
            self.wv = WV.load(wordVectorPath, wvMem, wvMap)
            self.dimVector = None
        else:
            self.dimVector = dimVector
        self.initialKeys = [] if keys == None else keys
        self.initialKeysInitialized = False
        for key in self.initialKeys:
            assert key not in self.embeddingIndex
            self.embeddingIndex[key] = len(self.embeddings)
            self.embeddings.append(numpy.zeros(self.dimVector) if self.wv == None else None)
    
    def releaseWV(self):
        self.wv = None
    
    def getIndex(self, key, default=None):
        if key not in self.embeddingIndex:
            if self.wv != None:
                vector = self.wv.w_to_normv(key)
                if vector is not None:
                    self.embeddingIndex[key] = len(self.embeddings)
                    self.embeddings.append(vector)
                    if not self.initialKeysInitialized:
                        for initialKey in self.initialKeys:
                            self.embeddings[self.embeddingIndex[initialKey]] = numpy.zeros(vector.size)
                        self.initialKeysInitialized = True
            else:
                self.embeddingIndex[key] = len(self.embeddings)
                self.embeddings.append(numpy.random.uniform(-1.0, 1.0, self.dimVector))
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
        self.tag = "keras-"
        self.exampleBuilder = None #KerasExampleBuilder
        self.matrices = None
        self.arrays = None
        #self.EXAMPLE_LENGTH = 1 #None #130
        self.exampleLength = -1
    
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
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        exampleFiles = {"devel":self.workDir+self.tag+"opt-examples.json.gz", "train":self.workDir+self.tag+"train-examples.json.gz"}
        if self.checkStep("EXAMPLES"): # Generate the adjacency matrices
            self.buildExamples(self.model, ["devel", "train"], [optData, trainData], [exampleFiles["devel"], exampleFiles["train"]], saveIdsToModel=True)
        print self.examples["devel"][0:2]
        if self.checkStep("MODEL"): # Define and train the Keras model
            self.defineModel()
            self.fitModel()
        if workDir != None:
            self.setWorkDir("")
        self.arrays = None
        self.exitState()
    
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
        
    def processCorpus(self, input, examples, gold=None):
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
        inputIterator = getCorpusIterator(input, None, self.parse, self.tokenization, removeIntersentenceInteractions=removeIntersentenceInteractions)            
        goldIterator = []
        if gold != None:
            goldIterator = getCorpusIterator(gold, None, self.parse, self.tokenization, removeIntersentenceInteractions=removeIntersentenceInteractions)
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
        self.exampleLength = 21 #5 #3 #9 #19 #21 #9 #5 #exampleLength = self.EXAMPLE_LENGTH if self.EXAMPLE_LENGTH != None else numTokens
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
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]

            # CLASS
            labels, entityIds = self.getEntityTypes(sentenceGraph.tokenIsEntityHead[token])
            self.exampleStats.beginExample(",".join(labels))
            
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token] and not self.styles.get("names") and not self.styles.get("all_tokens"):
                self.exampleStats.filter("name")
                self.exampleStats.endExample()
                continue
            
            tokens = []
            features = {"words":[], "positions":[], "named_entities":[], "POS":[]}
            featureGroups = sorted(features.keys())
            side = (self.exampleLength - 1) / 2
            windowIndex = 0
            for j in range(i - side, i + side + 1):
                #features["binary"].append([])
                #features["binary"][-1].append(1 if i == j else 0)
                if j >= 0 and j < numTokens:
                    token2 = sentenceGraph.tokens[j]
                    tokens.append(token2)
                    features["words"].append(indices[j])
                    features["positions"].append(self.embeddings["positions"].getIndex(windowIndex))
                    features["named_entities"].append(self.embeddings["named_entities"].getIndex(1 if (sentenceGraph.tokenIsEntityHead[token2] and sentenceGraph.tokenIsName[token2]) else 0))
                    features["POS"].append(self.embeddings["POS"].getIndex(token2.get("POS")))
                    #features["binary"][-1].append(1 if sentenceGraph.tokenIsName[sentenceGraph.tokens[j]] else 0)
                else:
                    tokens.append(None)
                    for featureGroup in featureGroups:
                        features[featureGroup].append(self.embeddings[featureGroup].getIndex("[padding]"))
                    #features["binary"][-1].append(0)
                windowIndex += 1
            
            examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(exampleIndex), "labels":labels, "features":features, "tokens":tokens}) #, "extra":{"eIds":entityIds}}
            #outfile.write("\n")
            #if exampleIndex > 0:
            #    outfile.write(",")
            #outfile.write(json.dumps(example))
            exampleIndex += 1
            self.exampleStats.endExample()
        #outfile.write("\n]")
        #return examples
        return exampleIndex
    
    def getEntityTypes(self, entities, useNeg=True):
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
        self.embeddings = {}
        wordVectorPath = self.styles.get("wordvector", Settings.W2VFILE)
        wv_mem = int(self.styles.get("wv_mem", 100000))
        wv_map = int(self.styles.get("wv_map", 10000000))
        self.embeddings["words"] = Embeddings(None, wordVectorPath, wv_mem, wv_map, ["[out]", "[padding]"])
        dimEmbeddings = 8 #32
        self.embeddings["positions"] = Embeddings(dimEmbeddings, keys=["[padding]"])
        self.embeddings["named_entities"] = Embeddings(dimEmbeddings, keys=["[padding]"])
        self.embeddings["POS"] = Embeddings(dimEmbeddings, keys=["[padding]"])
        # Make example for all input files
        self.examples = {x:[] for x in setNames}
        for setName, data, gold in itertools.izip_longest(setNames, datas, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName #, "to file", output 
            self.processCorpus(data, self.examples[setName], gold)          
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if modelChanged:
            model.save()
        self.embeddings["words"].releaseWV()
    
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
        merged_features = Dropout(0.1)(merged_features)
        
#         # Main network
#         x = Conv1D(64, 11, activation='relu')(x)
#         x = Conv1D(64, 4, activation='relu')(x)
#         #x = MaxPooling1D(3)(x)
#         x = Conv1D(64, 4, activation='relu')(x)
#         #x = MaxPooling1D(3)(x)
#         #x = Conv1D(256, 3, activation='relu')(x)
#         #x = MaxPooling1D(3)(x)
        
        convOutputs = []
        kernelSizes = [1, 3, 5, 7]
        numFilters = 32 #64
        for kernel in kernelSizes:
            subnet = Conv1D(numFilters, kernel, activation='relu', name='conv_' + str(kernel))(merged_features)
            subnet = MaxPooling1D(pool_length=self.exampleLength - kernel + 1, name='maxpool_' + str(kernel))(subnet)
            subnet = Flatten(name='flat_' + str(kernel))(subnet)
            convOutputs.append(subnet)       
        layer = merge(convOutputs, mode='concat')
        layer = Dropout(0.1)(layer)
        
        # Classification layers
        #layer = Flatten()(merged_features)
        layer = Dense(400, activation='relu')(layer)
        layer = Dense(len(labelSet), activation='sigmoid')(layer)
        
        self.kerasModel = Model([self.embeddings[x].inputLayer for x in embNames], layer)
        
        learningRate = float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"]
        self.kerasModel.compile(optimizer=optimizer, loss="binary_crossentropy", metrics=metrics)
        
        self.kerasModel.summary()
   
    def fitModel(self):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """
        
        print >> sys.stderr, "Vectorizing labels"
        mlb = MultiLabelBinarizer()
        labels = {}
        for dataSet in ("train", "devel"):
            labels[dataSet] = [x["labels"] for x in self.examples[dataSet]]
        mlb.fit_transform(labels["train"] + labels["devel"])
        for dataSet in ("train", "devel"):
            labels[dataSet] = numpy.array(mlb.transform(labels[dataSet]))
        
        print >> sys.stderr, "Labels:", mlb.classes_
        labelWeights = {}
        for i in range(len(mlb.classes_)):
            labelWeights[i] = 1.0 if mlb.classes_[i] != "neg" else 0.001
        print >> sys.stderr, "Label weights:", labelWeights
        #print >> sys.stderr, compute_sample_weight("balanced", [{i:x[i] for i in x} for x in labels["train"]])
        #labelWeights = {x[0]:x[1] for x in enumerate(compute_class_weight("balanced", np.unique(labels["train"]), labels["train"]))}
        #print >> sys.stderr, "Label weights:", labelWeights
        
        featureGroups = sorted(self.examples["train"][0]["features"].keys())
        print >> sys.stderr, [((x.get("text"), x.get("POS")) if x != None else None) for x  in self.examples["train"][0]["tokens"]]
        print >> sys.stderr, "Vectorizing features:", featureGroups
        features = {"train":{}, "devel":{}}
        for featureGroup in featureGroups:
            for dataSet in ("train", "devel"):
                if self.exampleLength != None:
                    for example in self.examples[dataSet]:
                        assert len(example["features"][featureGroup]) == self.exampleLength, example
                features[dataSet][featureGroup] = numpy.array([x["features"][featureGroup] for x in self.examples[dataSet]])
            print >> sys.stderr, featureGroup, features["train"][featureGroup].shape, features["train"][featureGroup][0]
        
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
        
        bestModelPath = self.model.get(self.tag + "model.hdf5", True) 
        print >> sys.stderr, "Predicting devel examples"
        self.kerasModel = load_model(bestModelPath)
        predictions = self.kerasModel.predict(features["devel"], 64, 1)
        print >> sys.stderr, mlb.classes_
        print labels["devel"][0]
        for i in range(len(predictions)):
            for j in range(len(predictions[i])):
                predictions[i][j] = 1 if predictions[i][j] > 0.5 else 0
        print predictions[0]
        scores = sklearn.metrics.precision_recall_fscore_support(labels["devel"], predictions, average=None)
        for i in range(len(mlb.classes_)):
            print mlb.classes_[i], "prfs =", (scores[0][i], scores[1][i], scores[2][i], scores[3][i])
        posLabels = [x for x in range(len(mlb.classes_)) if mlb.classes_[x] != "neg"]
        print mlb.classes_, posLabels
        micro = sklearn.metrics.precision_recall_fscore_support(labels["devel"], predictions, labels=posLabels,  average="micro")
        print "micro =", micro
        print(classification_report(labels["devel"], predictions, target_names=mlb.classes_))
        print(classification_report(labels["devel"], predictions, target_names=[x for x in mlb.classes_ if x != "neg"], labels=posLabels))
        #for prediction, gold in predictions, labels["devel"]:
        #    print prediction
        self.model.save()
        
        # For now the training ends here, later the predicted matrices should be converted back to XML events
        sys.exit()
    
#     def evaluate(self, correct, predictions, labels):
#         scores = sklearn.metrics.precision_recall_fscore_support(labels["devel"], predictions, average=None)
#         for i in range(len(labels)):
#             print labels[i], "prfs =", (scores[0][i], scores[1][i], scores[2][i], scores[3][i])