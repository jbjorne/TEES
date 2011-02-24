import sys, os
sys.path.append(os.path.join(os.path.abspath(__file__), ".."))
import Core.ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilder import FeatureBuilder
from nltk.corpus import wordnet as wn 

class WordNetFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
    
    def pennPOSToWordNet(self, pos):
        if pos.startswith("JJ"):
            return "a" #wn.ADJ
        elif pos.startswith("NN"):
            return "n" #wn.NOUN
        elif pos.startswith("VB"):
            #print "JEP"
            #print "VERB", wn.VERB
            return "v" #wn.VERB
        elif pos.startswith("RB"):
            return "r" #wn.ADV
        else:
            return None
    
    def getSynset(self, text, wordNetPos):
        if wordNetPos == None:
            return None
        synsets = wn.synsets(text, pos=wordNetPos)
        if len(synsets) > 0:
            return [synsets[0]]
        else:
            return None
        
    def getHypernyms(self, synset):
        rv = []
        rv.append("HYPER_"+synset.name) # add also the base level
        for hypernym in synset.hypernyms():
            rv.append("HYPER_"+hypernym.name)
        return rv
    
    def getTokenFeatures(self, tokenText, pennPos):
        #print tokenText, pennPos, "X",
        rv = []
        if tokenText == None:
            return rv
        #print "A",
        wordNetPos = self.pennPOSToWordNet(pennPos)
        #print "B",
        synsets = self.getSynset(tokenText, wordNetPos)
        #print "C",
        if synsets != None:
            rv.extend(self.getHypernyms(synsets[0]))
            rv.append("LEX_" + synsets[0].lexname)
        #print "D"
        return rv