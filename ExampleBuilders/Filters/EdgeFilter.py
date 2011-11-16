class EdgeFilter:
    def __init__(self, gazetteer):
        pass
        self.gazMatchCache = {}
    
    def filter(self, token1, token2):
        return False
    
    def initSentence(self, sentenceGraph):
        gazCategories = {None:{"neg":-1}}
        #stems = {}
        for token in sentenceGraph.tokens:
            gazText = self.getGazetteerMatch(token.get("text").lower())
            if gazText != None:
                gazCategories[token] = self.gazetteer[gazText]
            else:
                gazCategories[token] = {"neg":-1}

    
    def getGazetteerMatch(self, string, stem=False):
        if string in self.gazMatchCache:
            return self.gazMatchCache[string]
        
        origString = string
        if stem:
            string = PorterStemmer.stem(string)
        
        if string in self.gazetteer:
            self.gazMatchCache[origString] = string
            return string
        elif string.find("-") != -1:
            replaced = string.replace("-","")
        else:
            self.gazMatchCache[origString] = None
            return None
        
        if replaced in self.gazetteer:
            self.gazMatchCache[origString] = replaced
            return replaced
        else:
            splitted = string.rsplit("-",1)[-1]
        
        if splitted  in self.gazetteer:
            self.gazMatchCache[origString] = splitted
            return splitted
        else:
            self.gazMatchCache[origString] = None
            return None