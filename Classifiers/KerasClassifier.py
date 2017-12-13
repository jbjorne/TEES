import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import copy
import json
from Classifier import Classifier
from sklearn import datasets
from keras.layers import Input, Dense
from keras.models import Model, load_model
from keras.optimizers import SGD, Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint

class KerasClassifier(Classifier):
    def __init__(self):
        pass
    
    def classify(self, examples, output, model=None, finishBeforeReturn=False, replaceRemoteFiles=True):
        print >> sys.stderr, "Predicting devel examples"
        output = os.path.abspath(output)
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        
        if model == None:
            classifier.model = model = self.model
        model = os.path.abspath(model)
        model = self.connection.upload(model, uncompress=True, replace=replaceRemoteFiles)
        classifier.predictions = self.connection.getRemotePath(output, True)
        examples = self.getExampleFile(examples, replaceRemote=replaceRemoteFiles)
        classifier._filesToRelease = [examples]
        
        features, classes = datasets.load_svmlight_file(examples)
        self.kerasModel = load_model(model)
        predictions = self.kerasModel.predict(features, 128, 1)
        predClasses = predictions.argmax(axis=-1)

        predictionsPath = self.connection.getRemotePath(output, False)
        with open(predictionsPath, "wt") as f:
            f.write(predClasses)
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
        return self.train(examples, outDir, parameters, classifyExamples)
    
    def train(self, examples, outDir, parameters, classifyExamples=None, dummy=False):
        outDir = os.path.abspath(outDir)
        
        examples = self.getExampleFile(examples, dummy=dummy)
        classifyExamples = self.getExampleFile(classifyExamples, dummy=dummy)
        
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        classifier.parameters = parameters
        classifier._filesToRelease = [examples, classifyExamples]
        
        if not os.path.exists(outDir):
            os.makedirs(outDir)
        
        trainFeatures, trainClasses = datasets.load_svmlight_file(examples)
        if classifyExamples != None:
            develFeatures, develClasses = datasets.load_svmlight_file(classifyExamples)
        
        classifier.kerasModel = classifier._defineModel(outDir, parameters, trainFeatures, trainClasses, develFeatures, develClasses)
        classifier._fitModel(outDir, trainFeatures, trainClasses, develFeatures, develClasses)
    
    def _defineModel(self, outDir, parameters, trainFeatures, trainClasses, develFeatures, develClasses):        
        x = inputLayer = Input(shape=(trainFeatures.shape[0], trainFeatures.shape[1]))
        x = Dense(1024, activation='relu')(x)
        x = Dense(trainClasses.shape[0], activation='softmax')(x)
        kerasModel = Model(inputLayer, x)
        
        layersPath = self.connection.getRemotePath(outDir + "/layers.json", False)
        print >> sys.stderr, "Saving layers to", layersPath
        self.serializeLayers(self.kerasModel, layersPath)
        
        learningRate = 0.001 #float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"]
        kerasModel.compile(optimizer=optimizer, loss="categorical_crossentropy", metrics=metrics, sample_weight_mode="temporal") #, metrics=['accuracy'])
        
        kerasModel.summary()
        return kerasModel
    
    def _fitModel(self, outDir, trainFeatures, trainClasses, develFeatures, develClasses):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """        
        print >> sys.stderr, "Fitting model"
        
        patience = 10 #int(self.styles.get("patience", 10))
        print >> sys.stderr, "Early stopping patience:", patience
        es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
        self.model = self.connection.getRemotePath(outDir + "/model.hdf5", True)
        modelPath = self.connection.getRemotePath(outDir + "/model.hdf5", False)
        cp_cb = ModelCheckpoint(filepath=modelPath, save_best_only=True, verbose=1)
        
        self.kerasModel.fit(trainFeatures, trainClasses,
            epochs=100, #100 if not "epochs" in self.styles else int(self.styles["epochs"]),
            batch_size=64,
            shuffle=True,
            validation_data=(develFeatures, develClasses),
            #sample_weight=self.arrays["train"]["mask"],
            callbacks=[es_cb, cp_cb])
    
    def _serializeLayers(self, kerasModel, filePath, verbose=False):
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