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
        self.argLimits = None
        self.e2Types = None
        self.modelFileName = modelFileName
    
    def getValidEdgeTypes(self, e1, e2):
        if self.edgeTypes == null:
            raise Error("No structure definition loaded")
        if self.e1 in edgeTypes:
            if self.e2 in edgeTypes[e1]:
                return edgeTypes[e1][e2] # not a copy, so careful with using the returned list!
        return []
    
    def isValidEvent(self, entity, entityById=None, args=None):
        if args == None:
            args = []
        # analyze proposed arguments
        argTypes = set()
        argTypeCounts = defaultdict(int)
        argE2Types = defaultdict(set)
        for arg in args:
            assert entityById[arg.get("e1")] == entity
            argType = arg.get("type")
            argTypeCounts[argType] += 1
            argE2Types[argType].add(entityById[arg.get("e2")])
            argTypes.add(argType)
        argTypes = sorted(list(argTypes))
        # check validity of proposed arguments
        eventArgLimits = self.argLimits[entityType]
        for argType in argTypes:
            if argTypeCounts[argType] < eventArgLimits[argType][0]: # check for minimum number of arguments
                return False
            maxArgCount = eventArgLimits[argType][1]
            if maxArgCount > 1: # don't differentiate arguments beyond 0, 1 or more than one.
                maxArgCount = sys.maxint
            if argTypeCounts[argType] > maxArgCount: # check for maximum number of arguments
                return False
        # check that no required arguments are missing
        for argLimitType in eventArgLimits:
            if argLimitType not in argTypes: # this type of argument is not part of the proposed event
                if eventArgLimits[argLimitType][0] > 0: # for arguments not part of the event, the minimum limit must be one
                    return False
    
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
    
    def _defineValidEdgeTypes(self, e2Types):
        self.edgeTypes = {}
        for e1Type in sorted(e2Types.keys()):
            for argType in sorted(e2Types[e1Type].keys()):
                for e2Type in sorted(list(e2Types[e1Type][argType])):
                    if e1Type not in self.edgeTypes:
                        self.edgeTypes[e1Type] = {}
                    if e2Type not in self.edgeTypes[e1Type]:
                        self.edgeTypes[e1Type][e2Type] = []
                    self.edgeTypes[e1Type][e2Type].append(argType)
    
    def toString(self):
        assert self.argLimits != None
        assert self.e2Types != None
        s = ""
        for entityType in sorted(self.argLimits.keys()):
            s += entityType
            for argType in sorted(self.argLimits[entityType]):
                if self.argLimits[entityType][argType][1] > 0:
                    s += "\t" + argType + " " + str(self.argLimits[entityType][argType]).replace(" ", "") + " " + ",".join(sorted(list(self.e2Types[entityType][argType])))
            s += "\n"
        return s
    
    def save(self, model, filename=None):
        if filename == None:
            filename = modelFileName
        if model != None:
            filename = model.get(self.modelFileName, False)
        f = open(filename, "wt")
        f.write(self.toString())
        f.close()
        if model != None:
            model.save()
        
    def load(self, model, filename=None):
        if filename == None:
            filename = self.modelFileName
        if model != None:
            filename = model.get(filename)
        f = open(filename, "rt")
        lines = f.readlines()
        f.close()
        # determine all possible interaction types
        interactionTypes = set()
        countsTemplate = {}
        for line in lines:
            splits = line.strip().split("\t")
            for split in splits[1:]:
                intType = split.split()[0]
                interactionTypes.add(intType)
                countsTemplate[intType] = 0
        interactionTypes = sorted(list(interactionTypes))
        # load data structures
        self.argLimits = defaultdict(dict)
        self.e2Types = defaultdict(lambda:defaultdict(set))
        for line in lines:
            splits = line.strip().split("\t")
            e1Type = splits[0]
            for intType in interactionTypes:
                self.argLimits[e1Type][intType] = [0,0]
            for split in splits[1:]:
                intType, limits, argE2Types = split.split()
                self.argLimits[e1Type][intType] = eval(limits)
                for argE2Type in argE2Types.split(","):
                    self.e2Types[e1Type][intType].add(argE2Type)
        # construct additional structures
        self._defineValidEdgeTypes(self.e2Types)
    
    def showDebugInfo(self):
        # print internal structures
        print >> sys.stderr, "Argument limits:", self.argLimits
        print >> sys.stderr, "E2 types:", self.e2Types
        print >> sys.stderr, "Edge types:", self.edgeTypes
    
    def analyze(self, xml, model=None):
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
        self._defineValidEdgeTypes(e2Types)
        self.argLimits = argLimits
        self.e2Types = e2Types
        if model != None:
            self.save(model)

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
    optparser.add_option("-o", "--output", default=None, dest="output", help="", metavar="FILE")
    optparser.add_option("-l", "--load", default=False, action="store_true", dest="load", help="Input is a saved structure analyzer file")
    (options, args) = optparser.parse_args()
    
    s = StructureAnalyzer()
    if options.load:
        s.load(None, options.input)
    else:
        s.analyze(options.input)
    s.showDebugInfo()
    print >> sys.stderr, "--- Structure Analysis ----"
    print >> sys.stderr, s.toString()
    if options.output != None:
        s.save(None, options.output)

            