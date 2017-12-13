import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
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
        self.kerasModel = load_model(bestModelPath)
        predictions = self.kerasModel.predict(self.arrays["devel"], 128, 1)
    
    def train(self, examples, outDir, parameters, classifyExamples=None, dummy=False):
        outDir = os.path.abspath(outDir)
        
        examples = self.getExampleFile(examples, dummy=dummy)
        classifyExamples = self.getExampleFile(classifyExamples, dummy=dummy)
        
        trainFeatures, trainClasses = datasets.load_svmlight_file(examples)
        if classifyExamples != None:
            develFeatures, develClasses = datasets.load_svmlight_file(classifyExamples)
        
        x = inputLayer = Input(shape=(trainFeatures.shape[0], trainFeatures.shape[1]))
        x = Dense(1024)(x)
        x = Dense(trainClasses.shape[0], activation='sigmoid')(x)
        self.kerasModel = Model(inputLayer, x)
        
        layersPath = self.workDir + self.tag + "layers.json"
        print >> sys.stderr, "Saving layers to", layersPath
        self.serializeLayers(self.kerasModel, layersPath)
        
        learningRate = float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"]
        self.kerasModel.compile(optimizer=optimizer, loss="categorical_crossentropy", metrics=metrics, sample_weight_mode="temporal") #, metrics=['accuracy'])
        
        self.kerasModel.summary()
    
    def _fitModel(self, trainFeatures, trainClasses, develFeatures, develClasses):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """        
        print >> sys.stderr, "Fitting model"
        
        patience = int(self.styles.get("patience", 10))
        print >> sys.stderr, "Early stopping patience:", patience
        es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
        bestModelPath = self.model.get(self.tag + "model.hdf5", True)
        cp_cb = ModelCheckpoint(filepath=bestModelPath, save_best_only=True, verbose=1)
        
        self.kerasModel.fit(trainFeatures, trainClasses,
            epochs=100 if not "epochs" in self.styles else int(self.styles["epochs"]),
            batch_size=64,
            shuffle=True,
            validation_data=(develFeatures, develClasses),
            sample_weight=self.arrays["train"]["mask"],
            callbacks=[es_cb, cp_cb])
        
        bestModelPath = self.model.get(self.tag + "model.hdf5", True)
