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
from Utils.ProgressCounter import ProgressCounter

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
        sys.exit()
        if self.checkStep("MODEL"): # Define and train the Keras model
            self.defineModel()
            self.fitModel(exampleFiles)
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
        
    def processCorpus(self, input, output, gold=None):
        # Create intermediate paths if needed
        if os.path.dirname(output) != "" and not os.path.exists(os.path.dirname(output)):
            os.makedirs(os.path.dirname(output))
        # Open output file
        if output.endswith(".gz"):
            outfile = gzip.open(output, "wt")
        else:
            outfile = open(output, "wt")
        
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
            self.processDocument(inputSentences, goldSentences, outfile)
        outfile.close()
        self.progress.endUpdate()
        
        # Show statistics
        print >> sys.stderr, "Examples built:", self.exampleCount
        print >> sys.stderr, "Features:", len(self.featureSet.getNames())
        print >> sys.stderr, "Classes:", len(self.classSet.getNames())
        print >> sys.stderr, "Style:", Utils.Parameters.toString(self.getParameters(self.styles))
        if self.exampleStats.getExampleCount() > 0:
            self.exampleStats.printStats()
    
    def processDocument(self, sentences, goldSentences, outfile, structureAnalyzer=None):
        #calculatePredictedRange(self, sentences)            
        for i in range(len(sentences)):
            sentence = sentences[i]
            goldSentence = None
            if goldSentences != None:
                goldSentence = goldSentences[i]
            self.progress.update(1, "Building examples ("+sentence.sentence.get("id")+"): ")
            self.processSentence(sentence, outfile, goldSentence, structureAnalyzer=structureAnalyzer)
    
    def processSentence(self, sentence, outfile, goldSentence=None):
        # Process the sentence
        if sentence.sentenceGraph != None:
            self.exampleCount += self.buildExamplesFromGraph(sentence.sentenceGraph, outfile, goldSentence.sentenceGraph if goldSentence != None else None, structureAnalyzer=structureAnalyzer)

    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph=None):
        """
        Build one example for each token of the sentence
        """       
        exampleIndex = 0
        
        # determine (manually or automatically) the setting for whether sentences with no given entities should be skipped
        buildForNameless = False
        if self.structureAnalyzer and not self.structureAnalyzer.hasGroupClass("GIVEN", "ENTITY"): # no given entities points to no separate NER program being used
            buildForNameless = True
        if self.styles["build_for_nameless"]: # manually force the setting
            buildForNameless = True
        if self.styles["skip_for_nameless"]: # manually force the setting
            buildForNameless = False
        
        # determine whether sentences with no given entities should be skipped
        namedEntityHeadTokens = []
        if not self.styles["names"]:
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
            
            if self.styles["pos_pairs"]:
                namedEntityHeadTokens = self.getNamedEntityHeadTokens(sentenceGraph)
        else:
            for key in sentenceGraph.tokenIsName.keys():
                sentenceGraph.tokenIsName[key] = False
        
        outfile.write("[")
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]

            # CLASS
            if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
                categoryName, entityIds = self.getMergedEntityType(sentenceGraph.tokenIsEntityHead[token])
            else:
                categoryName, entityIds = "neg", None
            self.exampleStats.beginExample(categoryName)
            
            example = {"id":sentenceGraph.getSentenceId()+".x"+str(exampleIndex), "labels":categoryName.split("---"), "features":{}, "extra":{"eIds":entityIds}}
            outfile.write("\n")
            if exampleIndex > 0:
                outfile.write(",")
            outfile.write(json.dumps(example))
            exampleIndex += 1
            self.exampleStats.endExample()
        outfile.write("\n]")
        #return examples
        return exampleIndex
    
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
        # Make example for all input files
        for setName, data, output, gold in itertools.izip_longest(setNames, datas, outputs, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName, "to file", output  
            self.processCorpus(data, output, gold)          
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if modelChanged:
            model.save()
    
    def makeEmbeddingMatrix(self):
        vectors = self.wordvectors["vectors"]
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
        dimFeatures = int(self.model.getStr("dimFeatures")) # Number of channels in the source matrix
        dimLabels = int(self.model.getStr("dimLabels")) # Number of channels in the target matrix
        if "autoencode" in self.styles:
            dimFeatures = dimLabels
        dimMatrix = int(self.model.getStr("dimMatrix")) # The width/height of both the source and target matrix
        
        print >> sys.stderr, "Defining model", (dimMatrix, dimFeatures, dimFeatures)
        metrics = ["accuracy"]
        
        inputs = []
        if self.styles.get("wv") != None:
            # Features
            x1 = input_features = Input(shape=(dimMatrix * dimMatrix, dimFeatures), name='features')
            inputs.append(input_features)
            x1 = Reshape((dimMatrix, dimMatrix, dimFeatures))(x1)
            x1 = Conv2D(128, (1, 1), activation='relu', padding='same', name='X1_C2D_reduce')(x1)
            x1 = Conv2D(32, (1, 9), activation='relu', padding='same', name='X1_C2D_C1')(x1)
            x1 = Conv2D(32, (1, 5), activation='relu', padding='same', name='X1_C2D_C2')(x1)
            x1 = Conv2D(32, (1, 3), activation='relu', padding='same', name='X1_C2D_C3')(x1)
            
            # Embeddings
            dimEmbeddings = 2
            self.wordvectors = self.loadEmbeddings(self.styles.get("wv"))
            dimWordVector = len(self.wordvectors["vectors"][0])
            numWordVectors = len(self.wordvectors["vectors"])
            embedding_matrix = self.makeEmbeddingMatrix()
            x2 = input_embeddings = Input(shape=(dimMatrix * dimMatrix, dimEmbeddings), name='embeddings')
            inputs.append(input_embeddings)
            x2 = Reshape((dimMatrix, dimMatrix, dimEmbeddings))(x2)
            embedding_input_length = dimMatrix * dimMatrix * dimEmbeddings
            x2 = Reshape((dimMatrix * dimMatrix * dimEmbeddings, ))(x2)
            x2 = Embedding(numWordVectors, dimWordVector, weights=[embedding_matrix], 
                          input_length=embedding_input_length, trainable=True)(x2)
            x2 = Reshape((dimMatrix * dimMatrix, 2 * dimWordVector))(x2)
            x2 = Reshape((dimMatrix, dimMatrix, 2 * dimWordVector))(x2)
            #x = Reshape((dimMatrix, dimMatrix, dimEmbeddings))(x)
            x2 = Conv2D(dimWordVector, (1, 9), activation='relu', padding='same', name='X2_C2D_C1')(x2)
            x2 = Conv2D(dimWordVector, (1, 5), activation='relu', padding='same', name='X2_C2D_C2')(x2)
            x2 = Conv2D(dimWordVector, (1, 3), activation='relu', padding='same', name='X2_C2D_C3')(x2)
            
            # Merge
            x = merge([x1, x2], mode='concat')
#             x = Conv2D(128, (1, 1), activation='relu', padding='same')(x)
#             x = Conv2D(32, (1, 9), activation='relu', padding='same')(x)
#             x = Conv2D(32, (1, 5), activation='relu', padding='same')(x)
#             x = Conv2D(32, (1, 3), activation='relu', padding='same')(x)
            #x = Concatenate([input_features, x])
        else:
            x = Input(shape=(dimMatrix, dimMatrix, dimFeatures), name='features')
            inputs.append(x)
            ##x = Conv2D(32, (3, 3), padding='same')(x)
            #x = Conv2D(16, (3, 3), padding='same')(x)
            #x = Conv2D(16, (1, 21), padding='same')(x)
            x = Conv2D(128, (1, 1), activation='relu', padding='same')(x)
            x = Conv2D(32, (1, 9), activation='relu', padding='same')(x)
            x = Conv2D(32, (1, 5), activation='relu', padding='same')(x)
            x = Conv2D(32, (1, 3), activation='relu', padding='same')(x)
        
        x = Conv2D(256, (1, 1), activation='relu', padding='same')(x)
        x = Conv2D(dimLabels, (1, 1), activation='sigmoid', padding='same')(x)
        x = Reshape((dimMatrix * dimMatrix, dimLabels), name='labels')(x)
        self.kerasModel = Model(inputs, x)
        
        layersPath = self.workDir + self.tag + "layers.json"
        print >> sys.stderr, "Saving layers to", layersPath
        self.serializeLayers(self.kerasModel, layersPath)
        
        learningRate = float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        self.kerasModel.compile(optimizer=optimizer, loss="categorical_crossentropy", metrics=metrics, sample_weight_mode="temporal") #, metrics=['accuracy'])
        
        self.kerasModel.summary()
   
    def fitModel(self, exampleFiles):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """
        if self.matrices == None: # If program is run from the TRAIN.MODEL step matrices are loaded from files
            self.matrices = {}
            for setName in exampleFiles:
                print >> sys.stderr, "Loading dataset", setName, "from", exampleFiles[setName]
                self.matrices[setName] = self.loadJSON(exampleFiles[setName])
        if self.arrays == None: # The Python dictionary matrices are converted into dense Numpy arrays
            self.vectorizeMatrices(self.model, useMask=True)
         
#         targetIds = IdSet(filename=self.model.get(self.tag+"ids.classes"), locked=True)
#         class_weight = {}
#         for className in targetIds.Ids:
#             class_weight[targetIds.getId(className)] = 1.0 if className != "neg" else 0.00001
        
        print >> sys.stderr, "Fitting model"
        patience = int(self.styles.get("patience", 10))
        print >> sys.stderr, "Early stopping patience:", patience
        es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
        bestModelPath = self.model.get(self.tag + "model.hdf5", True) #self.workDir + self.tag + 'model.hdf5'
        cp_cb = ModelCheckpoint(filepath=bestModelPath, save_best_only=True, verbose=1)
        #sourceData = "source"
        #import pdb;pdb.set_trace()
        #if "autoencode" in self.styles:
        #    sourceData = "target"
        #print >> sys.stderr, sourceData, "->", "target", ("(autoencode)" if "autoencode" in self.styles else "")
        print >> sys.stderr, "Autoencoding:", self.styles.get("autoencode") != None
        print >> sys.stderr, "Arrays:", {x:{y:self.arrays[x][y].shape for y in self.arrays[x]} for x in self.arrays}
        self.kerasModel.fit(self.arrays["train"], self.arrays["train"], #[sourceData], self.arrays["train"]["target"],
            epochs=100 if not "epochs" in self.styles else int(self.styles["epochs"]),
            batch_size=64,
            shuffle=True,
            validation_data=(self.arrays["devel"], self.arrays["devel"], self.arrays["devel"]["mask"]), #[sourceData], self.arrays["devel"]["target"]), #, self.arrays["devel"]["mask"]),
            sample_weight=self.arrays["train"]["mask"],
            #class_weight=class_weight,
            callbacks=[es_cb, cp_cb])
        
        bestModelPath = self.model.get(self.tag + "model.hdf5", True) 
        print >> sys.stderr, "Predicting devel examples"
        self.kerasModel = load_model(bestModelPath)
        predictions = self.kerasModel.predict(self.arrays["devel"], 128, 1)
        self.model.save()
        
        # The predicted matrices are saved as an HTML heat map
        predMatrices = self.loadJSON(exampleFiles["devel"])
        predMatrices["predicted"] = self.devectorizePredictions(predictions)
        if "save_predictions" in self.styles:
            print >> sys.stderr, "Saving predictions to", self.workDir + self.tag + "devel-predictions.json.gz"
            self.saveJSON(self.workDir + self.tag + "devel-predictions.json.gz", predMatrices)
        if "html" in self.styles:
            self.matricesToHTML(self.model, predMatrices, self.workDir + self.tag + "devel-predictions.html", int(self.styles["html"]), names = ["features", "labels", "predicted"])
        
        # For now the training ends here, later the predicted matrices should be converted back to XML events
        sys.exit()
    
    ###########################################################################
    # HTML Table visualization
    ###########################################################################
    
    def matrixToTable(self, matrix, tokens, parent, name):
        """
        Converts a single Python dictionary adjacency matrix into an HTML table structure.
        """
        matrixRange = range(len(matrix) + 1)
        table = ET.SubElement(parent, 'table', {"border":"1"})
        outCount = 0
        for i in matrixRange:
            tr = ET.SubElement(table, 'tr')
            for j in matrixRange:
                td = ET.SubElement(tr, 'td')
                if i == 0 or j == 0:
                    if i != 0 and i > 0 and i <= len(tokens): td.text = tokens[i - 1]
                    elif j != 0 and j > 0 and j <= len(tokens): td.text = tokens[j - 1]
                else:
                    if i == j: # This element is on the diagonal
                        td.set("style", "font-weight:bold;")
                    features = matrix[i - 1][j - 1]
                    if "color" in features: # The 'color' is not a real feature, but rather defines this table element's background color
                        td.set("bgcolor", features["color"])
                    if name == "embeddings":
                        featureNames = [x + "=" + str(features[x]) for x in features]
                    else:
                        featureNames = [x for x in features if x != "color"]
                        td.set("weights", ",".join([x + "=" + str(features[x]) for x in featureNames]))
                    featureNames.sort()
                    td.text = ",".join([x for x in featureNames])
                    if td.text == "[out]":
                        outCount += 1
                        td.text = ""
        if outCount > 0:
            ET.SubElement(parent, "p").text = "[out]: " + str(outCount)
    
    def matricesToHTML(self, model, data, filePath, cutoff=None, names=None):
        """
        Saves the source (features), target (labels) and predicted adjacency matrices
        for a list of sentences as HTML tables.
        """
        print >> sys.stderr, "Writing adjacency matrix visualization to", os.path.abspath(filePath)
        root = ET.Element('html')
        if names == None:
            names = ["embeddings", "features", "labels", "predicted"]
        print >> sys.stderr, {x:(len(data.get(x)) if data.get(x) != None else None) for x in names}
        tokenLists = data["tokens"]
        for i in range(len(tokenLists)):
            if cutoff is not None and i >= cutoff:
                break
            ET.SubElement(root, "h3").text = str(i) + ": " + " ".join(tokenLists[i])
            for name in names:
                if data.get(name) != None:
                    ET.SubElement(root, "p").text = name
                    assert i < len(data[name]) and i < len(tokenLists), (name, len(data[name]), len(tokenLists))
                    self.matrixToTable(data[name][i], tokenLists[i], root, name)
        ETUtils.write(root, filePath)
        
    def clamp(self, value, lower, upper):
        return max(lower, min(value, upper))
    
    def getColor(self, value):
        r = self.clamp(int((1.0 - value) * 255.0), 0, 255)
        g = self.clamp(int(value * 255.0), 0, 255)
        b = 0
        return '#%02x%02x%02x' % (r, g, b)
    
    def getArrayShapes(self, arrayDict):
        return {x:(arrayDict.get(x).shape if arrayDict.get(x) is not None else None) for x in arrayDict}
    
    ###########################################################################
    # Serialization
    ###########################################################################
    
    def saveJSON(self, filePath, data):
        with gzip.open(filePath, "wt") as f:
            json.dump(data, f, indent=2)
    
    def loadJSON(self, filePath):
        with gzip.open(filePath, "rt") as f:
            return json.load(f)
    
    def serializeLayers(self, kerasModel, filePath, verbose=False):
        layers = []
        for layer in kerasModel.layers:
            layers.append({'class_name': layer.__class__.__name__, 'config': layer.get_config()})
        if verbose:
            print >> sys.stderr, "Layer configuration:"
            print >> sys.stderr, "_________________________________________________________________"
            for layer in layers:
                print >> sys.stderr, layer
            print >> sys.stderr, "_________________________________________________________________"
        with open(filePath, "wt") as f:
            json.dump(layers, f, indent=2)
    
    def loadEmbeddings(self, wvPath):
        vectorPath = self.styles.get("wv") + "-vectors.json.gz"
        if not os.path.exists(vectorPath):
            vectorPath = os.path.join(Settings.DATAPATH, "wv", vectorPath)
        print >> sys.stderr, "Loading word vector indices from", vectorPath
        assert os.path.exists(vectorPath)
        with gzip.open(vectorPath, "rt") as f:
            return json.load(f)
    
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