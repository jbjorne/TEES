#from Detector import Detector
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict
import types

def rangeToTuple(string):
    assert string.startswith("[")
    assert string.endswith("]")
    string = string.strip("[").strip("]")
    begin, end = string.split(",")
    begin = int(begin)
    end = int(end)
    return (begin, end)

class Target():
    def __init__(self, targetClass):
        assert targetClass in ["INTERACTION", "ENTITY"]
        self.targetClass = targetClass
        self.targetTypes = set()
    
    def __repr__(self):
        return "TARGET " + self.targetClass + "\t" + ",".join(sorted(list(self.targetTypes)))
    
    def load(self, line):
        line = line.strip()
        if not line.startswith("ENTITY"):
            raise Exception("Not an entity definition line: " + line)
        self.type = line.split()[1]

class Entity():
    def __init__(self, entityType=None):
        self.type = entityType
    
    def __repr__(self):
        return "ENTITY " + self.type
    
    def load(self, line):
        line = line.strip()
        if not line.startswith("ENTITY"):
            raise Exception("Not an entity definition line: " + line)
        self.type = line.split()[1]

class Event():
    def __init__(self, eventType=None):
        self.type = eventType
        self.minArgs = 0
        self.maxArgs = 0
        self.arguments = {}
        self.argumentsByE1Instance = defaultdict(set) # event instance cache
    
    def addArgumentInstance(self, e1Id, argType, e1Type, e2Type):
        # add argument to event definition
        if argType not in self.arguments:
            self.arguments[argType] = Argument(argType)
        self.arguments[argType].targetTypes.add(e2Type)
        # add to event instance cache
        self.argumentsByE1Instance.add((argType, e1Type, e2Type))
        
    def countArguments(self):
        # Update argument limits for each argument definition
        for combination in self.argumentsByE1Instance.values():
            counts = defaultdict(int)
            counts[combination[0]] += 1
            for argType in counts.keys():
                #if argType not in self.arguments:
                #    self.arguments[argType] = Argument(argType)
                self.arguments[argType].addCount(counts[argType])
        # Update event definition argument limits
        self.minArgs = 0
        self.maxArgs = 0
        for argument in self.arguments.values():
            assert argument.min != -1
            assert argument.max != -1
            self.minArgs += argument.min
            self.maxArgs += argument.max
        # Reset event instance cache
        self.argumentsByE1Instance = defaultdict(set)
    
    def __repr__(self):
        s = "EVENT " + self.type + " [" + str(self.minArgs) + "," + str(self.maxArgs) + "]"
        for argType in sorted(self.arguments.keys()):
            s += "\t" + str(self.arguments[argType])
    
    def load(self, line):
        line = line.strip()
        if not line.startswith("EVENT"):
            raise Exception("Not an event definition line: " + line)
        tabSplits = line.split("\t")
        self.type = tabSplits[0].split()[1]
        self.minArgs, self.maxArgs = rangeToTuple(tabSplits[0].split()[1])
        for tabSplit in tabSplits[1:]:
            argument = Argument()
            argument.load(tabSplit)
        self.arguments[argument.type] = argument

class Argument():
    def __init__(self, argType=None):
        self.type = argType
        self.min = -1
        self.max = -1
        self.targetTypes = set()
    
    def addCount(self, count):
        if self.min == -1 or self.min > count:
            self.min = count
        if self.max == -1 or self.max < count:
            self.max = count

    def __repr__(self):
        return self.type + " [" + str(self.min) + "," + str(self.max) + "] " + ",".join(sorted(list(self.targetTypes)))
    
    def load(self, string):
        string = string.strip()
        self.type, limits, self.targetTypes = string.split()
        self.min, self.max = rangeToTuple(limits)
        self.targetTypes = set(self.targetTypes.split(","))

class Modifier():
    def __init__(self, modType=None):
        self.type = modType
        self.entityTypes = set()

    def __repr__(self):
        return "MODIFIER " + self.modType + "\t" + ",".join(sorted(list(self.entityTypes)))
    
    def load(self, line):
        line = line.strip()
        if not line.startswith("MODIFIER"):
            raise Exception("Not a modifier definition line: " + line)
        tabSplits = line.split("\t")
        self.type = tabSplits[0].split()[1]
        self.entityTypes = set(tabSplits[1].split(","))

class Relation():
    def __init__(self, relType=None):
        self.type = relType
        self.directed = None
        self.e1Types = set()
        self.e2Types = set()
        self.e1Role = None
        self.e2Role = None
            
    def addInstance(self, directed=None, e1Role=None, e2Role=None, id="undefined"):
        if self.directed == None: # no relation of this type has been seen yet
            self.directed = directed
        elif self.directed != directed:
            raise Exception("Conflicting relation directed-attribute (" + str(directed) + ")for already defined relation of type " + self.type + " in relation " + id)
        if self.e1Role == None: # no relation of this type has been seen yet
            self.e1Role = e1Role
        elif self.e1Role != e1Role:
            raise Exception("Conflicting relation e1Role-attribute (" + str(e1Role) + ") for already defined relation of type " + self.type + " in relation " + id)
        if self.e2Role == None: # no relation of this type has been seen yet
            self.e2Role = e2Role
        elif self.e2Role != e2Role:
            raise Exception("Conflicting relation e2Role-attribute (" + str(e2Role) + ") for already defined relation of type " + self.type + " in relation " + id)
    
    def load(self, line):
        line = line.strip()
        if not line.startswith("RELATION"):
            raise Exception("Not a relation definition line: " + line)
        tabSplits = line.split("\t")
        self.type = tabSplits[0].split()[1]
        self.directed = bool(tabSplits[0].split()[2])
        self.e1Role = tabSplits[1].split()[0]
        self.e1Types = set(tabSplits[1].split()[1].split(","))
        self.e2Role = tabSplits[2].split()[0]
        self.e2Types = set(tabSplits[2].split()[1].split(","))
    
    def __repr__(self):
        return "RELATION " + self.type + " " + str(self.directed) + "\t" + \
            self.e1Role + ",".join(sorted(list(self.e1Types))) + "\t" + \
            self.e2Role + ",".join(sorted(list(self.e2Types)))

class StructureAnalyzer():
    def __init__(self, defaultFileNameInModel="structure.txt"):
        self.modelFileName = defaultFileNameInModel
        self.reset()

    def isInitialized(self):
        return self.argLimits != None
    
    def addTarget(self, element):
        if element.get("given" != "True"):
            if element.tag == "interaction":
                targetClass = "INTERACTION"
            elif element.tag == "entity":
                targetClass = "ENTITY"
            else:
                raise Exception("Unsupported non-given element type " + element.tag)
            if targetClass not in self.targets:
                self.targets[targetClass] = Target(targetClass)
            self.targets[targetClass].targetTypes.add(element.get("type"))
    
    def addInteractionElement(self, interaction, entityById):
        self.addTarget(interaction)
        
        if not (interaction.get("event") == "True"):
            self.addRelation(interaction, entityById)
        else:
            e1Type = entityById[interaction.get("e1")].get("type")
            e2Type = entityById[interaction.get("e2")].get("type")
            if e1Type not in self.events:
                raise Exception("Argument " + interaction.get("id") + " of type " + interaction.get("type") + " for undefined event type " + e1Type)
            self.events[e1Type].addArgumentInstance(interaction.get("e1"), interaction.get("type"), e1Type, e2Type)
    
    def addRelation(self, interaction, entityById):
        relType = interaction.get("type")
        if relType not in self.relations:
            self.relations[relType] = Relation(relType)
        self.relations[relType].addInstance(interaction.get("directed") == "True", interaction.get("e1Role"), interaction.get("e2Role"), interaction.get("id"))
    
    def addEntityElement(self, entity, interactionsByE1):
        # Determine extraction target
        self.addTarget(entity)
        
        entityType = entity.get("type")
        if entity.get("event") == "True" or entity.get("id") in interactionsByE1:
            if entityType not in self.events:
                self.events[entityType] = Event(entityType)
        else:
            if entityType not in self.entities:
                self.entities[entityType] = Entity(entityType)
        
#         currentArgCounts = defaultdict(int)# copy.copy(countsTemplate)
#         for interaction in interactionsByE1[entity.get("id")]:
#             interactionTypes.add(interaction.get("type"))
#             currentArgCounts[interaction.get("type")] += 1
#             self.e2Types[entity.get("type")][interaction.get("type")].add(entityById[interaction.get("e2")].get("type"))
#         argCounts[entity.get("type")].add(self._dictToTuple(currentArgCounts)) # save only one example for each detected argument combination
        
        # check for modifiers
        for modType in ("speculation", "negation"):
            if (entity.get(modType) != None):
                if modType not in self.modifiers:
                    self.modifiers[modType] = Modifier(modType)
                self.modifiers[modType].entityTypes.add(entityType)
    
    def reset(self):
        self.relations = None
        self.entities = None
        self.events = None
        self.modifiers = None
        self.targets = None
    
    def _init(self):
        self.reset()
        self.relations = {}
        self.entities = {}
        self.events = {}
        self.modifiers = {}
        self.targets = {}
        
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
        return entityType in self.events
    
    def isEventArgument(self, edgeType):
        if edgeType in self.eventArgumentTypes:
            return True
        else:
            assert edgeType in self.relations, (edgeType, self.relations)
            return False
        
    def getArgLimits(self, entityType, argType):
        argument = self.events[entityType].arguments[argType]
        return (argument.min, argument.max)
    
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
        elementById = {}
        for element in document.getiterator(elementType):
            elementId = element.get("id")
            if elementId == None:
                raise Exception("Element " + elementType + " without id in document " + str(document.get("id")))
            if elementId in elementById:
                raise Exception("Duplicate " + elementType + " id " + str(elementId) + " in document " + str(document.get("id")))
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
    
#     def _dictToTuple(self, d):
#         tup = []
#         for key in sorted(d.keys()):
#             tup.append((key, d[key]))
#         return tuple(tup)
#     
#     def _tupToDict(self, tup):
#         d = {}
#         for pair in tup:
#             d[pair[0]] = pair[1]
#         return d
    
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
        if self.events == None: 
            raise Exception("No structure definition loaded")
        s = ""
        for entity in self.entities:
            s += str(entity) + "\n"
        for event in self.event:
            s += str(event) + "\n"
        for relation in self.relations:
            s += str(relation) + "\n"
        for modifier in self.modifiers:
            s += str(modifier) + "\n"
        for target in self.targets:
            s += str(target) + "\n"
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
        self._init()  
        if type(inputs) in types.StringTypes:
            inputs = [inputs]
        for xml in inputs:
            print >> sys.stderr, "Analyzing", xml
            xml = ETUtils.ETFromObj(xml)
            
            for document in xml.getiterator("document"):
                # Collect elements into dictionaries
                entityById = self._getElementDict(document, "entity")
                interactionsByE1 = defaultdict(list)
                for interaction in document.getiterator("interaction"):
                    interactionsByE1[interaction.get("e1")].append(interaction)
                # Add entity elements to analysis
                for entity in document.getiterator("entity"):
                    self.addEntityElement(entity, interactionsByE1)
                # Add interaction elements to analysis
                for interaction in document.getiterator("interaction"):
                    self.addInteractionElement(interaction, entityById)
                # Calculate event definition argument limits from event instances
                for event in self.events.values():
                    event.countArguments()

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
            
            