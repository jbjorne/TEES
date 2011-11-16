import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer

class NamedEntityRecognizer(ExampleBuilder):
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            # CLASS
            if sentenceGraph.tokenIsName[token]:
                category = 1
            else:
                category = -1
            
            # FEATURES
            features = {}
            # Main features
            text = token.attrib["text"]
            features[self.featureSet.getId("txt_"+text)] = 1
            features[self.featureSet.getId("POS_"+token.attrib["POS"])] = 1
            stem = PorterStemmer.stem(text)
            features[self.featureSet.getId("stem_"+stem)] = 1
            features[self.featureSet.getId("nonstem_"+text[len(stem):])] = 1
            # Linear order features
            if i > 0:
                features[self.featureSet.getId("linear_-1_txt_"+sentenceGraph.tokens[i-1].attrib["text"])] = 1
                features[self.featureSet.getId("linear_-1_POS_"+sentenceGraph.tokens[i-1].attrib["POS"])] = 1
            if i > 1:
                features[self.featureSet.getId("linear_-2_txt_"+sentenceGraph.tokens[i-2].attrib["text"])] = 1
                features[self.featureSet.getId("linear_-2_POS_"+sentenceGraph.tokens[i-2].attrib["POS"])] = 1
            if i < len(sentenceGraph.tokens) - 1:
                features[self.featureSet.getId("linear_+1_txt_"+sentenceGraph.tokens[i+1].attrib["text"])] = 1
                features[self.featureSet.getId("linear_+1_POS_"+sentenceGraph.tokens[i+1].attrib["POS"])] = 1
            if i < len(sentenceGraph.tokens) - 2:
                features[self.featureSet.getId("linear_+2_txt_"+sentenceGraph.tokens[i+2].attrib["text"])] = 1
                features[self.featureSet.getId("linear_+2_POS_"+sentenceGraph.tokens[i+2].attrib["POS"])] = 1
            # Content
            if i > 0 and text[0].isalpha() and text[0].isupper():
                features[self.featureSet.getId("upper_case_start")] = 1
            for j in range(len(text)):
                if j > 0 and text[j].isalpha() and text[j].isupper():
                    features[self.featureSet.getId("upper_case_middle")] = 1
                # numbers and special characters
                if text[j].isdigit():
                    features[self.featureSet.getId("has_digits")] = 1
                    if j > 0 and text[j-1] == "-":
                        features[self.featureSet.getId("has_hyphenated_digit")] = 1
                elif text[j] == "-":
                    features[self.featureSet.getId("has_hyphen")] = 1
                elif text[j] == "/":
                    features[self.featureSet.getId("has_fslash")] = 1
                elif text[j] == "\\":
                    features[self.featureSet.getId("has_bslash")] = 1
                # duplets
                if j > 0:
                    features[self.featureSet.getId("dt_"+text[j-1:j+1].lower())] = 1
                # triplets
                if j > 1:
                    features[self.featureSet.getId("tt_"+text[j-2:j+1].lower())] = 1
            # Attached edges
            t1InEdges = sentenceGraph.dependencyGraph.in_edges(token)
            for edge in t1InEdges:
                features[self.featureSet.getId("t1HangingIn_"+edge[2].attrib["type"])] = 1
                features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["POS"])] = 1
                features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["text"])] = 1
            t1OutEdges = sentenceGraph.dependencyGraph.out_edges(token)
            for edge in t1OutEdges:
                features[self.featureSet.getId("t1HangingOut_"+edge[2].attrib["type"])] = 1
                features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["POS"])] = 1
                features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["text"])] = 1
             
            extra = {"xtype":"token","t":token}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
        return examples