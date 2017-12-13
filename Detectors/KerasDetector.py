import sys, os
from Detector import Detector
import itertools
from ExampleBuilders.KerasExampleBuilder import KerasExampleBuilder
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

# def categorical_crossentropy(output, target, from_logits=False):
#     from keras.backend.common import _EPSILON
#     from theano import tensor as T
#     from theano.tensor import basic as tensor
#     if from_logits:
#         output = T.nnet.softmax(output)
#     else:
#         # scale preds so that the class probas of each sample sum to 1
#         output /= output.sum(axis=-1, keepdims=True)
#     # avoid numerical instability with _EPSILON clipping
#     output = T.clip(output, _EPSILON, 1.0 - _EPSILON)
#     return T.nnet.categorical_crossentropy(output, target)

# def w_categorical_crossentropy(y_true, y_pred, weights):
#     nb_cl = len(weights)
#     final_mask = K.zeros_like(y_pred[:, 0])
#     y_pred_max = K.max(y_pred, axis=1)
#     y_pred_max = K.reshape(y_pred_max, (K.shape(y_pred)[0], 1))
#     y_pred_max_mat = K.equal(y_pred, y_pred_max)
#     for c_p, c_t in product(range(nb_cl), range(nb_cl)):
#         final_mask += (weights[c_t, c_p] * y_pred_max_mat[:, c_p] * y_true[:, c_t])
#     return K.categorical_crossentropy(y_pred, y_true) * final_mask

class KerasDetector(Detector):
    """
    The KerasDetector replaces the default SVM-based learning with a pipeline where
    sentences from the XML corpora are converted into adjacency matrix examples which
    are used to train the Keras model defined in the KerasDetector.
    """

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "keras-"
        self.exampleBuilder = KerasExampleBuilder
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
        if self.checkStep("MODEL"): # Define and train the Keras model
            self.defineModel()
            self.fitModel(exampleFiles)
        if workDir != None:
            self.setWorkDir("")
        self.arrays = None
        self.exitState()
    
#     def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, goldData=None, parse=None, recallAdjust=None, compressExamples=True, exampleStyle=None, useExistingExamples=False):
#         model = self.openModel(model, "r")
#         if parse == None:
#             parse = self.getStr(self.tag+"parse", model)
#         if useExistingExamples:
#             assert exampleFileName != None
#             assert os.path.exists(exampleFileName)
#         if exampleFileName == None:
#             exampleFileName = tag+self.tag+"examples"
#             if compressExamples:
#                 exampleFileName += ".gz"
#         if not useExistingExamples:
#             self.buildExamples(model, [data], [exampleFileName], [goldData], parse=parse, exampleStyle=exampleStyle)
#         if classifierModel == None:
#             classifierModel = model.get(self.tag+"classifier-model", defaultIfNotExist=None)
#         #else:
#         #    assert os.path.exists(classifierModel), classifierModel
#         classifier = self.getClassifier(model.getStr(self.tag+"classifier-parameter", defaultIfNotExist=None))()
#         classifier.classify(exampleFileName, tag+self.tag+"classifications", classifierModel, finishBeforeReturn=True)
#         threshold = model.getStr(self.tag+"threshold", defaultIfNotExist=None, asType=float)
#         predictions = ExampleUtils.loadPredictions(tag+self.tag+"classifications", recallAdjust, threshold=threshold)
#         evaluator = self.evaluator.evaluate(exampleFileName, predictions, model.get(self.tag+"ids.classes"))
#         #outputFileName = tag+"-"+self.tag+"pred.xml.gz"
#         #exampleStyle = self.exampleBuilder.getParameters(model.getStr(self.tag+"example-style"))
#         if exampleStyle == None:
#             exampleStyle = Parameters.get(model.getStr(self.tag+"example-style")) # no checking, but these should already have passed the ExampleBuilder
#         self.structureAnalyzer.load(model)
#         return self.exampleWriter.write(exampleFileName, predictions, data, tag+self.tag+"pred.xml.gz", model.get(self.tag+"ids.classes"), parse, exampleStyle=exampleStyle, structureAnalyzer=self.structureAnalyzer)
        
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
        self.exampleBuilder.structureAnalyzer = self.structureAnalyzer
        self.matrices = {} # For the Python-dictionary matrices generated by KerasExampleBuilder
        modelChanged = False
        # Make example for all input files
        for setName, data, output, gold in itertools.izip_longest(setNames, datas, outputs, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName, "to file", output
            if saveIdsToModel:
                modelChanged = True
            builder = self.exampleBuilder.run(data, output, parse, None, exampleStyle, model.get(self.tag+"ids.classes", 
                True), model.get(self.tag+"ids.features", True), gold, False, saveIdsToModel,
                structureAnalyzer=self.structureAnalyzer)
            model.addStr("dimFeatures", str(len(builder.featureSet.Ids)))
            model.addStr("dimLabels", str(len(builder.classSet.Ids)))
            model.addStr("dimMatrix", str(builder.dimMatrix))
            examples = {"features":builder.featureMatrices,
                        "embeddings":builder.embeddingMatrices, 
                        "labels":builder.labelMatrices, 
                        "tokens":builder.tokenLists, 
                        "setName":setName}
            print >> sys.stderr, "Saving examples to", output
            self.saveJSON(output, examples)
            self.matrices[setName] = examples
            if "html" in self.styles:
                self.matricesToHTML(model, self.matrices[setName], output + ".html", int(self.styles["html"]))
                    
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
        
        #m = self.kerasModel = Sequential()
        #m.add(Dense(300, input_shape=(dimMatrix, dimMatrix, dimSourceFeatures)))
        #m.add(Conv2D(dimTargetFeatures, (1, 1), activation='sigmoid', padding='same'))
        #m.add(Conv2D(dimTargetFeatures, (1, 1), activation='sigmoid', padding='same', input_shape=(dimMatrix, dimMatrix, dimSourceFeatures)))

   
#         x = Input(shape=(dimMatrix, dimMatrix, dimSourceFeatures))
#         reshaped_x = Reshape((dimMatrix * dimMatrix, dimSourceFeatures))(x)
#         xx = TimeDistributed(Dense(dimTargetFeatures, activation="sigmoid"))(reshaped_x)
#         reshaped_xx = Reshape((dimMatrix, dimMatrix, dimTargetFeatures))(xx)
#         self.kerasModel = Model(x, reshaped_xx)
        
#         x = inputLayer = Input(shape=(dimMatrix, dimMatrix, dimSourceFeatures))
#         #x = Conv2D(dimTargetFeatures, (1, 3), activation='relu', padding='same')(x)
#         x = Reshape((dimMatrix * dimMatrix * dimSourceFeatures,))(x)
#         x = Dense(1024)(x)
#         x = Dense(dimMatrix * dimMatrix * dimSourceFeatures, activation="sigmoid")(x)
#         x = Reshape((dimMatrix, dimMatrix, dimTargetFeatures))(x)
#         #x = Conv2D(dimTargetFeatures, (1, 1), activation='sigmoid', padding='same')(x)
#         #x = Dense(12)(x)
#         #x = Dense(dimTargetFeatures, activation='sigmoid')(x)
#         self.kerasModel = Model(inputLayer, x)
        
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
        
#         w_array = np.ones((dimLabels,dimLabels))
#         labelIds = IdSet(filename=self.model.get(self.tag+"ids.classes"), locked=True)
#         negLabelIds = set([labelIds.getId(x) for x in ["Eneg", "Ineg", "[out]"]])
#         negWeight = 0.001
#         for i in range(dimLabels):
#             for j in range(dimLabels):
#                 if i in negLabelIds and j in negLabelIds:
#                     w_array[i, j] = negWeight
#                     w_array[j, i] = negWeight
#         print >> sys.stderr, "Loss weights:", w_array
#         
#         ncce = partial(w_categorical_crossentropy, weights=w_array)
#         ncce.__name__ = "w_categorical_crossentropy"
        
        print >> sys.stderr, "Compiling model"
        self.kerasModel.compile(optimizer=optimizer, loss="categorical_crossentropy", metrics=metrics, sample_weight_mode="temporal") #, metrics=['accuracy'])
        
        self.kerasModel.summary()
        
#         inputShape = x = Input(shape=(dimMatrix, dimMatrix, dimSourceFeatures))
#         #x = Conv2D(32, (3, 3), activation='relu', padding='same')(x)
#         #x = Conv2D(16, (5, 5), activation='relu', padding='same')(x)
#         #x = Conv2D(8, (1, 9), activation='relu', padding='same')(x)
#         #x = MaxPooling2D((1, 2), padding='same')(x)
#         #x = Conv2D(32, (1, 1), padding='same')(x)
#         #x = MaxPooling2D((1, 2), padding='same')(x)
#         #x = Conv2D(16, (1, 1), padding='same')(x)
#         #x = UpSampling2D((1, 2))(x)
#         #x = Conv2D(32, (1, 1), padding='same')(x)
#         #x = UpSampling2D((1, 2))(x)
#         #x = Conv2D(64, (1, 1), padding='same')(x)
#         x = Dense(300, activation='tanh')(x)
#         #x = Conv2D(16, (5, 1), activation='relu', padding='same')(x)
#         x = Conv2D(dimTargetFeatures, (1, 1), activation='sigmoid', padding='same')(x)
#         x = Conv2D(dimTargetFeatures, (1, 1), activation='softmax', padding='same')(x)
#         self.kerasModel = Model(inputShape, x)

        
#         x = inputShape = Input(shape=(dimMatrix, dimMatrix, dimSourceFeatures))
#         #x = Conv2D(dimSourceFeatures, (1, 1), activation="relu", padding='same')(x)
#         #x = Dense(dimSourceFeatures, activation="relu")(x)
#         #x = Conv2D(dimSourceFeatures, (3, 3), padding='same')(x)
#         x = Conv2D(32, (1, 3), padding='same')(x)
#         x = MaxPooling2D((2, 2))(x)
#         x = Conv2D(32, (3, 1), padding='same')(x)
#         x = MaxPooling2D((2, 2))(x)
#         x = UpSampling2D((2, 2))(x)
#         x = UpSampling2D((2, 2))(x)
#         #x = Dropout(0.5)(x)
#         #x = Conv2D(16, (1, 1), padding='same')(x)
#         #x = Conv2D(16, (1, 1), padding='same')(x)
#         #x = MaxPooling2D((2, 2))(x)
#         #x = Dense(18)(x)
#         #x = Dense(128)(x)
#         #x = Dense(dimTargetFeatures, activation='sigmoid')(x)
#         x = Conv2D(dimTargetFeatures, (1, 1), activation='sigmoid', padding='same')(x)
#         #x = UpSampling2D((2, 2))(x)
#         #x = Activation('softmax')(x)
#         self.kerasModel = Model(inputShape, x)
#         self.kerasModel.compile(optimizer="adadelta", loss='categorical_crossentropy', metrics=['accuracy'])
        
#         x = Conv2D(4, (3, 3), activation='relu', padding='same')(inputShape)
#         x = MaxPooling2D((2, 2))(x)
#         x = Conv2D(4, (3, 3), activation='relu', padding='same')(x)
#         x = UpSampling2D((2, 2))(x)
#         x = Conv2D(dimTargetFeatures, (3, 3), activation='relu', padding='same')(x)
#         self.kerasModel = Model(inputShape, x)
#         self.kerasModel.compile(optimizer="adadelta", loss='categorical_crossentropy', metrics=['accuracy'])
        
#         kernel = 3
#         encoding_layers = [
#             Conv2D(16, (kernel, kernel), padding='same', input_shape=(dimMatrix, dimMatrix, dimSourceFeatures)),
#             BatchNormalization(),
#             Activation('relu'),
#             Conv2D(64, (kernel, kernel), padding='same'),
#             BatchNormalization(),
#             Activation('relu'),
#             MaxPooling2D()]
#      
#         decoding_layers = [
#             UpSampling2D(),
#             Conv2D(dimTargetFeatures, (kernel, kernel), padding='same'),
#             BatchNormalization(),
#             Activation('relu'),
#             Conv2D(dimTargetFeatures, (kernel, kernel), padding='same'),
#             BatchNormalization(),
#             Activation('relu'),
#             Conv2D(dimTargetFeatures, (kernel, kernel), padding='same'),
#             BatchNormalization(),
#             Activation('relu')]
#          
#         self.kerasModel = Sequential()
#         for l in encoding_layers + decoding_layers:
#             self.kerasModel.add(l)
        
#         kernel = (1, 9)
#         size = (1, 2)
#          
#         encoding_layers = [
#             Conv2D(64, kernel, padding='same', input_shape=(dimMatrix, dimMatrix, dimSourceFeatures)),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(64, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             MaxPooling2D(pool_size=size),
#          
#             Conv2D(128, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(128, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             MaxPooling2D(pool_size=size),
#          
#             Conv2D(256, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(256, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(256, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             MaxPooling2D(pool_size=size),
#          
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             MaxPooling2D(),
# #         
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             MaxPooling2D(),
#         ]
#          
#         self.kerasModel = Sequential()
#         self.kerasModel.encoding_layers = encoding_layers
#          
#         for l in self.kerasModel.encoding_layers:
#             self.kerasModel.add(l)
#          
#         decoding_layers = [
# #             UpSampling2D(),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #         
# #             UpSampling2D(),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(512, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
# #             Conv2D(256, kernel, kernel, border_mode='same'),
# #             BatchNormalization(),
# #             Activation('relu'),
#          
#             UpSampling2D(size=size),
#             Conv2D(256, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(256, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(128, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#          
#             UpSampling2D(size=size),
#             Conv2D(128, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(64, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#          
#             UpSampling2D(size=size),
#             Conv2D(64, kernel, padding='same'),
#             #BatchNormalization(),
#             Activation('relu'),
#             Conv2D(dimTargetFeatures, (1, 1), padding='valid'),
#             #BatchNormalization(),
#         ]
#         self.kerasModel.decoding_layers = decoding_layers
#         for l in self.kerasModel.decoding_layers:
#             self.kerasModel.add(l)
#           
#         self.kerasModel.add(Activation('softmax'))
#           
#         print >> sys.stderr, "Compiling model"
#         optimizer = SGD(lr=0.001, momentum=0.9, decay=0.0005, nesterov=False)
#         self.kerasModel.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])
        
        # Various attempts at neural networks: ##########################################        
        
        #         x = Conv2D(8, (4, 4), activation='relu', padding='same')(inputShape)
        #         #x = UpSampling2D((2, 2))(x)
        #         decoded = Conv2D(dimTargetFeatures, (3, 3), activation='sigmoid', padding='same')(x)
         
        #         x = Conv2D(16, (3, 3), activation='relu', padding='same')(inputShape)
        #         x = MaxPooling2D((2, 2), padding='same')(x)
        #         x = Conv2D(8, (3, 3), activation='relu', padding='same')(x)
        #         x = MaxPooling2D((2, 2), padding='same')(x)
        #         x = Conv2D(8, (3, 3), activation='relu', padding='same')(x)
        #         encoded = MaxPooling2D((2, 2), padding='same')(x)
        #          
        #         # at this point the representation is (4, 4, 8) i.e. 128-dimensional
        #          
        #         x = Conv2D(8, (3, 3), activation='relu', padding='same')(encoded)
        #         x = UpSampling2D((2, 2))(x)
        #         x = Conv2D(8, (3, 3), activation='relu', padding='same')(x)
        #         x = UpSampling2D((2, 2))(x)
        #         x = Conv2D(16, (3, 3), activation='relu')(x)
        #         x = UpSampling2D((2, 2))(x)
        #         decoded = Conv2D(dimFeatures, (3, 3), activation='sigmoid', padding='same')(x)
        
        
        #x = Conv2D(16, (3, 3), padding='same')(inputShape)
        #output = Conv2D(dimTargetFeatures, (1, 1), activation='tanh', padding='same')(x)
        
        #x = Dense(100)(inputShape)
        #x = Dense(18)(x)
        
        #x = Conv2D(100, (5, 5), padding='same')(inputShape)
        #x = Conv2D(100, (3, 3), padding='same')(x)
        #x = Conv2D(100, (2, 2), padding='same')(x)
        #x = Conv2D(dimTargetFeatures, (1, 1), padding='same')(x)
        
        #self.kerasModel.compile(optimizer='adadelta', loss='binary_crossentropy', metrics=['accuracy'])
    
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