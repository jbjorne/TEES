import sys
from Detector import Detector
import itertools
from ExampleBuilders.KerasExampleBuilder import KerasExampleBuilder
from Detectors import SingleStageDetector
import numpy as np
import xml.etree.ElementTree as ET
import Utils.ElementTreeUtils as ETUtils
from Core.IdSet import IdSet
from keras.models import Sequential
from keras.callbacks import EarlyStopping, ModelCheckpoint
import Utils.Parameters
import gzip
import json

class KerasDetector(Detector):

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "keras-"
        self.exampleBuilder = KerasExampleBuilder
        self.matrices = None
        self.arrays = None
    
#     def beginModel(self, step, model, trainExampleFiles, testExampleFile, importIdsFromModel=None):
#         if self.checkStep(step, False):
#             if model != None:
#                 if self.state != None and step != None:
#                     print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
#                 # Create combined model
#                 model = self.openModel(model, "w")
#                 assert model.mode in ["a", "w"], (model.path, model.mode)
#                 model.save()
#     
#     def endModel(self, step, model, testExampleFile):
#         if self.checkStep(step, False):
#             if model != None:
#                 if self.state != None and step != None:
#                     print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
#                 # Download combined model
#                 model = self.openModel(model, "a")
#                 assert model.mode in ["a", "w"]
#                 model.save()
    
    def buildExamples(self, model, setNames, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False, parse=None):
        if exampleStyle == None:
            exampleStyle = model.getStr(self.tag+"example-style")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.structureAnalyzer.load(model)
        self.exampleBuilder.structureAnalyzer = self.structureAnalyzer
        self.matrices = {}
        modelChanged = False
        for setName, data, output, gold in itertools.izip_longest(setNames, datas, outputs, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName, "to file", output
            if saveIdsToModel:
                modelChanged = True
            builder = self.exampleBuilder.run(data, output, parse, None, exampleStyle, model.get(self.tag+"ids.classes", 
                True), model.get(self.tag+"ids.features", True), gold, False, saveIdsToModel,
                structureAnalyzer=self.structureAnalyzer)
            model.addStr("dimSourceFeatures", str(len(builder.featureSet.Ids)))
            model.addStr("dimTargetFeatures", str(len(builder.classSet.Ids)))
            model.addStr("dimMatrix", str(builder.dimMatrix))
            examples =  {"source":builder.sourceMatrices, "target":builder.targetMatrices, "tokens":builder.tokenLists, "setName":setName}
            print >> sys.stderr, "Saving examples to", output
            self.saveJSON(output, examples)
            #builders[dataSet].saveMatrices(output)
            self.matrices[setName] = examples
            self.matricesToHTML(model, self.matrices[setName], output + ".html")
                    
#             for setName in builders:
#                 self.dimFeatures = len(builders[dataSet].featureSet.Ids)
#                 model.addStr("dimFeatures", str(self.dimFeatures))
#                 model.addStr("dimMatrix", str(builders[dataSet].dimMatrix))
#                 examples =  {"source":builders[dataSet].sourceMatrices, "target":builders[dataSet].targetMatrices, "tokens":builders[dataSet].tokenLists, "setName":setName}
#                 self.saveJSON(output, examples)
#                 #builders[dataSet].saveMatrices(output)
#                 self.matrices[setName] = examples
                    
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if modelChanged:
            model.save()
        
        #sys.exit()
    
    def defineModel(self):
        print >> sys.stderr, "Importing Keras"
        from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D
        from keras.models import Model
        from keras import backend as K
        
        dimSourceFeatures = int(self.model.getStr("dimSourceFeatures"))
        dimTargetFeatures = int(self.model.getStr("dimTargetFeatures"))
        dimMatrix = int(self.model.getStr("dimMatrix"))
        
        print >> sys.stderr, "Defining model"
        inputShape = Input(shape=(dimMatrix, dimMatrix, dimSourceFeatures))  # adapt this if using `channels_first` image data format

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

        x = Conv2D(dimTargetFeatures, (1, 1), padding='same')(inputShape)
        
        self.kerasModel = Model(inputShape, x)
        
        print >> sys.stderr, "Compiling model"
        self.kerasModel.compile(optimizer='adadelta', loss='binary_crossentropy', metrics=['accuracy'])

    def fitModel(self, exampleFiles):
        if self.matrices == None:
            self.matrices = {}
            for setName in exampleFiles:
                print >> sys.stderr, "Loading dataset", setName, "from", exampleFiles[setName]
                #builder = self.exampleBuilder()
                #builder.loadMatrices(exampleFiles[dataSet])
                #self.matrices[dataSet] = {"source":builder.sourceMatrices, "target":builder.targetMatrices}
                self.matrices[setName] = self.loadJSON(exampleFiles[setName])
        if self.arrays == None:
            self.vectorizeMatrices(self.model)
        print >> sys.stderr, "Fitting model"
        
        #es_cb = EarlyStopping(monitor='val_loss', patience=10, verbose=1)
        #cp_cb = ModelCheckpoint(filepath=self.workDir + self.tag + 'model.hdf5', save_best_only=True, verbose=1)
        
        print "ARRAYS", self.arrays.keys()
        self.kerasModel.fit(self.arrays["train"]["source"], self.arrays["train"]["target"],
            epochs=100 if not "epochs" in self.styles else int(self.styles["epochs"]),
            batch_size=128,
            shuffle=True,
            validation_data=(self.arrays["devel"]["source"], self.arrays["devel"]["target"]))
            #callbacks=[es_cb])#, cp_cb])
        
        print >> sys.stderr, "Predicting devel examples"
        predictions = self.kerasModel.predict(self.arrays["devel"]["source"], 128, 1)
        
        predMatrices = self.loadJSON(exampleFiles["devel"])
        predMatrices["predicted"] = self.devectorizePredictions(predictions)
        self.matricesToHTML(self.model, predMatrices, self.workDir + self.tag + "devel-predictions.html")
        
        sys.exit()
    
    def matrixToTable(self, matrix, tokens):
        matrixRange = range(len(matrix) + 1)
        table = ET.Element('table', {"border":"1"})
        for i in matrixRange:
            tr = ET.SubElement(table, 'tr')
            for j in matrixRange:
                td = ET.SubElement(tr, 'td')
                if i == 0 or j == 0:
                    if i != 0 and i > 0 and i <= len(tokens): td.text = tokens[i - 1]
                    elif j != 0 and j > 0 and j <= len(tokens): td.text = tokens[j - 1]
                else:
                    if i == j:
                        #td.set("bgcolor", "#FF0000")
                        td.set("style", "font-weight:bold;")
                    features = matrix[i - 1][j - 1]
                    #featureNames = features.keys() #[]
                    if "color" in features:
                        td.set("bgcolor", features["color"])
                    featureNames = [x for x in features if x != "color"]
#                     for featureId in features:
#                         name = featureSet.getName(featureId)
#                         assert name != None
#                         value = features[featureId]
#                         if value != 1:
#                             name += "=" + str(value)
#                         featureNames.append(name)
                    featureNames.sort()
                    td.text = ",".join(featureNames)
        return table
    
    def matricesToHTML(self, model, data, filePath):
        root = ET.Element('html')     
        sourceMatrices = data["source"]
        targetMatrices = data["target"]
        predMatrices = data.get("predicted")
        tokenLists = data["tokens"]
        #numExamples = len(sourceMatrices)
        for i in range(len(sourceMatrices)):
            ET.SubElement(root, "p").text = str(i) + ": " + " ".join(tokenLists[i])
            root.append(self.matrixToTable(sourceMatrices[i], tokenLists[i]))
            root.append(self.matrixToTable(targetMatrices[i], tokenLists[i]))
            if predMatrices is not None:
                root.append(self.matrixToTable(predMatrices[i], tokenLists[i]))
        print >> sys.stderr, "Writing adjacency matrix visualization to", filePath
        ETUtils.write(root, filePath)
    
    def saveJSON(self, filePath, data):
        with gzip.open(filePath, "wt") as f:
            json.dump(data, f)
    
    def loadJSON(self, filePath):
        with gzip.open(filePath, "rt") as f:
            return json.load(f)
    
    def clamp(self, value, lower, upper):
        return max(lower, min(value, upper))
    
    def getColor(self, value):
        r = self.clamp(int(1.0 - value * 255.0), 0, 255)
        g = self.clamp(int(value * 255.0), 0, 255)
        b = 0
        return '#%02x%02x%02x' % (r, g, b)
    
    def devectorizePredictions(self, predictions):
        #sourceIds = IdSet(filename=self.model.get(self.tag+"ids.features"), locked=True)
        targetIds = IdSet(filename=self.model.get(self.tag+"ids.classes"), locked=True)
        #dimFeatures = int(self.model.getStr("dimFeatures"))
        dimMatrix = int(self.model.getStr("dimMatrix"))
        rangeMatrix = range(dimMatrix)
        labels = np.argmax(predictions, axis=-1)
        values = np.max(predictions, axis=-1)
        minValue = np.max(values)
        maxValue = np.min(values)
        valRange = maxValue - minValue
        #print "MINMAX", minValue, maxValue
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
                    features[targetIds.getName(maxFeature)] = 1
                    features["color"] = self.getColor((values[exampleIndex][i][j] - minValue) / valRange)
        return devectorized
    
    def vectorizeMatrices(self, model):
        self.arrays = {}
        sourceIds = IdSet(filename=model.get(self.tag+"ids.features"), locked=True)
        targetIds = IdSet(filename=model.get(self.tag+"ids.classes"), locked=True)
        dimSourceFeatures = int(model.getStr("dimSourceFeatures"))
        dimTargetFeatures = int(model.getStr("dimTargetFeatures"))
        dimMatrix = int(model.getStr("dimMatrix"))
        rangeMatrix = range(dimMatrix)
        dataSets = [(x, self.matrices[x]) for x in sorted(self.matrices.keys())]
        self.matrices = None
        while dataSets:
            dataSetName, dataSetValue = dataSets.pop()
            print >> sys.stderr, "Vectorizing dataset", dataSetName
            sourceMatrices = dataSetValue["source"]
            targetMatrices = dataSetValue["target"]
            assert len(sourceMatrices) == len(targetMatrices)
            numExamples = len(sourceMatrices)
            sourceArrays = np.zeros((numExamples, dimMatrix, dimMatrix, dimSourceFeatures), dtype=np.float32)
            targetArrays = np.zeros((numExamples, dimMatrix, dimMatrix, dimTargetFeatures), dtype=np.float32)
            for exampleIndex in range(numExamples):
                sourceArray = sourceArrays[exampleIndex] #sourceArray = np.zeros((dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
                targetArray = targetArrays[exampleIndex] #targetArray = np.zeros((dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
                sourceMatrix = sourceMatrices.pop(0) #[exampleIndex]
                targetMatrix = targetMatrices.pop(0) #[exampleIndex]
                for matrix, array, ids in [(sourceMatrix, sourceArray, sourceIds), (targetMatrix, targetArray, targetIds)]:
                    for i in rangeMatrix:
                        for j in rangeMatrix:
                            features = matrix[i][j]
                            #print features
                            for featureName in features:
                                array[i][j][ids.getId(featureName)] = features[featureName]
            self.arrays[dataSetName] = {"source":sourceArrays, "target":targetArrays}
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None,
              workDir=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES", "DEFINE-MODEL", "FIT-MODEL"], fromStep, toStep)
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
        if self.checkStep("EXAMPLES"):
            self.buildExamples(self.model, ["devel", "train"], [optData, trainData], [exampleFiles["devel"], exampleFiles["train"]], saveIdsToModel=True)
        #self.beginModel("BEGIN-MODEL", self.model, [self.workDir+self.tag+"train-examples.gz"], self.workDir+self.tag+"opt-examples.gz")
        if self.checkStep("DEFINE-MODEL"):
            self.defineModel()
        if self.checkStep("FIT-MODEL"):
            self.fitModel(exampleFiles)
        #self.endModel("END-MODEL", self.model, self.workDir+self.tag+"opt-examples.gz")
        #self.beginModel("BEGIN-COMBINED-MODEL", self.combinedModel, [self.workDir+self.tag+"train-examples.gz", self.workDir+self.tag+"opt-examples.gz"], self.workDir+self.tag+"opt-examples.gz", self.model)
        #self.endModel("END-COMBINED-MODEL", self.combinedModel, self.workDir+self.tag+"opt-examples.gz")
        if workDir != None:
            self.setWorkDir("")
        self.arrays = None
        self.exitState()