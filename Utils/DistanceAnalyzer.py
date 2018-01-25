import sys
import Utils.Range as Range
import json
from Core.SentenceGraph import getCorpusIterator

class DistanceAnalyzer():
    def __init__(self):
        self.interactionSpans = {}
        self.eventSpans = {}
        self.intSpan = {"min":9999, "max":-9999}
        self.eventSpan = {"min":9999, "max":-9999}
    
    def toDict(self):
        return {"interactions":self.interactionSpans, "events":self.eventSpans, "limits":{"interaction":self.intSpan, "event":self.eventSpan}}
    
    def save(self, filePath):
        with open(filePath, "wt") as f:
            json.dump(self.toDict(), f, indent=2, sort_keys=True)
    
    def load(self, filePath):
        with open(filePath, "wt") as f:
            data = json.load(f)
            self.interactionSpans = data["interactions"]
            self.eventSpans = data["events"]
            self.intSpan = data["limits"]["interaction"]
            self.eventSpan = data["limits"]["event"]
            
    def analyze(self, corpusFiles, parse, tokenization=None):
        print >> sys.stderr, "Distance analysis for", corpusFiles
        for corpusFile in corpusFiles:
            for documentSentences in getCorpusIterator(corpusFile, None, parse, tokenization, removeIntersentenceInteractions=True):
                for sentenceElements in documentSentences:
                    self.addSentence(sentenceElements.sentenceGraph)
    
    def addSentence(self, sentenceGraph):
        if sentenceGraph == None:
            return
        tokens = sorted([(Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in sentenceGraph.tokens])
        indexByTokenId = {tokens[i][1].get("id"):i for i in range(len(tokens))}
        assert len(indexByTokenId) == len(tokens) # check that there were no duplicate ids
        entityById = {x.get("id"):x for x in sentenceGraph.entities}
        events = {}
        for interaction in sentenceGraph.interactions:
            e1Id = interaction.get("e1")
            e2Id = interaction.get("e2")
            e1 = entityById[e1Id]
            e2 = entityById[e2Id]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            index1 = indexByTokenId[t1.get("id")]
            index2 = indexByTokenId[t2.get("id")]
            intSpan = abs(index1 - index2)
            self.interactionSpans[intSpan] = self.interactionSpans.get(intSpan, 0) + 1
            self.intSpan["min"] = min(self.intSpan.get("min"), intSpan)
            self.intSpan["max"] = max(self.intSpan.get("max"), intSpan)
            if interaction.get("event") == "True":
                if e1Id not in events:
                    events[e1Id] = {"min":9999, "max":-9999}
                events[e1Id]["min"] = min(events[e1Id]["min"], index1, index2)
                events[e1Id]["max"] = max(events[e1Id]["max"], index1, index2)
        for eventId in sorted(events.keys()):
            eventSpan = events[eventId]["max"] - events[eventId]["min"]
            self.eventSpans[eventSpan] = self.eventSpans.get(eventSpan, 0) + 1
            self.eventSpan["min"] = min(self.eventSpan.get("min"), eventSpan)
            self.eventSpan["max"] = max(self.eventSpan.get("max"), eventSpan)

if __name__=="__main__":
    print >> sys.stderr, "##### Element Distance Analysis #####"
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None)
    optparser.add_option("-o", "--output", default=None)
    (options, args) = optparser.parse_args()
    
    analyzer = DistanceAnalyzer()
    analyzer.analyze(options.input.split(","), "McCC")
    print >> sys.stderr, analyzer.toDict() 