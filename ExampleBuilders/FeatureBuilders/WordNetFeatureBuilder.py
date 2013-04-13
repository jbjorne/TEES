import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
#print os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
from Core.IdSet import IdSet
import Utils.Libraries.PorterStemmer as PorterStemmer
import Core.ExampleUtils as ExampleUtils
from FeatureBuilder import FeatureBuilder

class WordNetFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet=None):
        FeatureBuilder.__init__(self, featureSet)
        from nltk.corpus import wordnet
        self.wordnet = wordnet
        print >> sys.stderr, "Using WordNet via NLTK"
    
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
        synsets = self.wordnet.synsets(text, pos=wordNetPos)
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

if __name__=="__main__":
    w = WordNetFeatureBuilder()
    print w.getTokenFeatures("cat", "NN")
    print w.getTokenFeatures("rivers", "NN")
    print w.getTokenFeatures("lakes", "NN")
    print w.getTokenFeatures("oceans", "NN")
    print w.getTokenFeatures("water", "NN")
    print w.getTokenFeatures("milk", "NN")
    print w.getTokenFeatures("chicken", "NN")
    print w.getTokenFeatures("food", "NN")