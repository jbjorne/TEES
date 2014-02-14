#from Detector import Detector
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from Utils.InteractionXML.CorpusElements import CorpusElements
from collections import defaultdict
import copy
import types

class Relation():
    def __init__(self, relType=None):
        self.type = relType
        self.isDirected = None
        self.e1Types = set()
        self.e2Types = set()
        self.e1Role = None
        self.e2Role = None
    
    def setStructure(self, isDirected=None, e1Role=None, e2Role=None, id="undefined"):
        if self.isDirected == None: # no relation of this type has been seen yet
            self.isDirected = isDirected
        elif self.isDirected != isDirected:
            raise Exception("Conflicting relation directed-attribute (" + str(isDirected) + ")for already defined relation of type " + self.type + " in relation " + id)
        if self.e1Role == None: # no relation of this type has been seen yet
            self.e1Role = e1Role
        elif self.e1Role != e1Role:
            raise Exception("Conflicting relation e1Role-attribute (" + str(e1Role) + ") for already defined relation of type " + self.type + " in relation " + id)
        if self.e2Role == None: # no relation of this type has been seen yet
            self.e2Role = e2Role
        elif self.e2Role != e2Role:
            raise Exception("Conflicting relation e2Role-attribute (" + str(e2Role) + ") for already defined relation of type " + self.type + " in relation " + id)

    def __repr__(self): # for debugging
        s = "<Relation"
        s += " " + str(self.type)
        s += " " + str(self.e1Types)
        s += " " + str(self.e2Types)
        s += " " + str(self.e1Role)
        s += " " + str(self.e2Role)
        s += ">"
        return s

class StructureAnalyzer():
    def __init__(self, modelFileName="structure.txt"):
        self.modelFileName = modelFileName
        self.reset()

    def isInitialized(self):
        return self.argLimits != None

    def reset(self):
        self.edgeTypes = None
        self.argLimits = None
        self.e2Types = None
        self.relations = None
        self.sites = None
        self.modifiers = None
        self.counts = None
        self.targets = None
        
        self.eventArgumentTypes = None
        #self.relationTypes = None
    
    def _init(self):
        self.reset()
        self.argLimits = defaultdict(dict)
        self.e2Types = defaultdict(lambda:defaultdict(set))
        self.relations = {}
        self.modifiers = {}
        self.targets = {}
        self.eventArgumentTypes = set()
        
    def getEntityRoles(self, edgeType):
        if self.isEventArgument(edgeType):
            return None
        else:
            relation = self.relations[edgeType]
            if relation.e1Role == None and relation.e2Role == None:
                return None
            else:
                return (relation.e1Role, relation.e2Role)
    
    def _updateCounts(self):
        self.counts = defaultdict(dict)
        self.counts["RELATION"] = len(self.relations)
        self.counts["MODIFIER"] = len(self.modifiers)
        self.counts["ENTITY"] = 0
        self.counts["EVENT"] = 0
        for entityType in sorted(self.argLimits.keys()):
            isEvent = False
            for argType in sorted(self.argLimits[entityType]):
                if self.argLimits[entityType][argType][1] > 0:
                    isEvent = True
                    break
            if isEvent:
                self.counts["EVENT"] += 1
            else:
                self.counts["ENTITY"] += 1
    
    def hasDirectedTargets(self):
        if "INTERACTION" not in self.targets: # no interactions to predict
            return False
        for argType in self.eventArgumentTypes: # look for event argument targets (always directed)
            if argType in self.targets["INTERACTION"]:
                return True
        for relType in self.relations: # look for directed relation targets
            relation = self.relations[relType]
            assert relation.isDirected != None
            if relation.isDirected and relType in self.targets["INTERACTION"]:
                return True
        return False
        
    def isDirected(self, edgeType):
        if self.isEventArgument(edgeType):
            return True
        else:
            relation = self.relations[edgeType]
            assert relation.isDirected in [True, False]
            return relation.isDirected
    
    def isEvent(self, entityType):
        if entityType in self.e2Types:
            return True
        else:
            return False
    
    def isEventArgument(self, edgeType):
        if edgeType in self.eventArgumentTypes:
            return True
        else:
            assert edgeType in self.relations, (edgeType, self.relations)
            return False
        
    def getArgLimits(self, entityType, argType):
        return self.argLimits[entityType][argType]
    
    def getValidEdgeTypes(self, e1Type, e2Type, forceUndirected=False):
        assert type(e1Type) in types.StringTypes
        assert type(e2Type) in types.StringTypes
        if self.edgeTypes == None: 
            raise Exception("No structure definition loaded")
        validEdgeTypes = []
        if e1Type in self.edgeTypes and e2Type in self.edgeTypes[e1Type]:
            if forceUndirected:
                validEdgeTypes = self.edgeTypes[e1Type][e2Type]
            else:
                return self.edgeTypes[e1Type][e2Type] # not a copy, so careful with using the returned list!
        if forceUndirected and e2Type in self.edgeTypes and e1Type in self.edgeTypes[e2Type]:
            validEdgeTypes = validEdgeTypes + self.edgeTypes[e2Type][e1Type]
        return validEdgeTypes

    
#    def isRelation(self, edgeType):
#        if edgeType in self.relationTypes:
#            return True
#        elif edgeType in self.eventArgumentTypes:
#            return False
#        else:
#            raise Exception("Unknown interaction type " + str(edgeType))
    
    def isValidEvent(self, entity, args=None, entityById=None, noUpperLimitBeyondOne=True, issues=None):
        if args == None:
            args = []
        if type(entity) in types.StringTypes:
            entityType = entity
        else:
            entityType = entity.get("type")
        # analyze proposed arguments
        argTypes = set()
        argTypeCounts = defaultdict(int)
        argE2Types = defaultdict(set)
        for arg in args:
            if type(arg) in [types.TupleType, types.ListType]:
                argType, argE2Type = arg
            else: # arg is an interaction element
                argType = arg.get("type")
                argE2Type = entityById[arg.get("e2")].get("type")
            argTypeCounts[argType] += 1
            argE2Types[argType].add(argE2Type)
            argTypes.add(argType)
        argTypes = sorted(list(argTypes))
        # check validity of proposed arguments
        valid = True
        eventArgLimits = self.argLimits[entityType]
        for argType in argTypes:
            if argTypeCounts[argType] < eventArgLimits[argType][0]: # check for minimum number of arguments
                if issues != None:
                    issues["TOO_FEW_ARG:"+entityType+"."+argType] += 1
                    valid = False
                else:
                    return False
            maxArgCount = eventArgLimits[argType][1]
            if maxArgCount > 1 and noUpperLimitBeyondOne: # don't differentiate arguments beyond 0, 1 or more than one.
                maxArgCount = sys.maxint
            if argTypeCounts[argType] > maxArgCount: # check for maximum number of arguments
                if issues != None:
                    issues["TOO_MANY_ARG:"+entityType+"."+argType] += 1
                    valid = False
                else:
                    return False
        # check that no required arguments are missing
        for argLimitType in eventArgLimits:
            if argLimitType not in argTypes: # this type of argument is not part of the proposed event
                if eventArgLimits[argLimitType][0] > 0: # for arguments not part of the event, the minimum limit must be one
                    if issues != None:
                        issues["MISSING_ARG:"+entityType+"."+argLimitType] += 1
                        valid = False
                    else:
                        return False
        return valid
    
    def _getElementDict(self, document, elementType):
        entities = [x for x in document.getiterator("entity")]
        elementById = {}
        for element in document.getiterator(elementType):
            elementId = element.get("id")
            if elementId == None:
                raise Error("Element " + elementType + " without id in document " + str(document.get("id")))
            if elementId in elementById:
                raise Error("Duplicate " + elementType + " id " + str(elementId) + " in document " + str(document.get("id")))
            elementById[elementId] = element
        return elementById
    
    def _getElementsAndParents(self, rootElement, elementType):
        elements = []
        for element in rootElement:
            elements.append((element, rootElement))
            elements.extend(self._getElementsAndParents(element, elementType))
        return elements
    
    def validate(self, xml, printCounts=True, simulation=False, debug=False):
        # 1. validate all edges (as relations)
        # 2. validate events constructed from remaining edges/entities
        # 3. repeat 2. until only valid events left
        counts = defaultdict(int)
        xml = ETUtils.ETFromObj(xml)
        for document in xml.getiterator("document"):
            entities = [x for x in document.getiterator("entity")]
            entityById = self._getElementDict(document, "entity")
            # Remove invalid interaction edges
            eventArgumentsByE1 = defaultdict(list)
            relations = []
            eventArguments = []
            for interaction in document.getiterator("interaction"):
                e1 = entityById[interaction.get("e1")]
                e2 = entityById[interaction.get("e2")]
                if interaction.get("type") in self.getValidEdgeTypes(e1.get("type"), e2.get("type")):
                    if interaction.get("event") == "True": # interaction is an event argument
                        eventArguments.append(interaction)
                        eventArgumentsByE1[interaction.get("e1")].append(interaction)
                        #if interaction.get("relation") not in (None, "False"):
                        #    interaction.set("relation", None)
                    else:
                        relations.append(interaction)
                        #interaction.set("relation", "True")
            # process events
            removed = 1
            while removed > 0:
                removed = 0
                remainingEntities = []
                remainingEntityIds = set()
                for entity in entities:
                    entityId = entity.get("id")
                    if self.isValidEvent(entity, eventArgumentsByE1[entityId], entityById):
                        remainingEntities.append(entity)
                        remainingEntityIds.add(entityId)
                    else:
                        if debug:
                            print >> sys.stderr, "Removing invalid event " + entity.get("id") + ":" + entity.get("type") + ":" + ",".join([x.get("type") for x in eventArgumentsByE1[entityId]])
                        counts[entity.get("type")] += 1
                        removed += 1
                entities = remainingEntities
                if removed > 0:
                    # Process event arguments
                    remainingEventArguments = []
                    eventArgumentsByE1 = defaultdict(list) # rebuild the map for current remaining entities
                    for arg in eventArguments:
                        if arg.get("e1") in remainingEntityIds and arg.get("e2") in remainingEntityIds:
                            remainingEventArguments.append(arg)
                            eventArgumentsByE1[arg.get("e1")].append(arg)
                        elif debug:
                            print >> sys.stderr, "Removing unconnected argument " + arg.get("id") + ":" + arg.get("type")
                    eventArguments = remainingEventArguments
                    # Process relations
                    remainingRelations = []
                    for relation in relations:
                        if relation.get("e1") in remainingEntityIds and relation.get("e2") in remainingEntityIds:
                            remainingRelations.append(relation)
                        elif debug:
                            print >> sys.stderr, "Removing unconnected relation " + relation.get("id") + ":" + relation.get("type")
                    relations = remainingRelations
            # clean XML
            if not simulation:
                interactions = eventArguments + relations
                for interaction, parent in self._getElementsAndParents(document, "interaction"):
                    if interaction not in interactions:
                        parent.remove(interaction)
                for entity, parent in self._getElementsAndParents(document, "entity"):
                    if entity not in entities:
                        parent.remove(entity)
        counts = dict(counts)
        if printCounts:
            print >> sys.stderr, "Validation removed:", counts
        return counts
    
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
    
#    def _defineEdgeTypes(self):
#        self.relationTypes = set(self.relations.keys())
#        self.eventArgumentTypes = set()
#        for entityType in self.argLimits.keys():
#            for argType in self.argLimits[entityType]:
#                self.eventArgumentTypes.add(argType)
    
    def _defineValidEdgeTypes(self):
        assert self.e2Types != None
        self.edgeTypes = defaultdict(lambda:defaultdict(list))
        for e1Type in sorted(self.e2Types.keys()):
            for argType in sorted(self.e2Types[e1Type].keys()):
                for e2Type in sorted(list(self.e2Types[e1Type][argType])):
                    self.edgeTypes[e1Type][e2Type].append(argType)
        for relationType in sorted(self.relations.keys()):
            relation = self.relations[relationType]
            for e1Type in sorted(list(relation.e1Types)):
                for e2Type in sorted(list(relation.e2Types)):
                    self.edgeTypes[e1Type][e2Type].append(relationType)
                    assert relation.isDirected in [True, False]
                    if not relation.isDirected: # undirected
                        self.edgeTypes[e2Type][e1Type].append(relationType)
    
    def toString(self):
        if self.argLimits == None or self.e2Types == None: 
            raise Exception("No structure definition loaded")
        s = ""
        eventStrings = []
        entityStrings = []
        for entityType in sorted(self.argLimits.keys()):
            argString = ""
            for argType in sorted(self.argLimits[entityType]):
                if self.argLimits[entityType][argType][1] > 0:
                    argString += "\t" + argType + " " + str(self.argLimits[entityType][argType]).replace(" ", "") + " " + ",".join(sorted(list(self.e2Types[entityType][argType])))
            if argString != "":
                eventStrings += "EVENT " + entityType + argString + "\n"
            else:
                entityStrings += "ENTITY " + entityType + argString + "\n"
        s += "".join(entityStrings)
        s += "".join(eventStrings)
        for relType in sorted(self.relations.keys()):
            relation = self.relations[relType]
            s += "RELATION " + relType
            if relation.isDirected:
                s += "\tdirected\t"
            else:
                s += "\tundirected\t"
            if relation.e1Role != None:
                s += relation.e1Role + " "
            s += ",".join(sorted(list(relation.e1Types)))
            s += "\t"
            if relation.e2Role != None:
                s += relation.e2Role + " "
            s += ",".join(sorted(list(relation.e2Types))) + "\n"
        for modType in sorted(self.modifiers.keys()):
            s += "MODIFIER " + modType + "\t" + ",".join(sorted(list(self.modifiers[modType]))) + "\n"
        for target in sorted(self.targets.keys()):
            s += "TARGET " + target + "\t" + ",".join(sorted(list(self.targets[target]))) + "\n"
        return s
    
    def save(self, model, filename=None):
        if filename == None:
            filename = self.modelFileName
        if model != None:
            filename = model.get(filename, True)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
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
        # initialize
        self._init()
        # determine all possible interaction types
        interactionTypes = set()
        for line in lines:
            splits = line.strip().split("\t")
            for split in splits[1:]:
                intType = split.split()[0]
                interactionTypes.add(intType)
        interactionTypes = sorted(list(interactionTypes))
        # load data structures
        for line in lines:
            tabSplits = line.strip().split("\t")
            defType, defName = tabSplits[0].split()
            if defType not in ["EVENT", "ENTITY", "RELATION", "MODIFIER", "TARGET"]:
                raise Exception("Unknown structure definition " + str(defType))
            if defType in ["EVENT", "ENTITY"]: # in the graph, entities are just events with no arguments
                e1Type = defName
                self.argLimits[e1Type] # initialize to include entities with no arguments
                for intType in interactionTypes:
                    self.argLimits[e1Type][intType] = [0,0]
                for split in tabSplits[1:]:
                    intType, limits, argE2Types = split.split()
                    self.eventArgumentTypes.add(intType)
                    self.argLimits[e1Type][intType] = eval(limits)
                    for argE2Type in argE2Types.split(","):
                        self.e2Types[e1Type][intType].add(argE2Type)
            elif defType == "RELATION":
                if len(tabSplits) != 4:
                    raise Exception("Incorrect relation definition \"" + str(tabSplits) + "\"")
                relation = Relation(defName)
                self.relations[defName] = relation
                relation.isDirected = tabSplits[1] == "directed"
                e1Role = None
                if " " in tabSplits[2]:
                    e1Role, tabSplits[2] = tabSplits[2].split()
                e2Role = None
                if " " in tabSplits[3]:
                    e2Role, tabSplits[3] = tabSplits[3].split()
                relation.e1Role = e1Role
                relation.e2Role = e2Role
                relation.e1Types = set(tabSplits[2].split(","))
                relation.e2Types = set(tabSplits[3].split(","))
            elif defType == "MODIFIER":
                self.modifiers[defName] = set(tabSplits[1].split(","))
            elif defType == "TARGET":
                self.targets[defName] = set(tabSplits[1].split(","))
                
        # construct additional structures
        #self._defineEdgeTypes()
        self._defineValidEdgeTypes()
        self._updateCounts()
    
    def showDebugInfo(self):
        # print internal structures
        print >> sys.stderr, "Argument limits:", self.argLimits
        print >> sys.stderr, "E2 types:", self.e2Types
        print >> sys.stderr, "Edge types:", self.edgeTypes
        print >> sys.stderr, "Relations:", self.relations
    
    def analyze(self, inputs, model=None):
        #xml = CorpusElements.loadCorpus(xml, parse=None, tokenization=None, removeIntersentenceInteractions=False, removeNameInfo=False)
        #for sentence in corpusElements.sentences:
        #    for entity in sentence.entities
        self._init()
        
        if type(inputs) in types.StringTypes:
            inputs = [inputs]
        interactionTypes = set()
        for xml in inputs:
            print >> sys.stderr, "Analyzing", xml
            xml = ETUtils.ETFromObj(xml)
            
#            countsTemplate = {}
#            for interaction in xml.getiterator("interaction"):
#                interactionTypes.add(interaction.get("type"))
#                countsTemplate[interaction.get("type")] = 0
            
            argCounts = defaultdict(set)
            for document in xml.getiterator("document"):
                entityById = self._getElementDict(document, "entity")
                interactionById = self._getElementDict(document, "interaction")
                # process interactions
                interactionsByE1 = defaultdict(list)
                for interaction in document.getiterator("interaction"):
                    if interaction.get("given") != "True":
                        if "INTERACTION" not in self.targets:
                            self.targets["INTERACTION"] = set()
                        self.targets["INTERACTION"].add(interaction.get("type"))
                    if not (interaction.get("event") == "True"):
                        relType = interaction.get("type")
                        if relType not in self.relations:
                            self.relations[relType] = Relation(relType)
                        self.relations[relType].setStructure(interaction.get("directed") == "True", interaction.get("e1Role"), interaction.get("e2Role"), interaction.get("id"))
                        self.relations[relType].e1Types.add(entityById[interaction.get("e1")].get("type"))
                        self.relations[relType].e2Types.add(entityById[interaction.get("e2")].get("type"))
                    else:
                        self.eventArgumentTypes.add(interaction.get("type"))
                        interactionsByE1[interaction.get("e1")].append(interaction)
                # process events
                for entity in document.getiterator("entity"):
                    if entity.get("given") != "True":
                        if "ENTITY" not in self.targets:
                            self.targets["ENTITY"] = set()
                        self.targets["ENTITY"].add(entity.get("type"))
                    currentArgCounts = defaultdict(int)# copy.copy(countsTemplate)
                    for interaction in interactionsByE1[entity.get("id")]:
                        interactionTypes.add(interaction.get("type"))
                        currentArgCounts[interaction.get("type")] += 1
                        self.e2Types[entity.get("type")][interaction.get("type")].add(entityById[interaction.get("e2")].get("type"))
                    argCounts[entity.get("type")].add(self._dictToTuple(currentArgCounts)) # save only one example for each detected argument combination
                    # check for modifiers
                    for modType in ("speculation", "negation"):
                        if (entity.get(modType) != None):
                            if modType not in self.modifiers:
                                self.modifiers[modType] = set()
                            self.modifiers[modType].add(entity.get("type"))
        
        for entityType in argCounts:
            self.argLimits[entityType] # initialize to include entities with no arguments
            for interactionType in interactionTypes:
                self.argLimits[entityType][interactionType] = [sys.maxint,0]
            for argCombination in argCounts[entityType]:
                argCombination = self._tupToDict(argCombination)
                #print entityType, combination
                for interactionType in interactionTypes:
                    minmax = self.argLimits[entityType][interactionType]
                    if interactionType not in argCombination:
                        minmax[0] = 0
                    else:
                        if minmax[0] > argCombination[interactionType]:
                            minmax[0] = argCombination[interactionType]
                        if minmax[1] < argCombination[interactionType]:
                            minmax[1] = argCombination[interactionType]
        
        # print results
        #self._defineEdgeTypes()
        self._defineValidEdgeTypes()
        self._updateCounts()
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
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="Debug mode")
    optparser.add_option("-v", "--validate", default=None, dest="validate", help="validate input", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    s = StructureAnalyzer()
    if options.load:
        s.load(None, options.input)
    else:
        s.analyze(options.input.split(","))
    if options.debug:
        s.showDebugInfo()
    print >> sys.stderr, "--- Structure Analysis ----"
    print >> sys.stderr, s.toString()
    if options.output != None:
        s.save(None, options.output)
    if options.validate != None:
        print >> sys.stderr, "--- Validation ----"
        xml = ETUtils.ETFromObj(options.validate)
        s.validate(xml, simulation=False, debug=options.debug)
        if options.output != None:
            ETUtils.write(xml, options.output)
            
            