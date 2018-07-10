import sys, os
import numpy
from Utils.Libraries.wvlib_light.lwvlib import WV
from keras.layers.embeddings import Embedding
from keras.layers import Input
import Utils.ElementTreeUtils as ETUtils

def normalized(a, axis=-1, order=2):
    l2 = numpy.atleast_1d(numpy.linalg.norm(a, order, axis))
    l2[l2==0] = 1
    return a / numpy.expand_dims(l2, axis)

def getRandomVector(dim, nor=False):
    vector = numpy.random.uniform(-1.0, 1.0, dim)
    if nor:
        vector = normalized(vector)
    return vector

class EmbeddingIndex():
    def __init__(self, name=None, dimVector=None, wordVectorPath=None, wvMem=100000, wvMap=10000000, keys=None, vocabularyType="AUTO", inputNames=None):
        self._reset(name, dimVector, wordVectorPath, wvMem, wvMap, keys, vocabularyType, inputNames=inputNames)
    
    def _reset(self, name, dimVector=None, wvPath=None, wvMem=100000, wvMap=10000000, keys=None, vocabularyType="AUTO", inputNames=None, embeddingIndex=None, locked=None):
        self.name = name
        self.inputNames = inputNames if inputNames != None else [name]
        self.embeddings = [] if embeddingIndex == None else None
        self.embeddingIndex = {} if embeddingIndex == None else embeddingIndex
        self.keyByIndex = {} if embeddingIndex == None else {embeddingIndex[x]:x for x in embeddingIndex.keys()}
        self.vocabularyType = vocabularyType
        if self.vocabularyType == "AUTO":
            self.vocabularyType = "words" if wvPath != None else None
        assert locked in (None, "all", "content")
        self.locked = locked
        self.wvPath = wvPath
        self.wvMem = wvMem
        self.wvMap = wvMap
        self.wv = None
        if self.wvPath != None and self.locked == None:
            print >> sys.stderr, "Loading word vectors", (wvMem, wvMap), "from", self.wvPath
            self.wv = WV.load(self.wvPath, wvMem, wvMap)
            assert dimVector == None or dimVector == self.wv.size
            self.dimVector = self.wv.size
        else:
            self.dimVector = dimVector if dimVector != None else 32
        self.initialKeys = [] if keys == None else keys
        #self.initialKeysInitialized = False
        for key in self.initialKeys:
            self._addEmbedding(key, numpy.zeros(self.dimVector)) #getRandomVector(self.dimVector)) # numpy.ones(self.dimVector)) #numpy.zeros(self.dimVector))
    
    def getSize(self):
        return len(self.embeddingIndex)
    
    def serialize(self):
        serialized = {"name":self.name, "inputNames":self.inputNames, "dimVector":self.dimVector, "index":self.embeddingIndex, "vocabularyType":self.vocabularyType, "locked":self.locked}
        if self.wvPath != None:
            serialized.update({"wvPath":self.wvPath, "wvMem":self.wvMem, "wvMap":self.wvMap})
        return serialized
    
    def deserialize(self, obj):
        self._reset(obj["name"], obj.get("dimVector"), obj.get("wvPath"), obj.get("wvMem"), obj.get("wvMap"), None, obj.get("vocabularyType"), obj.get("inputNames"), obj.get("index"), obj.get("locked"))
        return self
    
    def releaseWV(self):
        self.wv = None
    
    def _addEmbedding(self, key, vector):
        index = len(self.embeddings)
        assert key not in self.embeddingIndex
        assert index not in self.keyByIndex
        self.embeddingIndex[key] = len(self.embeddings)
        self.keyByIndex[index] = key
        self.embeddings.append(vector)
    
    def getKey(self, index):
        assert index in self.keyByIndex, (index, self.name, len(self.embeddingIndex), len(self.keyByIndex), len(self.embeddings))
        return self.keyByIndex[index]
    
    def getIndex(self, key, default=None, special=False):
        assert isinstance(key, basestring), key
        if key not in self.embeddingIndex and self.embeddings != None:
            if self.wvPath != None and not special:
                vector = self.wv.w_to_normv(key) if self.wv != None else None
            else:
                vector = numpy.ones(self.dimVector) #getRandomVector(self.dimVector) #numpy.ones(self.dimVector) #normalized(numpy.random.uniform(-1.0, 1.0, self.dimVector)))
            if vector is not None:
                if self.locked == "all":
                    #raise Exception("Cannot expand locked vocabulary with key '" + key + "' for embedding '" + self.name + "'")
                    print >> sys.stderr, "Tried to expand locked vocabulary with key", key
                elif self.locked == "content" and (key[0] != "[" or key[-1] != "]"):
                    #raise Exception("Cannot expand locked vocabulary with content key '" + key + "' for embedding '" + self.name + "'")
                    print >> sys.stderr, "Tried to expand locked vocabulary with content key", key
                else:
                    self._addEmbedding(key, vector)
        return self.embeddingIndex[key] if key in self.embeddingIndex else self.embeddingIndex[default]
    
    def addToVocabulary(self, tokens, dependencies):
        if self.vocabularyType == None:
            return
        if self.vocabularyType == "words":
            for token in tokens:
                self.getIndex(token.get("text").lower(), "[out]")
        elif self.vocabularyType == "POS":
            for token in tokens:
                self.getIndex(token.get("POS"))
        elif self.vocabularyType == "head_score":
            for token in tokens:
                self.getIndex(token.get("headScore"))
        elif self.vocabularyType == "directed_dependencies":
            for dependency in dependencies:
                self.getIndex("<" + dependency.get("type"))
                self.getIndex(dependency.get("type") + ">")
        else:
            raise Exception("Unknown vocabulary type '" + str(self.vocabularyType) + "'")
    
    def makeLayers(self, dimExample, name, trainable="AUTO", verbose=True, skipInputs=None):
        if trainable == "AUTO":
            trainable = True if self.wvPath == None else False
        skipInputs = skipInputs if skipInputs != None else []
        self.inputLayers = [Input(shape=(dimExample,), name=x) for x in self.inputNames if x not in skipInputs]
        if len(self.inputLayers) > 0:
            embeddingLayer = Embedding(len(self.embeddings), 
                                  self.embeddings[0].size, 
                                  weights=[self.getEmbeddingMatrix(self.name, verbose=verbose)], 
                                  input_length=dimExample,
                                  trainable=trainable,
                                  name=self.name + "_embeddings")
            self.embeddingLayers = [embeddingLayer(x) for x in self.inputLayers]
        else:
            self.embeddingLayers = []
        #return self.inputLayer, self.embeddingLayer
    
    def getEmbeddingMatrix(self, name, verbose=True):
        if verbose:
            print >> sys.stderr, "Making Embedding Matrix", name, (len(self.embeddings), self.embeddings[0].size), self.embeddingIndex.keys()[0:50], self.embeddings[-1]
        dimWordVector = len(self.embeddings[0])
        numWordVectors = len(self.embeddings)
        embedding_matrix = numpy.zeros((numWordVectors, dimWordVector))
        for i in range(len(self.embeddings)):
            embedding_matrix[i] = self.embeddings[i]
        return embedding_matrix