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
from keras.layers.core import Dropout, Flatten, Activation
from keras import optimizers
#from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from keras.layers import merge
from itertools import chain
import sklearn.metrics
from sklearn.preprocessing.label import MultiLabelBinarizer
from sklearn.metrics.classification import classification_report
from keras.layers import Conv1D
from keras.layers.pooling import MaxPooling1D, GlobalMaxPool1D
from __builtin__ import isinstance
from collections import defaultdict
from sklearn.utils.class_weight import compute_class_weight
import Utils.Range as Range
import Utils.STFormat
import Utils.KerasUtils as KerasUtils
from keras.layers.normalization import BatchNormalization
import random

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
        self.cmode = None
        self.useSeparateGold = False
        self.defaultStyles = {}
        self.embeddings = None
        #KerasUtils.setRandomSeed(0)
    
    ###########################################################################
    # Main Pipeline Interface
    ###########################################################################
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None,
              workDir=None, testData=None, goldData=None, extraData=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        self.model = model
        assert model != None
        if self.state != self.STATE_COMPONENT_TRAIN:
            self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES", "MODEL"], fromStep, toStep)
        else:
            self.state = None
            self.enterState(self.STATE_COMPONENT_TRAIN, [self.STATE_COMPONENT_TRAIN])
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
        self.styles = Utils.Parameters.get(exampleStyle, self.defaultStyles, allowNew=True)
        self.saveStr(self.tag+"example-style", Utils.Parameters.toString(self.styles), self.model)
        self.definePathDepth()
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        exampleFiles = {"devel":self.workDir+self.tag+"opt-examples.json.gz", "train":self.workDir+self.tag+"train-examples.json.gz"}
        if self.state == self.STATE_COMPONENT_TRAIN or self.checkStep("EXAMPLES"): # Generate the adjacency matrices
            self.initEmbeddings([optData, trainData, testData] if testData != None else [optData, trainData], parse)
            datas = [optData, trainData]
            golds = []
            if self.useSeparateGold:
                golds = goldData if goldData != None else [optData, trainData]
            if extraData != None:
                for i in range(len(datas)):
                    datas[i] = (datas[i], extraData[i]) if extraData[i] != None else datas[i]
            examples = self.buildExamples(self.model, ["devel", "train"], datas, [exampleFiles["devel"], exampleFiles["train"]], golds, saveIdsToModel=True)
            self.defineClassificationMode(examples)
            self.saveLabels(examples, ["devel", "train"])
            self.saveStr(self.tag + "classification-mode", self.cmode, self.model)
            self.defineExampleLength(model, examples)
            self.padExamples(self.model, examples)
            self.saveEmbeddings(self.embeddings, self.model.get(self.tag + "embeddings.json", True))
            if self.exampleLength != None and self.model.getStr(self.tag + "example-length", None, int) == None:
                self.saveStr(self.tag + "example-length", str(self.exampleLength), self.model)
            self.model.save()
            #if "test" in self.examples: # Test examples are generated here only for initializing the embeddings
            #    del self.examples["test"]
        #print self.examples["devel"][0:2]
        self.showExample(examples["devel"][0])
        if self.state == self.STATE_COMPONENT_TRAIN or self.checkStep("MODEL"): # Define and train the Keras model
            labelNames = self.loadLabels(self.model)
            self.fitModel(examples, labelNames)
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
        if xml != None:
            if (validate):
                self.structureAnalyzer.load(model)
                self.structureAnalyzer.validate(xml)
                ETUtils.write(xml, output+"-pred.xml.gz")
            else:
                shutil.copy2(workOutputTag+self.tag+"pred.xml.gz", output+"-pred.xml.gz")
            EvaluateInteractionXML.run(self.evaluator, xml, data, parse)
            stParams = self.getBioNLPSharedTaskParams(self.bioNLPSTParams, model)
            if stParams.get("convert"): #self.useBioNLPSTFormat:
                extension = ".zip" if (stParams["convert"] == "zip") else ".tar.gz" 
                Utils.STFormat.ConvertXML.toSTFormat(xml, output+"-events" + extension, outputTag=stParams["a2Tag"], writeExtra=(stParams["scores"] == True))
                if stParams["evaluate"]: #self.stEvaluator != None:
                    if task == None: 
                        task = self.getStr(self.tag+"task", model)
                    self.stEvaluator.evaluate(output+"-events" + extension, task)
        self.deleteTempWorkDir()
        self.exitState()
    
    def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, goldData=None, parse=None, recallAdjust=None, compressExamples=True, exampleStyle=None, useExistingExamples=False):
        model = self.openModel(model, "r")
        if exampleStyle == None:
            exampleStyle = Parameters.get(model.getStr(self.tag+"example-style")) # no checking, but these should already have passed the ExampleBuilder
        self.styles = Utils.Parameters.get(exampleStyle, self.defaultStyles, allowNew=True)
        self.cmode = self.getStr(self.tag+"classification-mode", model)
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.definePathDepth()
        if not useExistingExamples:
            examples = self.buildExamples(model, ["classification"], [data], [exampleFileName], [goldData], parse=parse)
            self.padExamples(model, examples)
        if len(examples["classification"]) > 0:
            self.showExample(examples["classification"][0])
        else:
            print >> sys.stderr, "No examples to classify"
            return None
        #if classifierModel == None:
        #    classifierModel = model.get(self.tag + "model.hdf5")
        #labelSet = IdSet(filename = model.get(self.tag + "labels.ids", False), locked=True)
        #labelNames = [None] * len(labelSet.Ids)
        #for label in labelSet.Ids:
        #    labelNames[labelSet.Ids[label]] = label
        #print >> sys.stderr, "Classification labels", labelNames
        numEnsemble = int(exampleStyle.get("ens", 1))
        labelNames = self.loadLabels(model)
        labels = self.vectorizeLabels(examples, ["classification"], labelNames)
        features = self.vectorizeFeatures(examples, ["classification"])
        predictions, confidences, _ = self.predict(labels["classification"], features["classification"], labelNames, model, numEnsemble)
        self.structureAnalyzer.load(model)
        outExamples = []
        outPredictions = []
        for pred, conf, example in zip(predictions, confidences, examples["classification"]):
            outExamples.append([example["id"], None, None, example["extra"]])
            outPredictions.append({"prediction":pred, "confidence":conf})
        labelSet = IdSet(idDict={labelNames[i]:i for i in range(len(labelNames))})
        return self.exampleWriter.write(outExamples, outPredictions, data, tag+self.tag+"pred.xml.gz", labelSet, parse, exampleStyle=exampleStyle, structureAnalyzer=self.structureAnalyzer)
    
    ###########################################################################
    # Example Generation
    ###########################################################################
        
    def processCorpus(self, input, examples, gold=None, parse=None, tokenization=None):
        print >> sys.stderr, "[input, gold] =", [input, gold]
        self.exampleStats = ExampleStats()
    
        # Build examples
        self.exampleIndex = 0
        self.elementCounts = None
        if type(input) in types.StringTypes:
            self.elementCounts = IXMLUtils.getElementCounts(input)
        self.progress = ProgressCounter(self.elementCounts.get("sentences") if self.elementCounts != None else None, "Build examples")
        
        removeIntersentenceInteractions = True
        if "keep_intersentence" in self.styles and self.styles["keep_intersentence"]:
            print >> sys.stderr, "Keeping intersentence interactions for input corpus"
            removeIntersentenceInteractions = False
        removeGoldIntersentenceInteractions = True
        if gold != None and "keep_intersentence_gold" in self.styles and self.styles["keep_intersentence_gold"]:
            print >> sys.stderr, "Keeping intersentence interactions for gold corpus"
            removeGoldIntersentenceInteractions = False
        
        inputIterator = getCorpusIterator(input, None, parse, tokenization, removeIntersentenceInteractions=removeIntersentenceInteractions)            
        goldIterator = getCorpusIterator(gold, None, parse, tokenization, removeIntersentenceInteractions=removeGoldIntersentenceInteractions) if gold != None else []
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
            self.addFeature(embName + str(i), features, keys[i], "[out]")
    
    def definePathDepth(self):
        self.pathDepth = self.styles.get("path", "3")
        if isinstance(self.pathDepth, basestring):
            self.pathDepth = int(self.pathDepth)
        else:
            self.pathDepth = max([int(x) for x in self.pathDepth])
        print >> sys.stderr, "Path depth is", self.pathDepth
    
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
                if group in self.embeddingInputs and showKeys:
                    embeddingName = self.embeddingInputs[group].getKey(embeddingIndex)
                line.append(embeddingName)
            print >> sys.stderr, line
    
    ###########################################################################
    # Main Pipeline Steps
    ###########################################################################
    
    def buildExamples(self, model, setNames, datas, outputs, golds=[], saveIdsToModel=False, parse=None):
        """
        Runs the KerasExampleBuilder for the input XML files and saves the generated adjacency matrices
        into JSON files.
        """
        #if exampleStyle == None:
        #    exampleStyle = model.getStr(self.tag+"example-style")
        #self.styles = Utils.Parameters.get(exampleStyle, self.defaultStyles, allowNew=True)
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.skipLabels = []
        if self.styles.get("skip_labels"):
            self.skipLabels = self.styles.get("skip_labels")
            if isinstance(self.skipLabels, basestring):
                self.skipLabels = self.skipLabels.split(",")
            self.skipLabels = set(self.skipLabels)
            print >> sys.stderr, "Skipping labels", sorted(self.skipLabels)
        self.structureAnalyzer.load(model)
        modelChanged = False
        # Load embeddings
        if self.embeddings == None:
            self.embeddings = self.loadEmbeddings(model.get(self.tag + "embeddings.json", False, None))
            self.embeddingInputs = {}
            for name in self.embeddings.keys():
                for inputName in self.embeddings[name].inputNames:
                    self.embeddingInputs[inputName] = self.embeddings[name]
        # Make example for all input files
        examples = {x:[] for x in setNames}
        print >> sys.stderr, "Building examples with styles:", self.styles
        for setName, data, gold in itertools.izip_longest(setNames, datas, golds, fillvalue=None):
            print >> sys.stderr, "Example generation for set", setName #, "to file", output
            if not isinstance(data, (list, tuple)): data = [data]
            if not isinstance(gold, (list, tuple)): gold = [gold]
            for d, g in itertools.izip_longest(data, gold, fillvalue=None):
                if d != None:
                    self.processCorpus(d, examples[setName], g if g != None else d, parse)
        # Remove specific labels
                 
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
                    json.dump(examples[dataSet], f, indent=2, sort_keys=True)
        if modelChanged:
            model.save()
        return examples
    
    def defineExampleLength(self, model, exampleSets):
        print >> sys.stderr, "Defining example length"
        if self.exampleLength == None or self.exampleLength <= 0:
            embNames = sorted(self.embeddings.keys())
            examples = list(itertools.chain.from_iterable([exampleSets[x] for x in sorted(exampleSets.keys())]))
            # Get the dimensions of non-negative examples
            dims = set([len(x["features"][embNames[0]]) for x in examples if (len(x["labels"]) > 0 and x["labels"][0] != "neg")])
            maxDim = max(dims)
            assert maxDim > 0
            print >> sys.stderr, "Defining example length as", maxDim
            self.exampleLength = maxDim
        else:
            print >> sys.stderr, "Saving already defined example length", self.exampleLength
        self.saveStr(self.tag + "example-length", str(self.exampleLength), model)

    def padExamples(self, model, exampleSets):
        if self.exampleLength == None or self.exampleLength <= 0:
            self.exampleLength = model.getStr(self.tag + "example-length", None, int)
        if self.exampleLength == None or self.exampleLength <= 0:
            raise Exception("Example length not defined")
         
        print >> sys.stderr, "Padding examples to length: " + str(self.exampleLength)
        counts = defaultdict(int)
        embNames = sorted(self.embeddingInputs.keys())
        paddings = {x:[self.embeddingInputs[x].getIndex("[pad]")] for x in embNames}
        for setName in sorted(exampleSets.keys()):
            examples = []
            for example in exampleSets[setName]:
                features = example["features"]
                dim = len(features[embNames[0]])
                if dim < self.exampleLength:
                    for embName in embNames:
                        features[embName] += paddings[embName] * (self.exampleLength - dim)
                if dim > self.exampleLength:
                    assert len(example["labels"]) == 0 or example["labels"][0] == "neg", example
                    counts["removed-neg-from-" + setName] += 1
                else:
                    counts["examples-" + setName] += 1
                    examples.append(example)
            exampleSets[setName] = examples
        print >> sys.stderr, dict(counts)
    
    def getTokenFeatures(self, sentenceGraph):
        # Pre-generate features for all tokens in the sentence
        tokenElements = sorted([(Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in sentenceGraph.tokens])
        tokens = []
        wordEmbeddings = sorted([x for x in self.embeddings.keys() if self.embeddings[x].wvPath != None])
        for i in range(len(tokenElements)):
            element = tokenElements[i][1]
            token = {"index":i, "element":element, "charOffset":tokenElements[i][0]}
            for wordEmbedding in wordEmbeddings:
                token[wordEmbedding] = self.embeddings[wordEmbedding].getIndex(element.get("text").lower(), "[out]")
            if "POS" in self.embeddings:
                token["POS"] = self.embeddings["POS"].getIndex(element.get("POS"), "[out]")
            if "head_score" in self.embeddings:
                token["head_score"] = self.embeddings["head_score"].getIndex(element.get("headScore"), "[out]")
            entityLabels = "---".join(sorted(set([x.get("type") for x in sentenceGraph.tokenIsEntityHead[sentenceGraph.tokens[i]]])))
            if "entities" in self.embeddings:
                token["entities"] = self.embeddings["entities"].getIndex(entityLabels if entityLabels != "" else "[N/A]", "[out]")         
            if "named_entities" in self.embeddings:
                token["named_entities"] = self.embeddings["named_entities"].getIndex("1" if (sentenceGraph.tokenIsEntityHead[element] and sentenceGraph.tokenIsName[element]) else "0")
            tokens.append(token)
        tokenMap = {tokenElements[i][1]:tokens[i] for i in range(len(tokenElements))}
        return tokens, tokenMap
    
    def saveLabels(self, examples, dataSetNames):
        labels = set()
        for dataSet in examples:
            for example in examples[dataSet]:
                for label in example["labels"]:
                    labels.add(label)
        labels = sorted(labels)
        assert self.cmode != None
        if self.cmode == "multiclass" and "neg" not in labels:
            labels = ["neg"] + labels
        #labels = {i:labels[i] for i in range(len(labels))}
        print >> sys.stderr, "Saving labels", labels
        with open(self.model.get(self.tag + "labels.json", True), "wt") as f:
            json.dump(labels, f, indent=2, sort_keys=True)
    
    def loadLabels(self, model):
        with open(model.get(self.tag + "labels.json"), "rt") as f:
            return json.load(f)
            
    ###########################################################################
    # Embeddings
    ###########################################################################
    
    def getPositionName(self, index):
        return str(index)
#         absIndex = abs(index)
#         if absIndex <= 10:
#             return str(index)
#         elif absIndex <= 20:
#             return "10+" if index > 0 else "-10+"
#         else:
#             return "20+" if index > 0 else "-20+"
    
    def addIndex(self, group, features, index):
        if group in self.embeddingInputs:
            features[group].append(index)
    
    def addFeature(self, group, features, key, default=None):
        if group in self.embeddingInputs:
            features[group].append(self.embeddingInputs[group].getIndex(key, default))
    
    def initEmbeddings(self, datas, parse):
        print >> sys.stderr, "Initializing embeddings"
        self.embeddings = {}
        self.embeddingInputs = {}
        self.skipGroups = self.styles.get("skip", None)
        if isinstance(self.skipGroups, basestring):
            self.skipGroups = self.skipGroups.split(",")
        self.limitGroups = self.styles.get("limit", None)
        if isinstance(self.limitGroups, basestring):
            self.limitGroups = self.skipGroups.split(",")
        self.defineFeatureGroups()
        self.initVocabularies(self.embeddings, datas, parse)
    
    def defineFeatureGroups(self):
        raise NotImplementedError
    
    def defineEmbedding(self, name, dim="AUTO", wvPath=None, wvMem=None, wvMap=None, initVectors="AUTO", vocabularyType="AUTO", inputNames=None):
        assert name not in self.embeddings
        if self.limitGroups != None and name not in self.limitGroups:
            print >> sys.stderr, "Limits: skipping feature group", name, self.limitGroups
            return
        if self.skipGroups != None and name in self.skipGroups:
            print >> sys.stderr, "Skip: skipping feature group", name, self.skipGroups
            return
        if initVectors == "AUTO":
            initVectors = ["[out]", "[pad]"]
        if dim == "AUTO":
            dim = int(self.styles.get("de", 8)) if wvPath == None else None #8 #32
        self.embeddings[name] = EmbeddingIndex(name, dim, wvPath, wvMem, wvMap, initVectors, vocabularyType, inputNames=inputNames)
        for inputName in self.embeddings[name].inputNames:
            self.embeddingInputs[inputName] = self.embeddings[name]
        
    def defineWordEmbeddings(self, wordVectors=None, wv_mem=None, wv_map=None):
        if wordVectors == None:
            wordVectors = self.styles.get("wv", Settings.W2VFILE)
        if wv_mem == None:
            wv_mem = int(self.styles.get("wv_mem", 100000))
        if wv_map == None:
            wv_map = int(self.styles.get("wv_map", 10000000))
        if wordVectors == "skip":
            wordVectors = []
        elif isinstance(wordVectors, basestring):
            wordVectors = wordVectors.split(",")
        wvCount = 0
        for wv in wordVectors:
            if os.path.exists(wv):
                embName = "words" + (str(wvCount) if len(wordVectors) > 1 else "")
                embPath = wv
            else:
                embName = wv
                embPath = Settings.W2V[wv]
            assert os.path.exists(embPath), (wv, embName, embPath)
            self.defineEmbedding(embName, None, embPath, wv_mem, wv_map)
            wvCount += 1
    
    def saveEmbeddings(self, embeddings, outPath):
        print >> sys.stderr, "Saving embedding indices"
        for embedding in self.embeddings.values():
            embedding.locked = "all"
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
                        if tokenization != None:
                            counts["tokenization"] += 1
                            dependencies = [x for x in parse.findall("dependency")]
                            tokens = [x for x in tokenization.findall("token")]
                            for embName in embNames:
                                embeddings[embName].addToVocabulary(tokens, dependencies)
            print dict(counts), {x.name:len(x.embeddings) for x in embeddings.values()}
        for embName in embNames:
            if embeddings[embName].vocabularyType != None:
                embeddings[embName].locked = "content"
            if embeddings[embName].vocabularyType == "words":
                embeddings[embName].releaseWV()
    
    def castValue(self, value):
        assert isinstance(value, basestring)
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            return float(value)
    
    def getParameter(self, name, styles, default, parameters=None, numRandom=None):
        if name in styles:
            if not isinstance(styles[name], basestring):
                value = [self.castValue(x) for x in styles[name]]
                if numRandom != None:
                    assert numRandom >= 1
                    value = random.choice(value) if numRandom == 1 else random.sample(value, numRandom)
            else:
                value = self.castValue(styles[name])
        else:
            value = default
        if parameters != None:
            parameters[name] = value
        return value
    
    def defineModel(self, dimLabels, parameters=None, verbose=False):
        """
        Defines the Keras model and compiles it.
        """
#         labelSet = set()
#         for dataSet in ("train", "devel"):
#             for example in self.examples[dataSet]:
#                 for label in example["labels"]:
#                     labelSet.add(label)
#         assert self.cmode != None
#         if self.cmode == "multiclass" and "neg" not in labelSet:
#             labelSet.add("neg")
        #labelNames = self.loadLabels()
        
        dropout = self.getParameter("do", self.styles, 0.1, parameters, 1) #float(self.styles.get("do", 0.1))
        #kernel_initializer = self.styles.get("init", "glorot_uniform")
        
        # The Embeddings
        embNames = sorted(self.embeddings.keys())
        skipInputs = []
        maxPathDepth = self.getParameter("path", self.styles, self.pathDepth, parameters, 1)
        skipInputs += ["path" + str(i) for i in range(self.pathDepth) if i >= maxPathDepth]
        skipInputs += ["path1_" + str(i) for i in range(self.pathDepth) if i >= maxPathDepth]
        skipInputs += ["path2_" + str(i) for i in range(self.pathDepth) if i >= maxPathDepth]
        #includedEmbeddings = [x for x in embNames if x not in set(skipEmbeddings)]
        for embName in embNames:
            self.embeddings[embName].makeLayers(self.exampleLength, embName, True if "wv_learn" in self.styles else "AUTO", verbose=verbose, skipInputs=skipInputs)
        merged_features = merge(sum([self.embeddings[x].embeddingLayers for x in embNames], []), mode='concat', name="merged_features")
        if dropout > 0.0:
            merged_features = Dropout(dropout)(merged_features)
        
        # Main network
        kernels = self.getParameter("kernels", self.styles, [1, 3, 5, 7], parameters)
        if kernels != "skip":
            convOutputs = []
            convAct = self.getParameter("cact", self.styles, "relu", parameters, 1) #self.styles.get("cact", "relu")
            numFilters = self.getParameter("nf", self.styles, 32, parameters, 1) #int(self.styles.get("nf", 32)) #32 #64
            for kernel in kernels:
                subnet = Conv1D(numFilters, kernel, activation=convAct, name='conv_' + str(kernel))(merged_features)
                #subnet = Conv1D(numFilters, kernel, activation='relu', name='conv2_' + str(kernel))(subnet)
                #subnet = MaxPooling1D(pool_length=self.exampleLength - kernel + 1, name='maxpool_' + str(kernel))(subnet)
                subnet = GlobalMaxPool1D(name='maxpool_' + str(kernel))(subnet)
                #subnet = Flatten(name='flat_' + str(kernel))(subnet)
                convOutputs.append(subnet)       
            layer = merge(convOutputs, mode='concat')
            #layer = BatchNormalization()(layer)
            #layer = Activation(convAct)(layer)
            if dropout > 0.0:
                layer = Dropout(dropout)(layer)
        else:
            layer = Flatten()(merged_features)
        
        # Classification layers
        denseSize = self.getParameter("dense", self.styles, 400, parameters, 1)
        #denseSizes = self.styles.get("dense", "400")
        #if isinstance(denseSizes, basestring):
        #    denseSizes = denseSizes.split(",")
        #denseSizes = [int(x) for x in denseSizes]
        #for denseSize in denseSizes:
        if denseSize > 0:
            layer = Dense(denseSize, activation='relu')(layer) #layer = Dense(800, activation='relu')(layer)
        assert self.cmode in ("binary", "multiclass", "multilabel")
        if self.cmode in ("binary", "multilabel"):
            layer = Dense(dimLabels, activation='sigmoid')(layer)
        else:
            layer = Dense(dimLabels, activation='softmax')(layer)
        
        kerasModel = Model(sum([self.embeddings[x].inputLayers for x in embNames], []), layer)
        
        learningRate = self.getParameter("lr", self.styles, 0.001, parameters, 1) #float(self.styles.get("lr", 0.001))
        optName = self.getParameter("opt", self.styles, "adam", parameters, 1) #self.styles.get("opt", "adam")
        print >> sys.stderr, "Using learning rate", learningRate, "with optimizer", optName
        optDict = {"adam":optimizers.Adam, "nadam":optimizers.Nadam, "sgd":optimizers.SGD, "adadelta":optimizers.Adadelta}
        optimizer = optDict[optName](lr=learningRate)
        
        print >> sys.stderr, "Compiling model"
        metrics = ["accuracy"] #, f1ScoreMetric]
        if self.cmode in ("binary", "multilabel"):
            loss = "binary_crossentropy"
        else:
            loss = "categorical_crossentropy"
        kerasModel.compile(optimizer=optimizer, loss=loss, metrics=metrics)
        
        if verbose:
            kerasModel.summary()
        return kerasModel
    
    ###########################################################################
    # Keras Model
    ###########################################################################
    
    def defineClassificationMode(self, examples):
        if self.cmode == None:
            self.cmode = self.styles.get("cm", "auto")
            if self.cmode == "auto":
                labelSet = set()
                maxlabels = 0
                for dataSet in ("train", "devel"):
                    for example in examples[dataSet]:
                        maxlabels = max(maxlabels, len(example["labels"]))
                        for label in example["labels"]:
                            labelSet.add(label)
                if len(labelSet) == 1:
                    self.cmode = "binary"
                elif maxlabels > 1:
                    self.cmode = "multilabel"
                else:
                    self.cmode = "multilabel" #"multiclass"
            #self.cmode = "multilabel"         
        assert self.cmode in ("binary", "multiclass", "multilabel"), self.cmode
        print >> sys.stderr, "Using classification mode", self.cmode
    
    def getLabelCounts(self, labels, labelNames):
        counts = {x:0 for x in range(len(labelNames))}
        for dataSet in labels:
            for labelSet in labels[dataSet]:
                for i in range(len(labelSet)):
                    if labelSet[i] > 0:
                        counts[i] += 1
        return counts
    
    def getBalancedWeights(self, labels, labelNames):
        n_samples = sum([len(x) for x in labels.values()])
        counts = self.getLabelCounts(labels, labelNames)
        n_labels = len(labelNames)
        return {i:n_samples / (n_labels * counts[i]) for i in range(n_labels)}

    def getProportionalWeights(self, labels, labelNames):
        counts = self.getLabelCounts(labels, labelNames)
        n_classes = len(labelNames)
        weights = {}
        minCount = min(counts.values())
        for i in range(n_classes):
            weights[i] = counts[i] / minCount
        return weights
    
    def getLabelWeights(self, labels, labelNames):
        print >> sys.stderr, "Labels:", labelNames
        labelWeights = None
        weightStyle = self.styles.get("weights")
        if weightStyle == None:
            pass
        elif weightStyle == "equal":
            if len(labelNames) > 1:
                labelWeights = {}
                for i in range(len(labelNames)):
                    labelWeights[i] = 1.0 if labelNames[i] != "neg" else 0.001
        elif weightStyle == "balanced":
            labelWeights = self.getBalancedWeights(labels, labelNames) #dict(enumerate(compute_class_weight("balanced", [x for x in range(len(labelNames))], numpy.concatenate([labels["train"], labels["devel"]], axis=0))))
        elif weightStyle == "proportional":
            labelWeights = self.getProportionalWeights(labels, labelNames)
        else:
            raise Exception("Unknown weight style '" + str(weightStyle) + "'")
        print >> sys.stderr, "Label weights:", weightStyle, labelWeights
        return labelWeights
    
    def getVectorized(self, examples, labelNames, setNames, trainSize=0.0):
        assert self.cmode != None
        if trainSize > 0.0:
            print >> sys.stderr, "Redividing sets, train size =", trainSize
            docSets = {}
            for dataSet in setNames:
                for example in examples[dataSet]:
                    if example["doc"] not in docSets:
                        docSets[example["doc"]] = []
                    docSets[example["doc"]].append(example)
            docIds = sorted(docSets.keys())
            random.shuffle(docIds)
            cutoff = int(trainSize * len(docIds))
            examples = {"train":list(itertools.chain.from_iterable([docSets[x] for x in docIds[:cutoff]])), 
                        "devel":list(itertools.chain.from_iterable([docSets[x] for x in docIds[cutoff:]]))}
        print >> sys.stderr, "Vectorizing examples", {x:len(examples[x]) for x in setNames}
        labels = self.vectorizeLabels(examples, ("train", "devel"), labelNames)
        labelWeights = self.getLabelWeights(labels, labelNames)      
        features = self.vectorizeFeatures(examples, ("train", "devel"))
        return features, labels, labelWeights
   
    def fitModel(self, examples, labelNames, verbose=True):
        """
        Fits the compiled Keras model to the adjacency matrix examples. The model is trained on the
        train set, validated on the devel set and finally the devel set is predicted using the model.
        """
        print >> sys.stderr, "Fitting model"
        #self.defineClassificationMode(self.examples)
#         assert self.cmode != None
#         labels = self.vectorizeLabels(self.examples, ["train", "devel"], labelNames)
#         labelWeights = self.getLabelWeights(labels, labelNames)      
#         
#         #labelSet = IdSet(idDict={labelNames[i]:i for i in range(len(labelNames))})
#         #labelFileName = self.model.get(self.tag + "labels.ids", True)
#         #print >> sys.stderr, "Saving class names to", labelFileName
#         #labelSet.write(labelFileName)   
#         
#         features = self.vectorizeFeatures(self.examples, ("train", "devel"))
        trainSize = float(self.styles.get("train", 0.0))
        if trainSize == 0.0:
            features, labels, labelWeights = self.getVectorized(examples, labelNames, ("train", "devel"))
        patience = int(self.styles.get("patience", 10))
        batchSize = int(self.styles.get("batch", 64))
        numModels = int(self.styles.get("mods", 1))
        numEnsemble = int(self.styles.get("ens", 1))
        #learningRate = float(self.styles.get("lr", 0.001))
        print >> sys.stderr, "Early stopping patience:", patience
        #bestScore = [0.0, 0.0, 0.0, 0]
        models = [] #modelScores = []
        for i in range(numModels):
            print >> sys.stderr, "***", "Model", i + 1, "/", numModels, "***"
            parameters = {}
            if trainSize > 0.0:
                features, labels, labelWeights = self.getVectorized(examples, labelNames, ("train", "devel"), trainSize)
                #setIndices = self.getDocSets(self.examples, ("train", "devel"), ("train", "devel"), trainSize)
                #currentFeatures = self.divideData(features, ("train", "devel"), setIndices)
                #currentLabels = self.divideData(labels, ("train", "devel"), setIndices)
                #print >> sys.stderr, "Redivided sets", {x:len(setIndices[x]) for x in setIndices}, {x:currentFeatures[x].shape for x in currentFeatures}, {x:currentLabels[x].shape for x in currentLabels}
            #else:
            #    currentFeatures = features
            #    currentLabels = labels
            #KerasUtils.setRandomSeed(i)
            es_cb = EarlyStopping(monitor='val_loss', patience=patience, verbose=1)
            modelFileName = self.tag + "model-" + str(i + 1) + ".hdf5"
            modelPath = self.model.get(modelFileName, True) #self.workDir + self.tag + 'model.hdf5'
            cp_cb = ModelCheckpoint(filepath=modelPath, save_best_only=True, verbose=1)
            #lr_cb = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=int(0.5 * patience), min_lr=0.01 * learningRate)
            kerasModel = self.defineModel(len(labelNames), parameters, verbose=True)
            print >> sys.stderr, "Model parameters:", parameters
            kerasModel.fit(features["train"], labels["train"], #[sourceData], self.arrays["train"]["target"],
                epochs=100 if not "epochs" in self.styles else int(self.styles["epochs"]),
                batch_size=batchSize,
                shuffle=True,
                validation_data=(features["devel"], labels["devel"]),
                class_weight=labelWeights,
                callbacks=[es_cb, cp_cb])
            print >> sys.stderr, "Predicting devel examples"
            _, _, scores = self.predictWithModel(labels["devel"], features["devel"], labelNames, modelPath, True)
            currentModel = {"filename":modelFileName, "scores":scores, "parameters":parameters, "index":i}
            models.append(currentModel)
            models.sort(reverse=True, key=lambda k: k["scores"]["micro"][2])
            if currentModel == models[0]:
                print >> sys.stderr, "New best model", scores["micro"]
            for j in range(len(models)):
                if j >= numEnsemble and models[j]["filename"] != None:
                    print >> sys.stderr, "Removing model", models[j]["filename"]
                    os.remove(self.model.get(models[j]["filename"]))
                    models[j]["filename"] = None
            # Save the updated model list after each new model
            with open(self.model.get(self.tag + "models.json", True), "wt") as f:
                json.dump(models, f, indent=2, sort_keys=True)
        modelScores = [x["scores"]["micro"][2] for x in sorted(models, key=lambda k: k["index"])]
        print >> sys.stderr, "Models:", json.dumps({"best":["%.4f" % x for x in models[0]["scores"]["micro"][:3]], "mean":["%.4f" % numpy.mean(modelScores), "%.4f" % numpy.var(modelScores)], "replicates":["%.4f" % x for x in modelScores]}, sort_keys=True)
        
        self.model.save()
        #self.examples = None
    
    def vectorizeLabels(self, examples, dataSets, labelNames):
        print >> sys.stderr, "Vectorizing labels", labelNames
        assert self.cmode != None
        #if labelNames != None and self.cmode == "multiclass" and "neg" not in labelNames:
        #    labelNames = ["neg"] + labelNames
        #labelNames = self.loadLabels()
        mlb = MultiLabelBinarizer(labelNames)
        labels = {}
        for dataSet in dataSets:
            if self.cmode == "multiclass":
                labels[dataSet] = [x["labels"] if len(x["labels"]) > 0 else ["neg"] for x in examples[dataSet]]
            else:
                labels[dataSet] = [x["labels"] for x in examples[dataSet]]
        #if labelNames == None:
        #    mlb.fit_transform(chain.from_iterable([labels[x] for x in dataSets]))
        #else:
        mlb.fit(None)
        assert [x for x in mlb.classes_] == labelNames, (mlb.classes_, labelNames)
        for dataSet in dataSets:
            labels[dataSet] = numpy.array(mlb.transform(labels[dataSet]))
        return labels #, labelNames
    
    def vectorizeFeatures(self, examples, dataSets):
        featureGroups = sorted(examples[dataSets[0]][0]["features"].keys())
        print >> sys.stderr, "Vectorizing features:", featureGroups
        features = {x:{} for x in dataSets}
        for featureGroup in featureGroups:
            for dataSet in dataSets:
                if self.exampleLength != None:
                    for example in examples[dataSet]:
                        fl = len(example["features"][featureGroup])
                        if len(example["features"][featureGroup]) != self.exampleLength:
                            raise Exception("Feature group '" + featureGroup + "' length differs from example length: " + str([fl, self.exampleLength, example["id"]]))
                features[dataSet][featureGroup] = numpy.array([x["features"][featureGroup] for x in examples[dataSet]])
            print >> sys.stderr, featureGroup, features[dataSets[0]][featureGroup].shape, features[dataSets[0]][featureGroup][0]
        return features
    
#     def getDocSets(self, examples, dataSets, newSets, cutoff):
#         examples = []
#         docSets = {}
#         for dataSet in dataSets:
#             for example in self.examples[dataSet]:
#                 examples.append(example)
#                 if example["doc"] not in docSets:
#                     docSets[example["doc"]] = "train" if random.random() < cutoff else "devel"
#         setIndices = {"train":[], "devel":[]}
#         for i in range(len(examples)):
#             setIndices[docSets[example["doc"]]].append(i)
#         return setIndices
#     
#     def divideData(self, arrayBySet, dataSets, setIndices):
#         print arrayBySet
#         catenated = numpy.concatenate([arrayBySet[x] for x in dataSets])
#         return {catenated.take(setIndices[x], axis=0) for x in dataSets}
    
    def predict(self, labels, features, labelNames, model, numEnsemble=1, evalAll=True):
        with open(model.get(self.tag + "models.json"), "rt") as f:
            models = json.load(f)
        confidences = numpy.zeros((len(labels), len(labelNames)))
        for modelIndex in range(len(models)):
            if modelIndex >= numEnsemble:
                break
            print >> sys.stderr, "Predicting with model", modelIndex + 1, models[modelIndex]["filename"]
            kerasModelPath = model.get(models[modelIndex]["filename"])
            modelConfidences, _, _ = self.predictWithModel(labels, features, labelNames, kerasModelPath)
            confidences = confidences + modelConfidences #numpy.sum([confidences, modelConfidences], axis=0)
            if evalAll and modelIndex < numEnsemble - 1:
                print >> sys.stderr, "Results for ensemble size", modelIndex + 1
                self.getPredictions(confidences / float(modelIndex + 1), labels, labelNames)
        print >> sys.stderr, "*****", "Results for ensemble, size =", numEnsemble, "*****"
        confidences = confidences / float(numEnsemble)
        predictions, scores = self.getPredictions(confidences, labels, labelNames)
        #print >> sys.stderr, confidences[0], predictions[0], (confidences.shape, predictions.shape)
        return predictions, confidences, scores
    
    def predictWithModel(self, labels, features, labelNames, kerasModelPath, evaluation=False):
        kerasModel = load_model(kerasModelPath)
        confidences = kerasModel.predict(features, 64, 1)
        print >> sys.stderr, ""
        predictions, scores = None, None
        if evaluation:
            predictions, scores = self.getPredictions(confidences, labels, labelNames)
        return confidences, predictions, scores
    
    def getPredictions(self, confidences, labels, labelNames):
        predictions = numpy.copy(confidences)
        if self.cmode == "multiclass":
            for i in range(len(confidences)):
                maxIndex = numpy.argmax(confidences[i])
                for j in range(len(confidences[i])):
                    predictions[i][j] = 1 if j == maxIndex else 0
            scores = self.evaluate([numpy.argmax(x) for x in labels], [numpy.argmax(x) for x in predictions], labelNames) 
        else:
            for i in range(len(confidences)):
                for j in range(len(confidences[i])):
                    predictions[i][j] = 1 if confidences[i][j] > 0.5 else 0
            scores = self.evaluate(labels, predictions, labelNames)
        return predictions, scores
    
    def evaluate(self, labels, predictions, labelNames):
        print "Evaluating, labels =", labelNames
        labelIndices = [i for i in range(len(labelNames))]
        scores = {"labels":{}, "micro":None}
        scoreList = sklearn.metrics.precision_recall_fscore_support(labels, predictions, labels=labelIndices, average=None)
        for i in range(len(labelNames)):
            scores["labels"][labelNames[i]] = (scoreList[0][i], scoreList[1][i], scoreList[2][i], scoreList[3][i])
            print >> sys.stderr, labelNames[i], "prfs =", scores["labels"][labelNames[i]]
        scores["micro-all"] = sklearn.metrics.precision_recall_fscore_support(labels, predictions, average="micro")
        if "neg" in labelNames: #[labelNames[i] for i in range(len(labelNames))]:
            posLabelIndices = [i for i in range(len(labelNames)) if labelNames[i] != "neg"]
            scores["micro"] = sklearn.metrics.precision_recall_fscore_support(labels, predictions, labels=posLabelIndices, average="micro")
            #print "positive labels", posLabelIndices, scores["micro"]
        else:
            scores["micro"] = scores["micro-all"]
        if scores["micro"] != scores["micro-all"]:
            print >> sys.stderr, "all labels micro prfs = ", scores["micro-all"]
        print >> sys.stderr, "micro prfs = ", scores["micro"]
        if scores["micro"][2] != 0.0 and len(labelNames) > 1:
            print >> sys.stderr, classification_report(labels, predictions, target_names=labelNames)
        return scores
