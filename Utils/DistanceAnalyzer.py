import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import Utils.Range as Range

class DistanceAnalyzer():
    def __init__(self):
        pass
    
    def addSentence(self, sentenceGraph):
        tokens = sorted([(Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in sentenceGraph.tokens])
        indexByTokenId = {tokens[i][0].get("id"):i for i in range(len(tokens))}
        assert len(indexByTokenId) == len(tokens) # check that there were no duplicate ids
        entityById = {x.get("id"):x for x in sentenceGraph.entities}
        events = {}
        for interaction in sentenceGraph.interactions:
            e1Id = entityById[interaction.get("e1")]
            e2 = entityById[interaction.get("e2")]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            index1 = indexByTokenId[interaction.get("e1")]
            index2 = indexByTokenId[interaction.get("e2")]
            intSpan = abs(index1 - index2)
            if interaction.get("event") == "True":
                if e1Id not in events:
                    events[e1Id] = {"min":9999, "max":-9999}
                events[e1Id]["min"] = min(events[e1Id]["min"], index1, index2)
                events[e1Id]["max"] = max(events[e1Id]["max"], index1, index2)
        