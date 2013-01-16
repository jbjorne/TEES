__version__ = "$Revision: 1.1 $"

import sys, os, types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Core.SentenceGraph as SentenceGraph
import Utils.ElementTreeUtils as ETUtils
#from Utils.ProgressCounter import ProgressCounter
import Utils.InteractionXML.CorpusElements as CorpusElements
import Utils.Range as Range

class NameGazetteer:
    
    def __init__(self):
        self.names = {}
        self.normalize = True
    
    def normalizeText(self, text):
        return text.replace("-","").replace("/","").replace(",","").replace("\\","").replace(" ","").lower()
    
    @classmethod
    def build(cls, input, output, parse, tokenization=None):
        gaz = NameGazetteer()
        gaz.fromXML(input, parse, tokenization)
        gaz.save(output)
        return gaz
    
    def addName(self, tokens, parent=None):
        if len(tokens) == 0:
            return
        
        if parent == None:
            parent = self.names
        
        texts = []
        tokText = tokens[0]
        if self.normalize:
            tokText = self.normalizeText(tokText)
        noDigits = tokText.replace("0","").replace("1","").replace("2","").replace("0","")
        if len(texts[0]) > 2 and texts[0][-1].isdigit():
            texts.append(texts[0][:-1])
        for text in texts:
            if not parent.has_key(text):
                parent[text] = {}
            if len(tokens) == 1:
                parent[text][None] = None # mark string end
            else:
                self.addName(tokens[1:], parent[text])
    
    def save(self, output, parent=None, path=[]):
        if type(output) == types.StringType:
            output = open(output, "wt")
        topLevel = False
        if parent == None:
            parent = self.names
            topLevel = True
        
        if parent.has_key(None) and len(path) > 0:
            output.write("\t".join(path)+"\n")
        for key in sorted(parent.keys()):
            if key == None:
                continue
            self.save(output, parent[key], path+[key])
        if topLevel:
            output.close()
    
    def fromXML(self, input, parse, tokenization=None):
        self.names = {}
        if type(input) == types.StringType:
            corpus = CorpusElements.loadCorpus(input, parse, tokenization)
        else:
            corpus = input
        for sentence in corpus.sentences:
            tokenTuples = self.prepareTokens(sentence.tokens)
            for entity in sentence.entities:
                if entity.get("given") == "True":
                    tokens = self.getTokens(entity, tokenTuples)
                    assert len(tokens) > 0
                    self.addName(tokens)
                    self.addName(["".join(tokens)])
    
    def prepareTokens(self, tokens):
        tokenTuples = []
        for token in tokens:
            tokenTuples.append( (Range.charOffsetToSingleTuple(token.get("charOffset")), token) )
        return tokenTuples
    
    def getTokens(self, entity, tokenTuples):
        offset = entity.get("charOffset")
        assert offset != None
        offset = Range.charOffsetToSingleTuple(offset)
        match = []
        for tokenTuple in tokenTuples:
            if Range.overlap(offset, tokenTuple[0]):
                match.append(tokenTuple[1].get("text"))
            elif len(match) > 0: # passed end
                break
        return match
        
    def matchTokens(self, tokens, tokenIsName, nameDict=None, tokenSet=None, tokenChain=[]):
        if len(tokens) == 0:
            return
        if tokenSet == None:
            tokenSet = set()
        if nameDict == None:
            nameDict = self.names
        
        token = tokens[0]
        self.matchTokens(tokens[1:], tokenIsName, self.names)
        if not tokenIsName[token]:
            text = token.get("text")
            assert text != None
            if self.normalize:
                text = self.normalizeText(text)
            for key in nameDict.keys():
                if key == text:
                    if nameDict[key].has_key(None): # string end
                        for prevToken in tokenChain:
                            tokenSet.add(prevToken)
                        tokenSet.add(token)
                    self.matchTokens(tokens[1:], tokenIsName, nameDict[key], tokenSet, tokenChain+[token])
        return tokenSet
            
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    import os
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input file (interaction XML)")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file name")
    optparser.add_option("-e", "--test", default=None, dest="test", help="")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
    (options, args) = optparser.parse_args()
    
    corpus = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    gaz = NameGazetteer.build(corpus, options.output, options.parse, options.tokenization)
    
    if options.test != None:
        corpus = SentenceGraph.loadCorpus(options.test, options.parse, options.tokenization)
    for sentence in corpus.sentences:
        tokenSet = gaz.matchTokens(sentence.tokens, sentence.sentenceGraph.tokenIsName)
        string = ""
        for token in sentence.tokens:
            chain = False
            if token in tokenSet:
                chain = True
                if string != "":
                    string += "\t"
                string += token.get("text")
            elif chain:
                string += "\n"
        if chain:
            string += "\n"
        if string != "":
            print sentence.sentence.get("id") + "\n" + string