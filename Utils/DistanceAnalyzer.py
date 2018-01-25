import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import Utils.Range as Range

class DistanceAnalyzer():
    def __init__():
        pass
    
    def addSentence(self, sentenceGraph, parserName):
        parse = IXMLUtils.getParseElement(sentence, parserName)
        tokenization = IXMLUtils.getParseElement(sentence, parse.get("tokenizer"))
        tokens = sorted([(Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in tokenization.findall("token")])
        indexByTokenId = {tokens[i][0].get("id"):i for i in range(len(tokens))}
        assert len(indexByTokenId) == len(tokens) # check that there were no duplicate ids
        for interaction in sentence.findall("interaction"):
            indexByTokenId[interaction.get("e1"), interaction.get("e2")]
        