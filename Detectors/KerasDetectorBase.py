import sys, os
import shutil
import gzip
import json
import itertools
import types
from Detector import Detector
from Core.SentenceGraph import getCorpusIterator
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
from Core.IdSet import IdSet
import Utils.Parameters
import Utils.Settings as Settings
from Utils.EmbeddingIndex import EmbeddingIndex
from Utils.ProgressCounter import ProgressCounter
from ExampleBuilders.ExampleStats import ExampleStats
from Evaluators import EvaluateInteractionXML
from Utils import Parameters
from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import numpy
from keras.layers import Dense
from keras.models import Model, load_model
from keras.layers.core import Dropout, Flatten
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import merge
from itertools import chain
import sklearn.metrics
from sklearn.preprocessing.label import MultiLabelBinarizer
from sklearn.metrics.classification import classification_report
from keras.layers import Conv1D
from keras.layers.pooling import MaxPooling1D
from __builtin__ import isinstance
from collections import defaultdict

def f1ScoreMetric(y_true, y_pred):
    return sklearn.metrics.f1_score(y_true, y_pred, average="micro")

class KerasDetectorBase(Detector):
    """
    The KerasDetector replaces the default SVM-based learning with a pipeline where
    sentences from the XML corpora are converted into adjacency matrix examples which
    are used to train the Keras model defined in the KerasDetector.
    """

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = None
        self.exampleWriter = None
        self.evaluator = AveragingMultiClassEvaluator
        self.debugGold = False
        self.exampleLength = None
    
    ###########################################################################
    # Main Pipeline Interface
    ###########################################################################
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None,
              workDir=None, testData=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        self.model = model
        assert model != None
        if self.state != self.STATE_COMPONENT_TRAIN:
            self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES", "MODEL"], fromStep, toStep)
        if self.state == self.STATE_COMPONENT_TRAIN or self.checkStep("ANALYZE"):
            # General training initialization done at the beginning of the first state
            self.model = self.initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters-train")])
            self.saveStr(self.tag+"parse", parse, self.model)
            if task != None:
                self.saveStr(self.tag+"task", task, self.model)
            self.model.save()
            # Perform structure analysis
            self.structureAnalyzer.analyze([optData, trainData], self.model)
            print >> sys.stderr, self.structureAnalyzer.toString()
            #self.distanceAnalyzer.analyze([optData, trainData], parse=parse)
            #print >> sys.stderr, self.distanceAnalyzer.toDict()
        self.styles = Utils.Parameters.get(exampleStyle)
        self.pathDepth = int(self.styles.get("path", 3))
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        exampleFiles = {"devel":self.workDir+self.tag+"opt-examples.json.gz", "train":self.workDir+self.tag+"train-examples.json.gz"}
        if self.state == self.STATE_COMPONENT_TRAIN or self.checkStep("EXAMPLES"): # Generate the adjacency matrices
            self.initEmbeddings([optData, trainData, testData] if testData != None else [optData, trainData], parse)
            self.buildExamples(self.model, ["devel", "train"], [optData, trainData], [exampleFiles["devel"], exampleFiles["train"]], saveIdsToModel=True)
            self.padExamples(self.model, self.examples)
            self.saveEmbeddings(self.embeddings, self.model.get(self.tag + "embeddings.json", True))
            if self.exampleLength != None and self.model.getStr(self.tag + "example-length", None, int) == None:
                self.saveStr(self.tag + "example-length", str(self.exampleLength), self.model)
            self.model.save()
            #if "test" in self.examples: # Test examples are generated here only for initializing the embeddings
            #    del self.examples["test"]
        #print self.examples["devel"][0:2]
        self.showExample(self.examples["devel"][0])
        if self.state == self.STATE_COMPONENT_TRAIN or self.checkStep("MODEL"): # Define and train the Keras model
            self.fitModel()
        if workDir != None:
            self.setWorkDir("")
        self.exitState()
    
    def classify(self, data, model, output, parse=None, task=None, goldData=None, workDir=None, fromStep=None, omitSteps=None, validate=False):
        self.enterState(self.STATE_CLASSIFY)
        self.setWorkDir(workDir)
        if workDir == None:
            self.setTempWorkDir()
        model = self.openModel(model, "r")
        if parse == None: parse = self.getStr(self.tag+"parse", model)
        workOutputTag = os.path.join(self.workDir, os.path.basename(output) + "-")
        xml = self.classifyToXML(data, model, None, workOutputTag, 
            model.get(self.tag+"classifier-model", defaultIfNotExist=None), goldData, parse, float(model.getStr("recallAdjustParameter", defaultIfNotExist=1.0)))
        if (validate):
            self.structureAnalyzer.load(model)
            self.structureAnalyzer.validate(xml)
            ETUtils.write(xml, output+"-pred.xml.gz")
        else:
            shutil.copy2(workOutputTag+self.tag+"pred.xml.gz", output+"-pred.xml.gz")
        EvaluateInteractionXML.run(self.evaluator, xml, data, parse)
#         stParams = self.getBioNLPSharedTaskParams(self.bioNLPSTParams, model)
#         if stParams.get("convert"): #self.useBioNLPSTFormat:
#             extension = ".zip" if (stParams["convert"] == "zip") else ".tar.gz" 
#             Utils.STFormat.ConvertXML.toSTFormat(xml, output+"-events" + extension, outputTag=stParams["a2Tag"], writeExtra=(stParams["scores"] == True))
#             if stParams["evaluate"]: #self.stEvaluator != None:
#                 if task == None: 
#                     task = self.getStr(self.tag+"task", model)
#                 self.stEvaluator.evaluate(output+"-events" + extension, task)
        self.deleteTempWorkDir()
        self.exitState()
    
    def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, goldData=None, parse=None, recallAdjust=None, compressExamples=True, exampleStyle=None, useExistingExamples=False):
        model = self.openModel(model, "r")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        if not useExistingExamples:
            self.buildExamples(model, ["classification"], [data], [exampleFileName], [goldData], parse=parse, exampleStyle=exampleStyle)
            self.padExamples(model, self.examples)
        examples = self.examples["classification"]
        self.showExample(examples[0])
        if classifierModel == None:
            classifierModel = model.get(self.tag + "model.hdf5")
        labelSet = IdSet(filename = model.get(self.tag + "labels.ids", False), locked=True)
        labelNames = [None] * len(labelSet.Ids)
        for label in labelSet.Ids:
            labelNames[labelSet.Ids[label]] = label
        print >> sys.stderr, "Classification labels", labelNames
        labels, _ = self.vectorizeLabels(examples, ["classification"], labelNames)
        features = self.vectorizeFeatures(examples, ["classification"])
        predictions, confidences, _ = self.predict(labels["classification"], features["classification"], labelNames, classifierModel)
        if exampleStyle == None:
            exampleStyle = Parameters.get(model.getStr(self.tag+"example-style")) # no checking, but these should already have passed the ExampleBuilder
        self.structureAnalyzer.load(model)
        outExamples = []
        outPredictions = []
        for pred, conf, example in zip(predictions, confidences, examples):
            outExamples.append([example["id"], None, None, example["extra"]])
            outPredictions.append({"prediction":pred, "confidence":conf})
        return self.exampleWriter.write(outExamples, outPredictions, data, tag+self.tag+"pred.xml.gz", labelSet, parse, exampleStyle=exampleStyle, structureAnalyzer=self.structureAnalyzer)
    
    ###########################################################################
    # Example Generation
    ###########################################################################
        
    def processCorpus(self, input, examples, gold=None, parse=None, tokenization=None):
        self.exampleStats = ExampleStats()
    
        # Build examples
        self.exampleIndex = 0
        if type(input) in types.StringTypes:
            self.elementCounts = IXMLUtils.getElementCounts(input)
            self.progress = ProgressCounter(self.elementCounts.get("sentences"), "Build examples")
        
        inputIterator = getCorpusIterator(input, None, parse, tokenization, removeIntersentenceInteractions=True)            
        goldIterator = getCorpusIterator(gold, None, parse, tokenization, removeIntersentenceInteractions=True) if gold != None else []
        for inputSentences, goldSentences in itertools.izip_longest(inputIterator, goldIterator, fillvalue=None):
            assert inputSentences != None and (goldSentences != None or gold == None)
            self.processDocument(inputSentences, goldSentences, examples)
        self.progress.endUpdate()
        
        # Show statistics
        print >> sys.stderr, "Examples built:", self.exampleIndex
        if self.exampleStats.getExampleCount() > 0:
            self.exampleStats.printStats()
    
    def processDocument(self, sentences, goldSentences, examples):
        for i in range(len(sentences)):
            self.progress.update(1, "Building examples ("+sentences[i].sentence.get("id")+"): ")
            self.processSentence(sentences[i], examples, goldSentences[i] if goldSentences else None)
    
    def processSentence(self, sentence, examples, goldSentence=None):
        if sentence.sentenceGraph != None:
            self.buildExamplesFromGraph(sentence.sentenceGraph, examples, goldSentence.sentenceGraph if goldSentence != None else None)
    
    def addPathEmbedding(self, token1, token2, dirGraph, undirGraph, edgeCounts, features, embName="path"):
        if self.pathDepth <= 0:
            return

        if token1 == token2:
            keys = ["[d0]"] * self.pathDepth
        else:
            paths = undirGraph.getPaths(token1, token2)
            path = paths[0] if len(paths) > 0 else None
            if path != None and len(path) <= self.pathDepth + 1:
                #key = "d" + str(len(paths[0]) - 1)
                walks = dirGraph.getWalks(path)
                walk = walks[0]
                keys = [] #pattern = []
                for i in range(len(path)-1): # len(pathTokens) == len(walk)
                    edge = walk[i]
                    if edge[0] == path[i]:
                        keys.append(edge[2].get("type") + ">")
                    else:
                        assert edge[1] == path[i]
                        keys.append("<" + edge[2].get("type"))
                while len(keys) < self.pathDepth:
                    keys.append("[N/A]")
                #key = "|".join(pattern)
            elif edgeCounts[token2] > 0: #len(graph.getInEdges(token2) + graph.getOutEdges(token2)) > 0:
                keys = ["[dMax]"] * self.pathDepth
            else:
                keys = ["[unconnected]"] * self.pathDepth
        for i in range(self.pathDepth):
            features[embName + str(i)].append(self.embeddings[embName + str(i)].getIndex(keys[i], "[out]"))
    
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        raise NotImplementedError
    
    def showExample(self, example, showKeys=True):
        features = example["features"]
        featureGroups = sorted(features.keys())
        exampleLength = len(features[featureGroups[0]])
        print >> sys.stderr, example["id"], example["labels"]
        print >> sys.stderr, ["index"] + featureGroups
        for i in range(exampleLength):
            line = [i]
            for group in featureGroups:
                embeddingIndex = features[group][i]
                if group in self.embeddings and showKeys:
                    embeddingName = self.embeddings[group].getKey(embeddingIndex)
                line.append(embeddingName)
            print >> sys.stderr, line
    
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
        # Load embeddings
        if self.embeddings == None:
            self.embeddings = self.loadEmbeddings(model.get(self.tag + "embeddings.json", False, None))
        # Make example for all input files
        self.examples = {x:[] for x in setNames}
        for setName, data, gold in itertools.izip_longest(setNames, datas, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName #, "to file", output 
            self.processCorpus(data, self.examples[setName], gold, parse)          
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            modelChanged = True
        if saveIdsToModel:
            self.saveEmbeddings(self.embeddings, model.get(self.tag + "embeddings.json", True))
            modelChanged = True
        if self.styles.get("save"):
            for dataSet in setNames:
                examplePath = os.path.join(os.path.abspath(self.workDir), dataSet + "-examples.json")
                if not os.path.exists(os.path.dirname(examplePath)):
                    os.makedirs(os.path.dirname(examplePath))
                print >> sys.stderr, "Saving", dataSet, "examples to", examplePath
                with open(examplePath, "wt") as f:
                    json.dump(self.examples[dataSet], f, indent=2, sort_keys=True)
        if modelChanged:
            model.save()
    
    def padExamples(self, model, examples):
        if self.exampleLength == None or self.exampleLength <= 0:
            self.exampleLength = model.getStr(self.tag + "example-length", None, int)
        elif model.getStr(self.tag + "example-length", None, int) == None:
            print >> sys.stderr, "Defining example length as", self.exampleLength
            self.saveStr(self.tag + "example-length", str(self.exampleLength), model)
         
        print >> sys.stderr, "Padding examples, length: " + str(self.exampleLength)
        embNames = sorted(self.embeddings.keys())
        examples = list(itertools.chain.from_iterable([examples[x] for x in sorted(examples.keys())]))
        dims = set([len(x["features"][embNames[0]]) for x in examples])
        maxDim = max(dims)
        if self.exampleLength == None:
            print >> sys.stderr, "Defining example length as", maxDim
            self.exampleLength = maxDim
            self.saveStr(self.tag + "example-length", str(self.exampleLength), model)
        
        if len(dims) != 1 or maxDim != self.exampleLength:
            print >> sys.stderr, "Padding examples to", self.exampleLength, "from dimensions", dims
            if maxDim > self.exampleLength:
                raise Exception("Example too long")
            paddings = {x:[self.embeddings[x].getIndex("[pad]")] for x in embNames}
            for example in examples:
                features = example["features"]
                dim = len(features[embNames[0]])
                if dim < self.exampleLength:
                    for embName in embNames:
                        features[embName] += paddings[embName] * (self.exampleLength - dim)
        else:
            print >> sys.stderr, "No padding added, all examples have the length", self.exampleLength
            
    ###########################################################################
    # Embeddings
    ###########################################################################
    
    def initEmbeddings(self, datas, parse):
        print >> sys.stderr, "Initializing embeddings"
        self.embeddings = self.defineEmbeddings()
        self.initVocabularies(self.embeddings, datas, parse)
    
    def defineEmbeddings(self):
        raise NotImplementedError
    
    def saveEmbeddings(self, embeddings, outPath):
        print >> sys.stderr, "Saving embedding indices"
        with open(outPath, "wt") as f:
            json.dump([embeddings[x].serialize() for x in sorted(embeddings.keys())], f, indent=2, sort_keys=True)
    
    def loadEmbeddings(self, inPath):
        print >> sys.stderr, "Loading embedding indices from", inPath
        embeddings = {}
        with open(inPath, "rt") as f:
            for obj in json.load(f):
                emb = EmbeddingIndex().deserialize(obj)
                embeddings[emb.name] = emb
        print >> sys.stderr, [(embeddings[x].name, embeddings[x].getSize()) for x in sorted(embeddings.keys())]
        return embeddings
    
    def initVocabularies(self, embeddings, inputs, parseName):
        print >> sys.stderr, "Initializing vocabularies using parse", parseName
        embNames = sorted(embeddings.keys())
        for xml in inputs:
            print >> sys.stderr, "Initializing embedding vocabularies from", xml
            counts = defaultdict(int)
            for document in ETUtils.ETFromObj(xml).getiterator("document"):
                counts["document"] += 1
                for sentence in document.findall("sentence"):
                    counts["sentence"] += 1
                    parse = IXMLUtils.getParseElement(sentence, parseName)
                    if parse != None:
                        counts["parse"] += 1
                        tokenization = IXMLUtils.getTokenizationElement(sentence, parse.get("tokenizer"))
                        dependencies = [x for x in parse.findall("dependency")]
                        tokens = [x for x in tokenization.findall("token")]
                        for embName in embNames:
                            embeddings[embName].addToVocabulary(tokens, dependencies)
            print dict(counts), {x.name:len(x.embeddings) for x in embeddings.values()}
        for embName in embNames:
            if embeddings[embName].vocabularyType != None:
                embeddings[embName].locked = True
            if embeddings[embName].vocabularyType == "words":
                embeddings[embName].releaseWV()
    
    def defineModel(self, verbose=False):
        """
        Defines the Keras model and compiles it.
        """
        labelSet = set()
        for dataSet in ("train", "devel"):
            for example in self.examples[dataSet]:
                for label in example["labels"]:
                    labelSet.add(label)
        
        # The Embeddings
        embNames = sorted(self.embeddings.keys())
        for embName in embNames:
            self.embeddings[embName].makeLayers(self.exampleLength, embName, embName != "words")
        merged_features = merge([self.embeddings[x].embeddingLayer for x in embNames], mode='concat', name="merged_features")
        merged_features = Dropout(float(self.styles.get("do", 0.1)))(merged_features)
        
#         # Main network
        if self.styles.get("kernels") != "skip":
            convOutputs = []
            kernelSizes = [int(x) for x in self.styles.get("kernels", [1, 3, 5, 7])]
            numFilters = int(self.styles.get("nf", 32)) #32 #64
            for kernel in kernelSizes:
                subnet = Conv1D(numFilters, kernel, activation='relu', name='conv_' + str(kernel))(merged_features)
                #subnet = Conv1D(numFilters, kernel, activation='relu', name='conv2_' + str(kernel))(subnet)
                subnet = MaxPooling1D(pool_length=self.exampleLength - kernel + 1, name='maxpool_' + str(kernel))(subnet)
                #subnet = GlobalMaxPooling1D(name='maxpool_' + str(kernel))(subnet)
                subnet = Flatten(name='flat_' + str(kernel))(subnet)
                convOutputs.append(subnet)       
            layer = merge(convOutputs, mode='concat')
            layer = Dropout(float(self.styles.get("do", 0.1)))(layer)
        else:
            layer = Flatten()(merged_features)
        
        # Classification layers
        layer = Dense(int(self.styles.get("dense", 400)), activation='relu')(layer) #layer = Dense(800, activation='relu')(layer)
        layer = Dense(len(labelSet), activation='sigmoid')(layer)
        
        kerasModel = Model([self.embeddings[x].inputLayer for x in embNames], layer)
        
        learningRate = float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Using learning rate", learningRate
        optimizer = Adam(lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"] #, f1ScoreMetric]
        kerasModel.compile(optimizer=optimizer, loss="binary_crossentropy", metrics=metrics)
        
        if verbose:
            kerasModel.summary()
        return kerasModel
    
    ###########################################################################
    # Keras Model
    ###########################################################################
   
    def fitModel(self, verbose=True):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """
        labels, labelNames = self.vectorizeLabels(self.examples, ["train", "devel"])        
        print >> sys.stderr, "Labels:", labelNames
        labelWeights = {}
        for i in range(len(labelNames)):
            labelWeights[i] = 1.0 if labelNames[i] != "neg" else 0.001
        print >> sys.stderr, "Label weights:", labelWeights
        labelSet = IdSet(idDict={labelNames[i]:i for i in range(len(labelNames))})
        labelFileName = self.model.get(self.tag + "labels.ids", True)
        print >> sys.stderr, "Saving class names to", labelFileName
        labelSet.write(labelFileName)
        
        features = self.vectorizeFeatures(self.examples, ("train", "devel"))
        
        print >> sys.stderr, "Fitting model"
        patience = int(self.styles.get("patience", 10))
        replicates = int(self.styles.get("reps", 1))
        print >> sys.stderr, "Early stopping patience:", patience
        bestScore = [0.0, 0.0, 0.0, 0]
        modelScores = []
        repModelPath = self.tag + "current-model.hdf5" if replicates > 1 else self.tag + "model.hdf5"
        for i in range(replicates):
            print >> sys.stderr, "***", "Replicate", i + 1, "/", replicates, "***"
            es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
            modelPath = self.model.get(repModelPath, True) #self.workDir + self.tag + 'model.hdf5'
            cp_cb = ModelCheckpoint(filepath=modelPath, save_best_only=True, verbose=1)
            kerasModel = self.defineModel(verbose)
            kerasModel.fit(features["train"], labels["train"], #[sourceData], self.arrays["train"]["target"],
                epochs=100 if not "epochs" in self.styles else int(self.styles["epochs"]),
                batch_size=64,
                shuffle=True,
                validation_data=(features["devel"], labels["devel"]),
                class_weight=labelWeights,
                callbacks=[es_cb, cp_cb])
            print >> sys.stderr, "Predicting devel examples"
            _, _, scores = self.predict(labels["devel"], features["devel"], labelNames, modelPath)
            modelScores.append(scores)
            if replicates > 1:
                if scores["micro"][2] > bestScore[2]:
                    print >> sys.stderr, "New best replicate", scores["micro"]
                    bestScore = scores["micro"]
                    shutil.copy2(self.model.get(repModelPath, True), self.model.get(self.tag + "model.hdf5", True))
            else:
                bestScore = scores["micro"]
        if replicates > 1 and self.model.hasMember(repModelPath):
            os.remove(self.model.get(repModelPath))
        modelScores = [x["micro"][2] for x in modelScores]
        print >> sys.stderr, "Models:", json.dumps({"best":["%.4f" % x for x in bestScore[:3]], "mean":["%.4f" % numpy.mean(modelScores), "%.4f" % numpy.var(modelScores)], "replicates":["%.4f" % x for x in modelScores]}, sort_keys=True)
        
        self.model.save()
        self.examples = None
    
    def vectorizeLabels(self, examples, dataSets, labelNames=None):
        print >> sys.stderr, "Vectorizing labels"
        mlb = MultiLabelBinarizer(labelNames)
        labels = {}
        for dataSet in dataSets:
            labels[dataSet] = [x["labels"] for x in self.examples[dataSet]]
        if labelNames == None:
            mlb.fit_transform(chain.from_iterable([labels[x] for x in dataSets]))
        else:
            mlb.fit(None)
            assert [x for x in mlb.classes_] == labelNames, (mlb.classes_, labelNames)
        for dataSet in dataSets:
            labels[dataSet] = numpy.array(mlb.transform(labels[dataSet]))
        return labels, mlb.classes_
    
    def vectorizeFeatures(self, examples, dataSets):
        featureGroups = sorted(self.examples[dataSets[0]][0]["features"].keys())
        print >> sys.stderr, "Vectorizing features:", featureGroups
        features = {x:{} for x in dataSets}
        for featureGroup in featureGroups:
            for dataSet in dataSets:
                if self.exampleLength != None:
                    for example in self.examples[dataSet]:
                        fl = len(example["features"][featureGroup])
                        if len(example["features"][featureGroup]) != self.exampleLength:
                            raise Exception("Feature group '" + featureGroup + "' length differs from example length: " + str([fl, self.exampleLength, example["id"]]))
                features[dataSet][featureGroup] = numpy.array([x["features"][featureGroup] for x in self.examples[dataSet]])
            print >> sys.stderr, featureGroup, features[dataSets[0]][featureGroup].shape, features[dataSets[0]][featureGroup][0]
        return features
    
    def predict(self, labels, features, labelNames, kerasModel):
        if isinstance(kerasModel, basestring):
            kerasModel = load_model(kerasModel)
        confidences = kerasModel.predict(features, 64, 1)
        
        predictions = numpy.copy(confidences)
        for i in range(len(confidences)):
            for j in range(len(confidences[i])):
                predictions[i][j] = 1 if confidences[i][j] > 0.5 else 0
        print confidences[0], predictions[0], (confidences.shape, predictions.shape)
        
        scores = self.evaluate(labels, predictions, labelNames)
        return predictions, confidences, scores
    
    def evaluate(self, labels, predictions, labelNames):
        print "Evaluating, labels =", labelNames
        scores = {"labels":{}, "micro":None}
        scoreList = sklearn.metrics.precision_recall_fscore_support(labels, predictions, average=None)
        for i in range(len(labelNames)):
            scores["labels"][labelNames[i]] = (scoreList[0][i], scoreList[1][i], scoreList[2][i], scoreList[3][i])
            print labelNames[i], "prfs =", scores["labels"][labelNames[i]]
        scores["micro"] = sklearn.metrics.precision_recall_fscore_support(labels, predictions, average="micro")
        print "micro prfs = ", scores["micro"]
        if scores["micro"][2] != 0.0:
            print(classification_report(labels, predictions, target_names=labelNames))
        return scores
