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

class KerasDetector(Detector):

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "keras-"
        self.exampleBuilder = KerasExampleBuilder
        self.dimFeatures = None
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
    
    def buildExamples(self, model, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False, parse=None):
        if exampleStyle == None:
            exampleStyle = model.getStr(self.tag+"example-style")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.structureAnalyzer.load(model)
        self.exampleBuilder.structureAnalyzer = self.structureAnalyzer
        self.matrices = {}
        modelChanged = False
        for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
            print >> sys.stderr, "Example generation for", output
            if not isinstance(data, (list, tuple)): data = [data]
            if not isinstance(gold, (list, tuple)): gold = [gold]
            builders = {}
            for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                if dataSet != None:
                    if saveIdsToModel:
                        modelChanged = True
                    builders[dataSet] = self.exampleBuilder.run(dataSet, output, parse, None, exampleStyle, model.get(self.tag+"ids.classes", 
                        True), model.get(self.tag+"ids.features", True), goldSet, False, saveIdsToModel,
                        structureAnalyzer=self.structureAnalyzer)
            for dataSet in builders:
                self.dimFeatures = len(builders[dataSet].featureSet.Ids)
                model.addStr("dimFeatures", str(self.dimFeatures))
                model.addStr("dimMatrix", str(builders[dataSet].dimMatrix))
                builders[dataSet].saveMatrices(output)
                self.matrices[output] = {"source":builders[dataSet].sourceMatrices, "target":builders[dataSet].targetMatrices, "tokens":builders[dataSet].tokenLists}
                    
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if modelChanged:
            model.save()
        
        self.matricesToHTML(model)
        #sys.exit()
    
    def defineModel(self):
        print >> sys.stderr, "Importing Keras"
        from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D
        from keras.models import Model
        from keras import backend as K
        
        dimFeatures = int(self.model.getStr("dimFeatures"))
        dimMatrix = int(self.model.getStr("dimMatrix"))
        
        print >> sys.stderr, "Defining model"
        if self.dimFeatures == None:
            self.dimFeatures = int(self.model.getStr("dimFeatures"))
        
        inputShape = Input(shape=(dimMatrix, dimMatrix, dimFeatures))  # adapt this if using `channels_first` image data format

        x = Conv2D(8, (4, 4), activation='relu', padding='same')(inputShape)
        #x = UpSampling2D((2, 2))(x)
        decoded = Conv2D(dimFeatures, (3, 3), activation='sigmoid', padding='same')(x)
 
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
        
        self.kerasModel = Model(inputShape, decoded)
        
        print >> sys.stderr, "Compiling model"
        self.kerasModel.compile(optimizer='adadelta', loss='binary_crossentropy', metrics=['accuracy'])

    def fitModel(self, exampleFiles):
        if self.matrices == None:
            self.matrices = {}
            for dataSet in exampleFiles:
                print >> sys.stderr, "Loading dataset", dataSet, "from", exampleFiles[dataSet]
                builder = self.exampleBuilder()
                builder.loadMatrices(exampleFiles[dataSet])
                self.matrices[dataSet] = {"source":builder.sourceMatrices, "target":builder.targetMatrices}
        if self.arrays == None:
            self.vectorizeMatrices(self.model)
        print >> sys.stderr, "Fitting model"
        
        #es_cb = EarlyStopping(monitor='val_loss', patience=10, verbose=1)
        #cp_cb = ModelCheckpoint(filepath=self.workDir + self.tag + 'model.hdf5', save_best_only=True, verbose=1)
        
        self.kerasModel.fit(self.arrays["train"]["source"], self.arrays["train"]["target"],
            epochs=1, #100,
            batch_size=128,
            shuffle=True,
            validation_data=(self.arrays["devel"]["source"], self.arrays["devel"]["target"]))
            #callbacks=[es_cb])#, cp_cb])
        
        print >> sys.stderr, "Predicting devel examples"
        predictions = self.kerasModel.predict(self.arrays["devel"]["source"], 128, 1)
        predictions = np.argmax(predictions, axis=-1)
        self.predictionsToDicts(predictions)
        
        sys.exit()
    
    def predictionsToDicts(self, predictions):
        for exampleIndex in range(predictions.shape[0]):
            print predictions[exampleIndex]
    
    def matrixToTable(self, matrix, tokens, featureSet):
        matrixRange = range(len(matrix) + 1)
        table = ET.Element('table', {"border":"1"})
        for i in matrixRange:
            tr = ET.SubElement(table, 'tr')
            for j in matrixRange:
                td = ET.SubElement(tr, 'td')
                if i == 0 or j == 0:
                    if i != 0 and i > 0 and i <= len(tokens): td.text = tokens[i - 1].get("text")
                    elif j != 0 and j > 0 and j <= len(tokens): td.text = tokens[j - 1].get("text")
                else:
                    if i == j:
                        td.set("bgcolor", "#FF0000")
                    features = matrix[i - 1][j - 1]
                    featureNames = []
                    for featureId in features:
                        name = featureSet.getName(featureId)
                        value = features[featureId]
                        if value != 1:
                            name += "=" + str(value)
                        featureNames.append(name)
                    featureNames.sort()
                    td.text = ",".join(featureNames)
        return table
    
    def matricesToHTML(self, model):
        featureSet = IdSet(filename=model.get(self.tag+"ids.features"), locked=True)
        
        root = ET.Element('html')     
        for outPathStem in self.matrices:
            sourceMatrices = self.matrices[outPathStem]["source"]
            tokenLists = self.matrices[outPathStem]["tokens"]
            targetMatrices = self.matrices[outPathStem]["target"]
            #numExamples = len(sourceMatrices)
            for i in range(len(sourceMatrices)):
                ET.SubElement(root, "p").text = str(i) + ": " + " ".join([x.get("text") for x in tokenLists[i]])
                root.append(self.matrixToTable(sourceMatrices[i], tokenLists[i], featureSet))
                root.append(self.matrixToTable(targetMatrices[i], tokenLists[i], featureSet))
            ETUtils.write(root, outPathStem + ".html")
    
    def vectorizeMatrices(self, model):
        self.arrays = {}
        featureSet = IdSet(filename=model.get(self.tag+"ids.features"), locked=True)
        dimFeatures = int(model.getStr("dimFeatures"))
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
            sourceArrays = np.zeros((numExamples, dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
            targetArrays = np.zeros((numExamples, dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
            for exampleIndex in range(numExamples):
                sourceArray = sourceArrays[exampleIndex] #sourceArray = np.zeros((dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
                targetArray = targetArrays[exampleIndex] #targetArray = np.zeros((dimMatrix, dimMatrix, dimFeatures), dtype=np.float32)
                sourceMatrix = sourceMatrices.pop(0) #[exampleIndex]
                targetMatrix = targetMatrices.pop(0) #[exampleIndex]
                for matrix, array in [(sourceMatrix, sourceArray), (targetMatrix, targetArray)]:
                    for i in rangeMatrix:
                        for j in rangeMatrix:
                            features = matrix[i][j]
                            #print features
                            for featureName in features:
                                array[i][j][featureSet.getId(featureName)] = features[featureName]
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
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        exampleFiles = {"devel":self.workDir+self.tag+"opt-examples.json.gz", "train":self.workDir+self.tag+"train-examples.json.gz"}
        if self.checkStep("EXAMPLES"):
            self.buildExamples(self.model, [optData, trainData], [exampleFiles["devel"], exampleFiles["train"]], saveIdsToModel=True)
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