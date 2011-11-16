from GeneralEntityTypeRecognizerGztr import GeneralEntityTypeRecognizerGztr 

class BinaryEntityExampleBuilder(GeneralEntityTypeRecognizerGztr):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None):
        GeneralEntityTypeRecognizerGztr.__init__(self, style, classSet, featureSet, gazetteerFileName)
    
    def buildExamples(self, sentenceGraph):
        examples = GeneralEntityTypeRecognizerGztr.buildExamples(self, sentenceGraph)
        listExamples = []
        for example in examples:
            listExample = list(example)
            if listExample[1] != 1:
                listExample[1] = 2
            listExamples.append(listExample)
        return listExamples

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteerFileName=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = BinaryEntityExampleBuilder(style, classSet, featureSet, gazetteerFileName)
        if "names" in style:
            sentences = cls.getSentences(input, parse, tokenization, removeNameInfo=True)
        else:
            sentences = cls.getSentences(input, parse, tokenization, removeNameInfo=False)
        e.buildExamplesForSentences(sentences, output, idFileTag)
