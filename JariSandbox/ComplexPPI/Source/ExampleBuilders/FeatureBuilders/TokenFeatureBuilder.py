from FeatureBuilder import FeatureBuilder
#import Stemming.PorterStemmer as PorterStemmer

class TokenFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
    
    def buildLinearOrderFeatures(self, tokenIndex, sentenceGraph, rangePos = 999, rangeNeg = 999 ):
        count = 1
        for i in range(tokenIndex+1,min(len(sentenceGraph.tokens), tokenIndex+rangePos+1)):
            tag = "linear_+" + str(count) + "_"
            t = sentenceGraph.tokens[i]
            self.features[self.featureSet.getId(tag+"txt_"+sentenceGraph.getTokenText(t))] = 1
            self.features[self.featureSet.getId(tag+"POS_"+t.attrib["POS"])] = 1
            if sentenceGraph.tokenIsName[t]:
                self.features[self.featureSet.getId(tag+"isName")] = 1
            count += 1
        count = 1
        for i in range(tokenIndex-1,max(tokenIndex-rangeNeg-1, -1),-1):
            tag = "linear_-" + str(count) + "_"
            t = sentenceGraph.tokens[i]
            self.features[self.featureSet.getId(tag+"txt_"+sentenceGraph.getTokenText(t))] = 1
            self.features[self.featureSet.getId(tag+"POS_"+t.attrib["POS"])] = 1
            if sentenceGraph.tokenIsName[t]:
                self.features[self.featureSet.getId(tag+"isName")] = 1
            count += 1
    
    def buildContentFeatures(self, tokenIndex, text, duplets=True, triplets=True):
        # Content
        if tokenIndex > 0 and text[0].isalpha() and text[0].isupper():
            self.features[self.featureSet.getId("upper_case_start")] = 1
        for j in range(len(text)):
            if j > 0 and text[j].isalpha() and text[j].isupper():
                self.features[self.featureSet.getId("upper_case_middle")] = 1
            # numbers and special characters
            if text[j].isdigit():
                self.features[self.featureSet.getId("has_digits")] = 1
                if j > 0 and text[j-1] == "-":
                    self.features[self.featureSet.getId("has_hyphenated_digit")] = 1
            elif text[j] == "-":
                self.features[self.featureSet.getId("has_hyphen")] = 1
            elif text[j] == "/":
                self.features[self.featureSet.getId("has_fslash")] = 1
            elif text[j] == "\\":
                self.features[self.featureSet.getId("has_bslash")] = 1
            # duplets
            if j > 0 and duplets:
                self.features[self.featureSet.getId("dt_"+text[j-1:j+1].lower())] = 1
            # triplets
            if j > 1 and triplets:
                self.features[self.featureSet.getId("tt_"+text[j-2:j+1].lower())] = 1

