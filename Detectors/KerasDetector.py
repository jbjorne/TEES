import sys
from Detector import Detector
import itertools
from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D
from keras.models import Model
from keras import backend as K
from ExampleBuilders.KerasExampleBuilder import KerasExampleBuilder
from Detectors import SingleStageDetector

class EventDetector(Detector):

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "keras-"
        self.exampleBuilder = KerasExampleBuilder
        self.dimFeatures = None
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
        self.arrays = {}
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
                self.dimFeatures = len(builders[dataSet].featureIds)
                model.addStr("dimFeatures", str(self.dimFeatures))
                builders[dataSet].saveMatrices(output)
                self.arrays[dataSet] = {"source":self.exampleBuilder.sourceArrays, "target":self.exampleBuilder.targetArrays}
                    
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if modelChanged:
            model.save()
    
    def defineModel(self):
        if self.dimFeatures == None:
            self.dimFeatures = int(self.model.getStr("dimFeatures"))
        
        inputShape = Input(shape=(30, 30, self.dimFeatures))  # adapt this if using `channels_first` image data format

        x = Conv2D(16, (3, 3), activation='relu', padding='same')(inputShape)
        x = MaxPooling2D((2, 2), padding='same')(x)
        x = Conv2D(8, (3, 3), activation='relu', padding='same')(x)
        x = MaxPooling2D((2, 2), padding='same')(x)
        x = Conv2D(8, (3, 3), activation='relu', padding='same')(x)
        encoded = MaxPooling2D((2, 2), padding='same')(x)
        
        # at this point the representation is (4, 4, 8) i.e. 128-dimensional
        
        x = Conv2D(8, (3, 3), activation='relu', padding='same')(encoded)
        x = UpSampling2D((2, 2))(x)
        x = Conv2D(8, (3, 3), activation='relu', padding='same')(x)
        x = UpSampling2D((2, 2))(x)
        x = Conv2D(16, (3, 3), activation='relu')(x)
        x = UpSampling2D((2, 2))(x)
        decoded = Conv2D(1, (3, 3), activation='sigmoid', padding='same')(x)
        
        self.model = Model(inputShape, decoded)
        self.model.compile(optimizer='adadelta', loss='binary_crossentropy')
    
    def fitModel(self, exampleFiles):
        if self.arrays == None:
            self.arrays = {}
            for dataSet in exampleFiles:
                builder = self.exampleBuilder()
                builder.loadMatrices(self.model.get(exampleFiles[dataSet]))
                self.arrays[dataSet] = {"source":self.exampleBuilder.sourceArrays, "target":self.exampleBuilder.targetArrays}
        self.model.fit(self.arrays["train"]["source"], self.arrays["train"]["target"],
            epochs=100,
            batch_size=128,
            shuffle=True,
            validation_data=(self.arrays["devel"]["source"], self.arrays["devel"]["target"]),
            callbacks=None)
    
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
        exampleFiles = {"devel":self.workDir+self.tag+"opt-examples.gz", "train":self.workDir+self.tag+"train-examples.gz"}
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