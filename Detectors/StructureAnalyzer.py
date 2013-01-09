#from Detector import Detector
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from Utils.InteractionXML.CorpusElements import CorpusElements
from collections import defaultdict
import copy
import types

class StructureAnalyzer():
    def __init__(self, modelFileName="structure.txt"):
        self.modelFileName = modelFileName
        self.reset()
    
    def reset(self):
        self.edgeTypes = None
        self.argLimits = None
        self.e2Types = None
        self.relations = None
        self.sites = None
        self.modifiers = None
    
    def _init(self):
        self.reset()
        self.argLimits = defaultdict(dict)
        self.e2Types = defaultdict(lambda:defaultdict(set))
        self.relations = {}
        self.modifiers = {}
    
    def getValidEdgeTypes(self, e1Type, e2Type):
        assert type(e1Type) in types.StringTypes
        assert type(e2Type) in types.StringTypes
        if self.edgeTypes == None: 
            raise Exception("No structure definition loaded")
        if e1Type in self.edgeTypes:
            if e2Type in self.edgeTypes[e1Type]:
                return self.edgeTypes[e1Type][e2Type] # not a copy, so careful with using the returned list!
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
    
    def _defineValidEdgeTypes(self):
        assert self.e2Types != None
        self.edgeTypes = defaultdict(lambda:defaultdict(list))
        for e1Type in sorted(self.e2Types.keys()):
            for argType in sorted(self.e2Types[e1Type].keys()):
                for e2Type in sorted(list(self.e2Types[e1Type][argType])):
                    self.edgeTypes[e1Type][e2Type].append(argType)
        for relationType in sorted(self.relations.keys()):
            relation = self.relations[relationType]
            for e1Type in sorted(list(relation[1])):
                for e2Type in sorted(list(relation[2])):
                    self.edgeTypes[e1Type][e2Type].append(relationType)
                    if not relation[1]: # undirected
                        self.edgeTypes[e2Type][e1Type].append(relationType)
    
    def toString(self):
        if self.argLimits == None or self.e2Types == None: 
            raise Exception("No structure definition loaded")
        s = ""
        for entityType in sorted(self.argLimits.keys()):
            argString = ""
            for argType in sorted(self.argLimits[entityType]):
                if self.argLimits[entityType][argType][1] > 0:
                    argString += "\t" + argType + " " + str(self.argLimits[entityType][argType]).replace(" ", "") + " " + ",".join(sorted(list(self.e2Types[entityType][argType])))
            if argString != "":
                s += "EVENT "
            else:
                s += "ENTITY "
            s += entityType + argString + "\n"
        for relType in sorted(self.relations.keys()):
            s += "RELATION " + relType
            if relations[relType][0]:
                s += "\t directed \t"
            else:
                s += "\t undirected \t"
            s += ",".join(sorted(list(relations[relType][1])))
            s += "\t" + ",".join(sorted(list(relations[relType][1]))) + "\n"
        for modType in sorted(self.modifiers.keys()):
            s += "MODIFIER " + modType + "\t" + ",".join(sorted(list(self.modifiers[modType]))) + "\n"
        if self.sites != None:
            s += "SITES\t" + ",".join(sorted(list(self.sites))) + "\n"
        return s
    
    def save(self, model, filename=None):
        if filename == None:
            filename = self.modelFileName
        if model != None:
            filename = model.get(filename, True)
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
        for line in lines:
            splits = line.strip().split("\t")
            defType, e1Type = splits[0].split()
            if defType not in ["EVENT", "ENTITY", "RELATION", "SITES", "MODIFIER"]:
                raise Exception("Unknown structure definition " + str(defType))
            if defType in ["EVENT", "ENTITY"]: # in the graph, entities are just events with no arguments
                for intType in interactionTypes:
                    self.argLimits[e1Type][intType] = [0,0]
                for split in splits[1:]:
                    intType, limits, argE2Types = split.split()
                    self.argLimits[e1Type][intType] = eval(limits)
                    for argE2Type in argE2Types.split(","):
                        self.e2Types[e1Type][intType].add(argE2Type)
            elif defType == "RELATION":
                if len(splits) != 4:
                    raise Exception("Incorrect structure definition \"" + line.strip() + "\"")
                self.relations[e1Type] = [splits[0] == "directed", splits[1].split(","), splits[2].split(",")]
            elif defType == "SITES":
                self.sites = set(splits[1].split(","))
            elif defType == "MODIFIER":
                self.modifiers[e1Type] = set(splits[1].split(","))
                
        # construct additional structures
        self._defineValidEdgeTypes(self.e2Types)
    
    def showDebugInfo(self):
        # print internal structures
        print >> sys.stderr, "Argument limits:", self.argLimits
        print >> sys.stderr, "E2 types:", self.e2Types
        print >> sys.stderr, "Edge types:", self.edgeTypes
        print >> sys.stderr, "Relations:", self.relations
    
    def analyze(self, xml, model=None):
        #xml = CorpusElements.loadCorpus(xml, parse=None, tokenization=None, removeIntersentenceInteractions=False, removeNameInfo=False)
        #for sentence in corpusElements.sentences:
        #    for entity in sentence.entities
        self._init()
        
        xml = ETUtils.ETFromObj(xml)
        interactionTypes = set()
        countsTemplate = {}
        for interaction in xml.getiterator("interaction"):
            interactionTypes.add(interaction.get("type"))
            countsTemplate[interaction.get("type")] = 0
        
        argCounts = defaultdict(set)
        for document in xml.getiterator("document"):
            # read entities
            entities = [x for x in document.getiterator("entity")]
            entityById = {}
            for entity in entities:
                if entity.get("id") in entityById:
                    raise Error("Duplicate entity id " + str(entity.get("id") + " in document " + str(document.get("id"))))
                entityById[entity.get("id")] = entity
            # read interactions
            interactions = [x for x in document.getiterator("interaction")]
            interactionById = {}
            for interaction in interactions:
                if interaction.get("id") in interactionById:
                    raise Error("Duplicate entity id " + str(interaction.get("id") + " in document " + str(document.get("id"))))
                interactionById[interaction.get("id")] = interaction
            # process interactions
            interactionsByE1 = defaultdict(list)
            for interaction in interactions:
                if interaction.get("relation") == "True":
                    relType = interaction.get("type")
                    if not self.relations[relType]:
                        self.relations[relType] = [None, set(), set()]
                    isDirected = eval(interaction.get("directed", "False"))
                    if self.relations[relType][0] == None: # no relation of this type has been seen yet
                        self.relations[relType][0] == isDirected
                    elif self.relations[relType][0] != isDirected:
                        raise Exception("Conflicting relation directed-attribute for already defined relation of type " + relType)
                    self.relations[relType][1].add(entityById[interaction.get("e1")].get("type"))
                    self.relations[relType][2].add(entityById[interaction.get("e2")].get("type"))
                else:
                    interactionsByE1[interaction.get("e1")].append(interaction)
                # check for sites
                if interaction.get("type") == "Site" and interaction.get("parent") != None:
                    parentInteraction = interactionById[interaction.get("parent")]
                    if self.sites == None:
                        self.sites = set()
                    self.sites.add(entityById[parentInteraction.get("e1")].get("type") + " " + parentInteraction.get("type"))
            # process events
            for entity in entities:
                currentArgCounts = copy.copy(countsTemplate)
                for interaction in interactionsByE1[entity.get("id")]:
                    interactionTypes.add(interaction.get("type"))
                    currentArgCounts[interaction.get("type")] += 1
                    self.e2Types[entity.get("type")][interaction.get("type")].add(entityById[interaction.get("e2")].get("type"))
                argCounts[entity.get("type")].add(self._dictToTuple(currentArgCounts))
                # check for modifiers
                for modType in ("speculation", "negation"):
                    if (entity.get(modType) != None):
                        if modType not in self.modifiers:
                            self.modifiers[modType] = set()
                        self.modifiers[modType].add(entity.get("type"))
        
        for entityType in argCounts:
            for combination in argCounts[entityType]:
                combination = self._tupToDict(combination)
                #print entityType, combination
                for interactionType in interactionTypes:
                    if not interactionType in self.argLimits[entityType]:
                        self.argLimits[entityType][interactionType] = [sys.maxint,-sys.maxint]
                    minmax = self.argLimits[entityType][interactionType]
                    if minmax[0] > combination[interactionType]:
                        minmax[0] = combination[interactionType]
                    if minmax[1] < combination[interactionType]:
                        minmax[1] = combination[interactionType]
        
        # print results
        self._defineValidEdgeTypes()
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

            