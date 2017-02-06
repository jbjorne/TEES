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
        
    def getHypernyms(self, synset, tag=""):
        rv = []
        rv.append("SYNSET_" + tag + synset.name()) # add also the base level
        for hypernym in synset.hypernyms():
            rv.append("HYPER_" + tag + hypernym.name())
        return rv
    
    def getTokenFeatures(self, tokenText, pennPos, tag=""):
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
            rv.extend(self.getHypernyms(synsets[0], tag))
            #rv.append("SYNSET_" + tag + synsets[0].name())
            rv.append("LEX_" + tag + synsets[0].lexname())
        #print "D"
        return rv
    
    def buildPathFeatures(self, path):
        if len(path) < 3:
            return
        lexnames = []
        for token in path[1:-1]:
            pos = self.pennPOSToWordNet(token.get("POS"))
            synsets = self.getSynset(token.get("text"), pos)
            if synsets != None:
                lexnames.append(synsets[0].lexname())
            else:
                lexnames.append("NONE")
        lexnames = ["ENT"] + lexnames + ["ENT"]
        if len(lexnames) <= 4:
            self.features[self.featureSet.getId("WNP_" + "-".join(lexnames))] = 1
        for i in range(len(lexnames) - 2):
            self.features[self.featureSet.getId("WNP_" + "-".join(lexnames[i:i+3]))] = 1
    
    def buildFeaturesForEntityPair(self, token1, token2):
        f1 = self.getTokenFeatures(token1.get("text"), token1.get("POS"), "e1_")
        f2 = self.getTokenFeatures(token2.get("text"), token2.get("POS"), "e2_")
        for name in f1 + f2:
            self.features[self.featureSet.getId(name)] = 1
        for e1Name in f1:
            for e2Name in f2:
                self.features[self.featureSet.getId(e1Name + "__" + e2Name)] = 1
    
    def buildCompoundFeatures(self, token1, token2, tokens):
        t1Index = tokens.index(token1)
        t2Index = tokens.index(token1)
        if abs(t1Index - t2Index) > 1:
            return
        synsets = self.wordnet.synsets(token1.get("text") + "_" + token2.get("text"))
        if synsets != None:
            self.features[self.featureSet.getId("WNC_True")] = 1
            for synset in synsets:
                self.features[self.featureSet.getId("WNC_" + synset.lexname())] = 1
        else:
            self.features[self.featureSet.getId("WNC_False")] = 1
    
    def buildLinearFeatures(self, token, tokens, before=1, after=1, tag=""):
        tokenIndex = tokens.index(token)
        numTokens = len(tokens)
        for i in range(-before, 0) + range(1, 1 + after):
            currentIndex = tokenIndex + i 
            if currentIndex < 0 or currentIndex >= numTokens:
                continue
            t = tokens[currentIndex]
            synsets = self.wordnet.synsets(t.get("text"), self.pennPOSToWordNet(t.get("POS")))
            if len(synsets) > 0:
                self.features[self.featureSet.getId("WNL_" + tag + "_lin" + str(i) + "_" + synsets[0].lexname())] = 1

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