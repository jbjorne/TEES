import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import copy
import json
import types
from Classifier import Classifier
import Utils.Connection.Connection as Connection
from Utils.Connection.UnixConnection import UnixConnection
import Utils.Parameters as Parameters
from sklearn import datasets, preprocessing
from keras.layers import Input, Dense
from keras.models import Model, load_model
from keras.optimizers import SGD, Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
import numpy as np

def batch_generator(X, y, batch_size):
    number_of_batches = X.shape[0] / batch_size #samples_per_epoch / batch_size
    counter=0
    shuffle_index = np.arange(np.shape(y)[0])
    np.random.shuffle(shuffle_index)
    X =  X[shuffle_index, :]
    y =  y[shuffle_index]
    while 1:
        index_batch = shuffle_index[batch_size*counter:batch_size*(counter+1)]
        X_batch = X[index_batch,:].todense()
        y_batch = y[index_batch]
        counter += 1
        yield(np.array(X_batch),y_batch)
        if (counter < number_of_batches):
            np.random.shuffle(shuffle_index)
            counter=0

def predict_batch_generator(X, batch_size):
    number_of_batches = X.shape[0] / batch_size
    while 1:
        for i in range(number_of_batches):
            batchIndex = i * batch_size
            #print "INDEX", (batchIndex, batchIndex + batch_size)
            Xbatch = X[batchIndex:batchIndex + batch_size].todense()
            #print Xbatch.shape
            yield(np.array(Xbatch))

class KerasClassifier(Classifier):
    def __init__(self, connection=None):
        self.defaultEvaluator = None
        if connection == None:
            self.connection = UnixConnection() # A local connection
        else:
            self.connection = connection
        self._filesToRelease = []
        
        self.parameters = None
        self.model = None
        self.predictions = None
        self.numFeatures = None
    
#     def saveModel(self, teesModel, tag=""):
#         Classifier.saveModel(self, teesModel, tag)
#         if hasattr(self, "numFeatures") and self.numFeatures != None:
#             teesModel.addStr(tag+"numFeatures", str(self.numFeatures))
    
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
        
        self.kerasModel = load_model(model)
        numFeatures = self.kerasModel.layers[0].get_input_shape_at(0)[1]
        
        features, classes = datasets.load_svmlight_file(examples, numFeatures)
        #features = features.toarray()
        #predictions = self.kerasModel.predict(features, 128, 1)
        predictions = self.kerasModel.predict_generator(predict_batch_generator(features, 1), features.shape[0] / 1)
        predClasses = predictions.argmax(axis=-1)

        predictionsPath = self.connection.getRemotePath(output, False)
        with open(predictionsPath, "wt") as f:
            for i in range(predictions.shape[0]):
                f.write(str(predClasses[i] + 1) + " " + " ".join([str(x) for x in  predictions[i]]) + "\n")                
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
        assert step in ["BOTH", "SUBMIT", "RESULTS"], step
        if step == "RESULTS": # Return already
            classifier = copy.copy(self)
            classifier.parameters = parameters
            classifier.model = self.connection.getRemotePath(outDir + "/model.hdf5", True)
            return classifier
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
            develFeatures, develClasses = datasets.load_svmlight_file(classifyExamples, trainFeatures.shape[1])
        binarizer = preprocessing.LabelBinarizer()
        binarizer.fit(trainClasses)
        trainClasses = binarizer.transform(trainClasses)
        if classifyExamples != None:
            develClasses = binarizer.transform(develClasses)
        
        print >> sys.stderr, "Training Keras model with parameters:", parameters
        parameters = Parameters.get(parameters, {"TEES.classifier":"KerasClassifier", "layers":5, "lr":0.001, "epochs":1, "batch_size":64, "patience":10})
        np.random.seed(10)
        classifier.kerasModel = classifier._defineModel(outDir, parameters, trainFeatures, trainClasses, develFeatures, develClasses)
        classifier._fitModel(outDir, parameters, trainFeatures, trainClasses, develFeatures, develClasses)
    
    def _defineModel(self, outDir, parameters, trainFeatures, trainClasses, develFeatures, develClasses):        
        x = inputLayer = Input(shape=(trainFeatures.shape[1],))
        layers = parameters["layers"]
        if type(layers) not in [types.ListType, types.TupleType]:
            layers = [layers]
        for layer in layers:
            x = Dense(int(layer), activation='relu')(x)
        x = Dense(trainClasses.shape[1], activation='softmax')(x)
        kerasModel = Model(inputLayer, x)
        
        layersPath = self.connection.getRemotePath(outDir + "/layers.json", False)
        print >> sys.stderr, "Saving layers to", layersPath
        self._serializeLayers(kerasModel, layersPath)
        
        learningRate = float(parameters["lr"]) #0.001 #float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"]
        kerasModel.compile(optimizer=optimizer, loss="categorical_crossentropy", metrics=metrics) #, metrics=['accuracy'])
        
        kerasModel.summary()
        return kerasModel
    
    def _fitModel(self, outDir, parameters, trainFeatures, trainClasses, develFeatures, develClasses):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """        
        print >> sys.stderr, "Fitting model"
        
        patience = int(parameters["patience"]) #10 #int(self.styles.get("patience", 10))
        print >> sys.stderr, "Early stopping patience:", patience
        es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
        self.model = self.connection.getRemotePath(outDir + "/model.hdf5", True)
        modelPath = self.connection.getRemotePath(outDir + "/model.hdf5", False)
        cp_cb = ModelCheckpoint(filepath=modelPath, save_best_only=True, verbose=1)
        
        #self.numFeatures = trainFeatures.shape[1]
        
#         #print "SHAPE", trainFeatures.shape, trainClasses.shape, develFeatures.shape, develClasses.shape
#         self.kerasModel.fit(trainFeatures, trainClasses,
#             epochs=100, #100 if not "epochs" in self.styles else int(self.styles["epochs"]),
#             batch_size=64,
#             shuffle=True,
#             validation_data=(develFeatures, develClasses),
#             #sample_weight=self.arrays["train"]["mask"],
#             callbacks=[es_cb, cp_cb])
        
        self.kerasModel.fit_generator(generator=batch_generator(trainFeatures, trainClasses, int(parameters["batch_size"])),
            epochs=int(parameters["epochs"]), 
            samples_per_epoch=trainFeatures.shape[0],
            validation_data=batch_generator(develFeatures, develClasses, int(parameters["batch_size"])),
            validation_steps=develFeatures.shape[0] / int(parameters["batch_size"]),
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