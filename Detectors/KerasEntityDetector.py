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
from keras.layers.core import Activation, Reshape, Permute, Dropout
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
from Utils.ProgressCounter import ProgressCounter
from ExampleBuilders.ExampleStats import ExampleStats
from Utils.Libraries.wvlib_light.lwvlib import WV
import numpy
from sklearn.preprocessing.label import MultiLabelBinarizer

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
        print self.examples["devel"][0:10]
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
            
            text = token.get("text").lower()
            if text not in self.embeddingIndex:
                vector = self.wv.w_to_normv(text)
                if vector is not None:
                    self.embeddings.append(self.wv.w_to_normv(text))
                    self.embeddingIndex[text] = len(self.embeddings)
                    if self.embeddings[0] is None: # initialize the out-of-vocabulary vector
                        self.embeddings[0] = numpy.zeros(self.embeddings[1].size)
            vectorIndex = self.embeddingIndex[text] if text in self.embeddingIndex else self.embeddingIndex["[out]"]
            
            examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(exampleIndex), "labels":labels, "features":{"index":vectorIndex}}) #, "extra":{"eIds":entityIds}}
            #outfile.write("\n")
            #if exampleIndex > 0:
            #    outfile.write(",")
            #outfile.write(json.dumps(example))
            exampleIndex += 1
            self.exampleStats.endExample()
        #outfile.write("\n]")
        #return examples
        return exampleIndex
    
    def getEntityTypes(self, entities):
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
        if len(types) == 0:
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
        self.wv = None
        if "wordvector" in self.styles and isinstance(self.styles["wordvector"], basestring):
            wordVectorPath = self.styles["wordvector"]
        else:
            wordVectorPath = Settings.W2VFILE
        print >> sys.stderr, "Loading word vectors from", wordVectorPath
        self.wv = WV.load(wordVectorPath, 1000, 10000)
        self.embeddings = [None]
        self.embeddingIndex = {"[out]":0}
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
    
    def makeEmbeddingMatrix(self, vectors):
        dimWordVector = len(vectors[0])
        numWordVectors = len(vectors)
        embedding_matrix = np.zeros((numWordVectors, dimWordVector))
        for i in range(len(vectors)):
            embedding_matrix[i] = vectors[i]
        return embedding_matrix
    
    def defineModel(self):
        """
        Defines the Keras model and compiles it.
        """
        print >> sys.stderr, "Making Embedding Matrix"
        embedding_matrix = self.makeEmbeddingMatrix(self.embeddings)
        
        labelSet = set()
        for dataSet in ("train", "devel"):
            for example in self.examples[dataSet]:
                for label in example["labels"]:
                    labelSet.add(label)
        
        x = inputLayer = Input(shape=(1,))
        Embedding(len(self.embeddings), 
                  self.embeddings[0].size, 
                  weights=[embedding_matrix], 
                  input_length=1,
                  trainable=False)(x)
        x = Dense(400, activation='relu')(x)
        x = Dense(len(labelSet), activation='sigmoid')(x)
        
        self.kerasModel = Model(inputLayer, x)
        
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
        
        print >> sys.stderr, "Vectorizing features"
        features = {}
        for dataSet in ("train", "devel"):
            features[dataSet] = numpy.array([[x["features"]["index"]] for x in self.examples[dataSet]])
        
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
        #for prediction, gold in predictions, labels["devel"]:
        #    print prediction
        self.model.save()
        
        # For now the training ends here, later the predicted matrices should be converted back to XML events
        sys.exit()
    
    ###########################################################################
    # Vectorization
    ###########################################################################
    
    def devectorizePredictions(self, predictions):
        """
        Converts a dense Numpy array of [examples][width][height][features] into
        the corresponding Python list matrices where features are stored in a key-value
        dictionary.
        """
        targetIds = IdSet(filename=self.model.get(self.tag+"ids.classes"), locked=True)
        dimMatrix = int(self.model.getStr("dimMatrix"))
        dimLabels = int(self.model.getStr("dimLabels"))
        predictions = reshape(predictions, (predictions.shape[0], dimMatrix, dimMatrix, dimLabels))
        rangeMatrix = range(dimMatrix)
        labels = np.argmax(predictions, axis=-1)
        values = np.max(predictions, axis=-1)
        minValue = np.min(values)
        maxValue = np.max(values)
        valRange = maxValue - minValue
        print "MINMAX", minValue, maxValue
        devectorized = []
        for exampleIndex in range(predictions.shape[0]):
            #print predictions[exampleIndex]
            devectorized.append([])
            for i in rangeMatrix:
                devectorized[-1].append([])
                for j in rangeMatrix:
                    features = {}
                    devectorized[-1][-1].append(features)
                    maxFeature = labels[exampleIndex][i][j]
                    predValue = predictions[exampleIndex][i][j][maxFeature]
                    features[targetIds.getName(maxFeature)] = float(predValue)
                    features["color"] = self.getColor((predValue - minValue) / valRange)
        return devectorized
    
    def vectorizeMatrices(self, model, useMask=False):
        """
        Converts the Python input matrices of the form [examples][width][height]{features} into
        corresponding dense Numpy arrays.
        """
        counts = defaultdict(int)
        self.arrays = {}
        featureIds = IdSet(filename=model.get(self.tag+"ids.features"), locked=True)
        labelIds = IdSet(filename=model.get(self.tag+"ids.classes"), locked=True)
        #negLabelIds = set([labelIds.getId(x) for x in ["Eneg", "Ineg", "[out]"]])
        negLabels = str(["Eneg", "Ineg", "[out]"])
        dimFeatures = int(model.getStr("dimFeatures"))
        dimLabels = int(model.getStr("dimLabels"))
        dimMatrix = int(model.getStr("dimMatrix"))
        rangeMatrix = range(dimMatrix)
        dataSets = [(x, self.matrices[x]) for x in sorted(self.matrices.keys())]
        self.matrices = None
        while dataSets:
            dataSetName, dataSetValue = dataSets.pop()
            print >> sys.stderr, "Vectorizing dataset", dataSetName
            featureMatrices = dataSetValue["features"]
            labelMatrices = dataSetValue["labels"]
            embeddingMatrices = None
            assert len(featureMatrices) == len(labelMatrices)
            numExamples = len(featureMatrices)
            self.arrays[dataSetName] = {"features":np.zeros((numExamples, dimMatrix, dimMatrix, dimFeatures), dtype=np.float32), 
                                        "labels":np.zeros((numExamples, dimMatrix, dimMatrix, dimLabels), dtype=np.float32)}
            if self.styles.get("wv") != None:
                embeddingMatrices = dataSetValue["embeddings"]
                self.arrays[dataSetName]["embeddings"] = np.zeros((numExamples, dimMatrix, dimMatrix, 2), dtype=np.int32)
            if useMask:
                self.arrays[dataSetName]["mask"] = np.ones((numExamples, dimMatrix, dimMatrix), dtype=np.float32)
            for exampleIndex in range(numExamples):
                numTokens = len(dataSetValue["tokens"][exampleIndex])
                featureArray = self.arrays[dataSetName]["features"][exampleIndex] #sourceArray = np.zeros((dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
                labelArray = self.arrays[dataSetName]["labels"][exampleIndex] #targetArray = np.zeros((dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
                if useMask:
                    maskArray = self.arrays[dataSetName]["mask"][exampleIndex]
                featureMatrix = featureMatrices.pop(0) #[exampleIndex]
                labelMatrix = labelMatrices.pop(0) #[exampleIndex]
                transfers = [(featureMatrix, featureArray, featureIds), (labelMatrix, labelArray, labelIds)]
                for matrix, array, ids in transfers:
                    for i in rangeMatrix:
                        for j in rangeMatrix:
                            features = matrix[i][j]
                            #print features
                            for featureName in features:
                                array[i][j][ids.getId(featureName)] = features[featureName]
                if useMask:
                    for i in rangeMatrix:
                        for j in rangeMatrix:
                            if i > numTokens or j > numTokens:
                                maskArray[i][j] = 0.0
                                counts["masked-out"] += 1
                            elif len(set(labelMatrix[i][j].keys()).union(negLabels)) > 0:
                                maskArray[i][j] = 0.001
                                counts["masked-neg"] += 1
                if embeddingMatrices != None:
                    embeddingMatrix = embeddingMatrices.pop(0)
                    embeddingArray = self.arrays[dataSetName]["embeddings"][exampleIndex]
                    for i in rangeMatrix:
                        for j in rangeMatrix:
                            embeddingArray[i][j][0] = embeddingMatrix[i][j]["0"]
                            embeddingArray[i][j][1] = embeddingMatrix[i][j]["1"]
            if self.styles.get("autoencode") != None:
                print >> sys.stderr, "Autoencoding dataset", dataSetName
                self.arrays[dataSetName]["features"] = self.arrays["labels"]
            dimLast = {"features":dimFeatures, "labels":dimLabels, "embeddings":2, "mask":dimLabels}
            for arrayName in self.arrays[dataSetName]:
                if arrayName != "mask":
                    targetShape = (numExamples, dimMatrix * dimMatrix, dimLast[arrayName])
                else:
                    targetShape = (numExamples, dimMatrix * dimMatrix)
                self.arrays[dataSetName][arrayName] = reshape(self.arrays[dataSetName][arrayName], targetShape)
            print >> sys.stderr, dataSetName, self.getArrayShapes(self.arrays[dataSetName]), dict(counts)