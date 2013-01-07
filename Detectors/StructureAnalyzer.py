#from Detector import Detector
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from Utils.InteractionXML.CorpusElements import CorpusElements
from collections import defaultdict
import copy

class StructureAnalyzer():
    def __init__(self, modelFileName="structure.txt"):
        self.edgeTypes = None
        self.modelFileName = modelFileName
    
    def getValidEdgeTypes(self, e1, e2):
        if self.edgeTypes == null:
            raise Error("No structure definition loaded")
        if self.e1 in edgeTypes:
            if self.e2 in edgeTypes[e1]:
                return edgeTypes[e1][e2]
        return []
    
    def _dictToTuple(self, d):
        tup = []
        for key in sorted(d.keys()):
            tup.append((key, d[key]))
        return tuple(tup)
    
    def _tupToDict(self, tup):
        d = {}
        for pair in tup:
            d[pair[0]] = pair[1]
        return d
    
    def _analysisToString(self, argLimits, e2Types):
        s = ""
        for entityType in sorted(argLimits.keys()):
            s += entityType
            for argType in sorted(argLimits[entityType]):
                if argLimits[entityType][argType][1] > 0:
                    s += "\t" + argType + " " + str(argLimits[entityType][argType]).replace(" ", "") + " " + ",".join(sorted(list(e2Types[entityType][argType])))
            s += "\n"
        return s
    
    def _saveToModel(self, string, model):
        filename = model.get(self.modelFileName, True)
        f = open(filename, "wt")
        f.write(string)
        f.close()
        model.save()
        
    def load(self, model):
        filename = model.get(self.modelFileName)
        f = open(filename, "rt")
        lines = f.readlines()
        f.close()
        for line in lines:
            pass
    
    def analyzeXML(self, xml, model=None):
        #xml = CorpusElements.loadCorpus(xml, parse=None, tokenization=None, removeIntersentenceInteractions=False, removeNameInfo=False)
        #for sentence in corpusElements.sentences:
        #    for entity in sentence.entities
        xml = ETUtils.ETFromObj(xml)
        interactionTypes = set()
        countsTemplate = {}
        for interaction in xml.getiterator("interaction"):
            interactionTypes.add(interaction.get("type"))
            countsTemplate[interaction.get("type")] = 0
        
        argCounts = defaultdict(set)
        e2Types = defaultdict(lambda:defaultdict(set))
        for document in xml.getiterator("document"):
            interactions = [x for x in document.getiterator("interaction")]
            interactionsByE1 = defaultdict(list)
            for interaction in interactions:
                interactionsByE1[interaction.get("e1")].append(interaction)
            entities = [x for x in document.getiterator("entity")]
            entityById = {}
            for entity in entities:
                if entity.get("id") in entityById:
                    raise Error("Duplicate entity id " + str(entity.get("id") + " in document " + str(document.get("id"))))
                entityById[entity.get("id")] = entity
            for entity in entities:
                currentArgCounts = copy.copy(countsTemplate)
                for interaction in interactionsByE1[entity.get("id")]:
                    interactionTypes.add(interaction.get("type"))
                    currentArgCounts[interaction.get("type")] += 1
                    e2Types[entity.get("type")][interaction.get("type")].add(entityById[interaction.get("e2")].get("type"))
                argCounts[entity.get("type")].add(self._dictToTuple(currentArgCounts))
        
        argLimits = defaultdict(dict)
        for entityType in argCounts:
            for combination in argCounts[entityType]:
                combination = self._tupToDict(combination)
                #print entityType, combination
                for interactionType in interactionTypes:
                    if not interactionType in argLimits[entityType]:
                        argLimits[entityType][interactionType] = [sys.maxint,-sys.maxint]
                    minmax = argLimits[entityType][interactionType]
                    if minmax[0] > combination[interactionType]:
                        minmax[0] = combination[interactionType]
                    if minmax[1] < combination[interactionType]:
                        minmax[1] = combination[interactionType]
        
        # print results
        string = self._analysisToString(argLimits, e2Types)
        if model != None:
            self._saveToModel(string, model)
        return string

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    s = StructureAnalyzer()
    print s.analyzeXML(options.input)

            