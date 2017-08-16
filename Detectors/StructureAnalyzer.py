#from Detector import Detector
import sys, os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict
import types
import collections

class StructureAnalyzer():
    def __init__(self, defaultFileNameInModel="structure.txt"):
        self.modelFileName = defaultFileNameInModel
        self.reset()
    
    # Initialization ##########################################################
    
    def reset(self):
        self.relations = None
        self.entities = None
        self.events = None
        self.modifiers = None
        self.targets = None
        self.givens = None
        # supporting analyses
        self.eventArgumentTypes = None
        self.edgeTypes = None
    
    def _init(self):
        self.reset()
        self.relations = {}
        self.entities = {}
        self.events = {}
        self.modifiers = {}
        self.targets = {}
        self.givens = {}

    def isInitialized(self):
        return self.events != None
    
    # analysis ################################################################
    
    def determineNonOverlappingTypes(self):
        print "================", "Non-overlapping types", "================"
        if hasattr(self, "typeMap"):
            print >> sys.stderr, "Using existing type map"
            return
        #groups = {}
        index = 0
        merged = {}
        for key in sorted(self.relations.keys()): #values():
#             firstPart = relation.type.split("(")[0].split("_")[0]
#             if firstPart not in groups:
#                 groups[firstPart] = []
#             groups[firstPart].append(relation)
            relation = self.relations[key]
            relation.permutations = [] #[zip(x,relation.e2Types) for x in itertools.permutations(relation.e1Types,len(relation.e2Types))]
            for e1Type in sorted(relation.e1Types):
                for e2Type in sorted(relation.e2Types):
                    relation.permutations.append((e1Type, e2Type))
            merged[index] = {"e1Types":relation.e1Types, 
                             "e2Types":relation.e2Types, 
                             "permutations":set(relation.permutations), 
                             "relations":[relation],
                             "categories":set([relation.type.split("_")[0]])}
            index += 1
        #print "Keys:", sorted(groups.keys())
        keys = sorted(merged.keys())
        mergedOne = True
        while mergedOne:
            mergedOne = False
            for key1 in keys:
                candidates = []
                for key2 in keys:
                    if key1 == key2:
                        continue
                    if not (len(merged[key1]["relations"]) >= 1 and len(merged[key2]["relations"]) >= 1):
                        continue
                    foundOverlap = False
                    for p in merged[key1]["permutations"]:
                        if p in merged[key2]["permutations"]:
                            foundOverlap = True
                            break
                    if foundOverlap:
                        continue
                    priority = 0
                    if len(merged[key1]["e1Types"].intersection(merged[key2]["e1Types"])) > 0:
                        priority += 1
                    if len(merged[key1]["e2Types"].intersection(merged[key2]["e2Types"])) > 0:
                        priority += 10
                    if len(merged[key1]["categories"].intersection(merged[key2]["categories"])) > 0:
                        priority += 100
                    candidates.append((priority, merged[key2]))
                if len(candidates) > 0:
                    candidates.sort(key=lambda x: x[0], reverse=True)
                    #print merged[key1]["relations"][0].type, [(x[0], [x.type for x in x[1]["relations"]]) for x in candidates]
                    best = candidates[0][1]
                    best["relations"].extend(merged[key1]["relations"])
                    merged[key1]["relations"] = []
                    for dataType in ("e1Types", "e2Types", "permutations", "categories"):
                        best[dataType] = best[dataType].union(merged[key1][dataType])
                    #merged[key1][1] = []
                    mergedOne = True
                    break
        
        self.typeMap = {"forward":{}, "reverse":{}}
        for key in sorted(merged.keys()):
            if len(merged[key]["relations"]) == 0:
                continue
            relTypes = [x.type for x in merged[key]["relations"]]
            shortId = str(key) + "-" +  "_".join(sorted(set([x.split("_")[0] for x in relTypes])))
            print key, relTypes, shortId
            for relation in merged[key]["relations"]:
                assert relation.type not in self.typeMap["forward"]
                self.typeMap["forward"][relation.type] = shortId
            assert shortId not in self.typeMap["reverse"]
            self.typeMap["reverse"][shortId] = relTypes
        print "--------------------------------------------------------"           
    
    def analyze(self, inputs, model=None, verbose=False):
        self._init()  
        if type(inputs) in types.StringTypes or not isinstance(inputs, collections.Sequence):
            inputs = [inputs]
        for xml in inputs:
            print >> sys.stderr, "Analyzing", xml
            xml = ETUtils.ETFromObj(xml)
            
            for document in xml.getiterator("document"):
                # Collect elements into dictionaries
                entityById = {}
                for entity in document.getiterator("entity"):
                    entityById[entity.get("id")] = entity
                interactions = []
                interactionsByE1 = defaultdict(list)
                for interaction in document.getiterator("interaction"):
                    interactions.append(interaction)
                    interactionsByE1[interaction.get("e1")].append(interaction)
                siteOfTypes = self.buildSiteOfMap(interactions, interactionsByE1, entityById)
                # Add entity elements to analysis
                for entity in document.getiterator("entity"):
                    self.addEntityElement(entity, interactionsByE1)
                # Add interaction elements to analysis
                for interaction in interactions:
                    self.addInteractionElement(interaction, entityById, siteOfTypes[interaction])
                # Calculate event definition argument limits from event instances
                for event in self.events.values():
                    event.countArguments()
        
        self._updateSupportingAnalyses()
        if verbose:
            print >> sys.stderr, self.toString()
        if model != None:
            self.save(model)
    
    def buildSiteOfMap(self, interactions, interactionsByE1, entityById):
        siteOfTypes = defaultdict(set)
        #interactionsByE2 = {}
        #for interaction in interactions:
        #    interactionsByE2[interaction.get("e2")] = interaction
        interactionById = {}
        for interaction in interactions:
            interactionById[interaction.get("id")] = interaction
        for interaction in interactions:
            if interaction.get("type") == "Site":
                if interaction.get("siteOf") != None: # annotated primary arguments
                    siteOfTypes[interaction].add(interactionById[interaction.get("siteOf")].get("type"))
                else:
                    triggerId = interaction.get("e1")
                    entityEntityId = interaction.get("e2")
                    siteParentProteinIds = set()
                    for interaction2 in interactionsByE1[entityEntityId]:
                        if interaction2.get("type") == "SiteParent":
                            siteParentProteinIds.add(interaction2.get("e2"))
                    for interaction2 in interactionsByE1[triggerId]:
                        if interaction2 == interaction or interaction2.get("Type") == "Site":
                            continue
                        if interaction2.get("e1") == triggerId and interaction2.get("e2") in siteParentProteinIds:
                            siteOfTypes[interaction].add(interaction2.get("type"))
        return siteOfTypes

    def addTarget(self, element):
        if element.get("given") != "True":
            self._addToGroup("TARGET", self.targets, element)
    
    def addGiven(self, element):
        if element.get("given") == "True":
            self._addToGroup("GIVEN", self.givens, element)
    
    def _addToGroup(self, groupName, groups, element):
        if element.tag == "interaction":
            elementClass = "INTERACTION"
        elif element.tag == "entity":
            elementClass = "ENTITY"
        else:
            raise Exception("Unsupported '" + groupName + "' element type " + element.tag)
        if elementClass not in groups:
            groups[elementClass] = Group(groupName, elementClass)
        groups[elementClass].targetTypes.add(element.get("type"))
    
    def addInteractionElement(self, interaction, entityById, siteOfTypes):
        self.addTarget(interaction)
        self.addGiven(interaction)
        
        if not (interaction.get("event") == "True"):
            self.addRelation(interaction, entityById)
        else:
            e1Type = entityById[interaction.get("e1")].get("type")
            e2Type = entityById[interaction.get("e2")].get("type")
            if e1Type not in self.events:
                raise Exception("Argument " + interaction.get("id") + " of type " + interaction.get("type") + " for undefined event type " + e1Type)
            self.events[e1Type].addArgumentInstance(interaction.get("e1"), interaction.get("type"), e1Type, e2Type, siteOfTypes)
    
    def addRelation(self, interaction, entityById):
        relType = interaction.get("type")
        if relType not in self.relations:
            self.relations[relType] = Relation(relType)
        e1Type = entityById[interaction.get("e1")].get("type")
        e2Type = entityById[interaction.get("e2")].get("type")
        self.relations[relType].addInstance(e1Type, e2Type, interaction.get("directed") == "True", interaction.get("e1Role"), interaction.get("e2Role"), interaction.get("id"))
    
    def addEntityElement(self, entity, interactionsByE1):
        # Determine extraction target
        self.addTarget(entity)
        self.addGiven(entity)
        
        entityType = entity.get("type")
        isEvent = entity.get("event") == "True"
        if not isEvent and entity.get("id") in interactionsByE1: # event can be also defined by simply having outgoing argument edges
            for interaction in interactionsByE1[entity.get("id")]:
                if interaction.get("event") == "True":
                    isEvent = True
                    break
        if isEvent:
            if entityType not in self.events:
                self.events[entityType] = Event(entityType)
            self.events[entityType].addTriggerInstance(entity.get("id"))
        else:
            if entityType not in self.entities:
                self.entities[entityType] = Entity(entityType)
        
        # check for modifiers
        for modType in ("speculation", "negation"):
            if (entity.get(modType) != None):
                if modType not in self.modifiers:
                    self.modifiers[modType] = Modifier(modType)
                self.modifiers[modType].entityTypes.add(entityType)
    
    def _updateSupportingAnalyses(self):
        self.eventArgumentTypes = set()
        self.edgeTypes = defaultdict(lambda:defaultdict(set))
        # Add relations to edge types
        for relation in self.relations.values():
            for e1Type in relation.e1Types:
                for e2Type in relation.e2Types:
                    self.edgeTypes[e1Type][e2Type].add(relation.type)
                    if not relation.directed:
                        self.edgeTypes[e2Type][e1Type].add(relation.type)
        # Process arguments
        for eventType in sorted(self.events.keys()):
            # Remove conflicting entities
            if eventType in self.entities:
                print >> sys.stderr, "Warning, removing ENTITY conflicting with EVENT for type " + eventType
                del self.entities[eventType]
            # Update analyses
            event = self.events[eventType]
            for argType in event.arguments:
                # Update set of known event argument types
                self.eventArgumentTypes.add(argType)
                # Add argument to edge types (argument is always directed)
                argument = event.arguments[argType]
                for e2Type in argument.targetTypes:
                    self.edgeTypes[eventType][e2Type].add(argType)
    
    # validation ##############################################################
            
    def getRelationRoles(self, relType):
        if relType not in self.relations:
            return None
        relation = self.relations[relType]
        if relation.e1Role == None and relation.e2Role == None:
            return None
        else:
            return (relation.e1Role, relation.e2Role)
    
    def hasEvents(self):
        return len(self.events) > 0
    
    def hasModifiers(self):
        return len(self.modifiers) > 0
    
    def getGroups(self, name):
        assert name in ["TARGET", "GIVEN"]
        if name == "TARGET":
            return self.targets
        else:
            return self.givens
    
    def hasGroupClass(self, group, elementClass):
        groups = self.getGroups(group)
        assert elementClass in ["INTERACTION", "ENTITY"]
        return elementClass in groups
    
    def hasGroupType(self, group, elementClass, elementType):
        if not self.hasTargetClass(elementClass):
            return False
        return elementType in self.getGroups(group)[elementClass].targetTypes
    
    def hasDirectedTargets(self):
        if "INTERACTION" not in self.targets: # no interactions to predict
            return False
        for event in self.events.values(): # look for event argument targets (always directed)
            for argType in event.arguments:
                if argType in self.targets["INTERACTION"].targetTypes:
                    return True
        for relType in self.relations: # look for directed relation targets
            relation = self.relations[relType]
            assert relation.directed in [True, False]
            if relation.directed and relType in self.targets["INTERACTION"].targetTypes:
                return True
        return False
        
    def isDirected(self, edgeType):
        if edgeType in self.eventArgumentTypes:
            return True
        else:
            relation = self.relations[edgeType]
            assert relation.directed in [True, False]
            return relation.directed
    
    def isEvent(self, entityType):
        return entityType in self.events
    
    def isEventArgument(self, edgeType):
        if edgeType in self.eventArgumentTypes:
            return True
        else:
            assert edgeType in self.relations, (edgeType, self.relations)
            return False
    
    def getArgSiteOfTypes(self, entityType, edgeType, strict=False):
        #if not edgeType in self.eventArgumentTypes:
        #    raise Exception("Edge type " + str(edgeType) + " is not an event argument and cannot be a site")
        if not entityType in self.events:
            if strict:
                raise Exception("No event of type " + str(entityType))
            return set()
        event = self.events[entityType]
        if not edgeType in event.arguments:
            if strict:
                raise Exception("Event of type " + str(entityType) + " cannot have an argument of type " + str(edgeType))
            return set()
        return self.events[entityType].arguments[edgeType].siteOfTypes
        
    def getArgLimits(self, entityType, argType):
        argument = self.events[entityType].arguments[argType]
        return (argument.min, argument.max)
    
    def getValidEdgeTypes(self, e1Type, e2Type, forceUndirected=False):
        assert type(e1Type) in types.StringTypes
        assert type(e2Type) in types.StringTypes
        if self.events == None: 
            raise Exception("No structure definition loaded")
        validEdgeTypes = set()
        if e1Type in self.edgeTypes and e2Type in self.edgeTypes[e1Type]:
            if forceUndirected:
                validEdgeTypes = self.edgeTypes[e1Type][e2Type]
            else:
                return self.edgeTypes[e1Type][e2Type] # not a copy, so careful with using the returned set!
        if forceUndirected and e2Type in self.edgeTypes and e1Type in self.edgeTypes[e2Type]:
            validEdgeTypes = validEdgeTypes.union(self.edgeTypes[e2Type][e1Type])
        return validEdgeTypes
    
    def isValidEntity(self, entity):
        if entity.get("type") in self.entities and entity.get("event") != "True":
            return True
        else:
            return False
    
    def isValidRelation(self, interaction, entityById=None, issues=None):
        if interaction.get("type") not in self.relations:
            if issues != None: issues["INVALID_TYPE:"+interaction.get("type")] += 1
            return False
        relDef = self.relations[interaction.get("type")]
        e1 = interaction.get("e1")
        if e1 not in entityById:
            if issues != None: issues["MISSING_E1:"+interaction.get("type")] += 1
            return False
        e2 = interaction.get("e2")
        if e2 not in entityById:
            if issues != None: issues["MISSING_E2:"+interaction.get("type")] += 1
            return False
        e1 = entityById[e1]
        e2 = entityById[e2]
        if e1.get("type") in relDef.e1Types and e2.get("type") in relDef.e2Types:
            return True
        elif (not relDef.directed) and e1.get("type") in relDef.e2Types and e2.get("type") in relDef.e1Types:
            return True
        else:
            if issues != None: issues["INVALID_TARGET:"+interaction.get("type")] += 1
            return False
    
    def isValidArgument(self, interaction, entityById=None, issues=None):
        if interaction.get("type") not in self.eventArgumentTypes:
            if issues != None: issues["INVALID_TYPE:"+interaction.get("type")] += 1
            return False
        e1 = interaction.get("e1")
        if e1 not in entityById:
            if issues != None: issues["MISSING_E1:"+interaction.get("type")] += 1
            return False
        e1 = entityById[e1]
        if e1.get("type") not in self.events:
            if issues != None: issues["INVALID_EVENT_TYPE:"+interaction.get("type")] += 1
            return False
        eventDef = self.events[e1.get("type")]
        if interaction.get("type") not in eventDef.arguments:
            if issues != None: issues["INVALID_TYPE:"+interaction.get("type")] += 1
            return False
        argDef = eventDef.arguments[interaction.get("type")]
        e2 = interaction.get("e2")
        if e2 not in entityById:
            if issues != None: issues["MISSING_E2:"+interaction.get("type")] += 1
            return False
        e2 = entityById[e2]
        if e2.get("type") in argDef.targetTypes:
            return True
        else:
            if issues != None: issues["INVALID_TARGET:"+interaction.get("type")+"->"+e2.get("type")] += 1
            return False
    
    def isValidEvent(self, entity, args=None, entityById=None, noUpperLimitBeyondOne=True, issues=None):
        if args == None:
            args = []
        if type(entity) in types.StringTypes:
            entityType = entity
        else:
            entityType = entity.get("type")
        valid = True
        # check type
        if entityType not in self.events:
            if issues != None: 
                issues["INVALID_TYPE:"+entityType] += 1
            return False
        # check validity of proposed argument count
        eventDefinition = self.events[entityType]
        if len(args) < eventDefinition.minArgs:
            if issues != None: 
                issues["ARG_COUNT_TOO_LOW:"+entityType] += 1
                valid = False
            else:
                return False
        if (not noUpperLimitBeyondOne) and len(args) > eventDefinition.maxArgs:
            if issues != None: 
                issues["ARG_COUNT_TOO_HIGH:"+entityType] += 1
                valid = False
            else:
                return False
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
        argumentDefinitions = eventDefinition.arguments
        for argType in argTypes:
            # Check if valid argument
            if argType not in argumentDefinitions:
                if issues != None:
                    issues["INVALID_ARG_TYPE:"+entityType+"."+argType] += 1
                    valid = False
                else:
                    return False
            else:
                argDef = argumentDefinitions[argType]
                # Check minimum limit
                if argTypeCounts[argType] < argDef.min: # check for minimum number of arguments
                    if issues != None:
                        issues["TOO_FEW_ARG:"+entityType+"."+argType] += 1
                        valid = False
                    else:
                        return False
                # Check maximum limit
                # noUpperLimitBeyondOne = don't differentiate arguments beyond 0, 1 or more than one.
                if (not noUpperLimitBeyondOne) and argTypeCounts[argType] > argDef.max: # check for maximum number of arguments
                    if issues != None:
                        issues["TOO_MANY_ARG:"+entityType+"."+argType] += 1
                        valid = False
                    else:
                        return False
                # Check validity of E2 types
                for e2Type in argE2Types[argType]:
                    if e2Type not in argDef.targetTypes:
                        if issues != None:
                            issues["INVALID_ARG_TARGET:"+entityType+"."+argType+":"+e2Type] += 1
                            valid = False
                        else:
                            return False
        # check that no required arguments are missing
        for argDef in argumentDefinitions.values():
            if argDef.type not in argTypes: # this type of argument is not part of the proposed event
                if argDef.min > 0: # for arguments not part of the event, the minimum limit must be zero
                    if issues != None:
                        issues["MISSING_ARG:"+entityType+"."+argDef.type] += 1
                        valid = False
                    else:
                        return False
        return valid
    
    def _removeNestedElement(self, root, element):
        for child in root:
            if child == element:
                root.remove(child)
                break
            else:
                self._removeNestedElement(child, element)
    
    def validate(self, xml, printCounts=True, simulation=False, debug=False):
        counts = defaultdict(int)
        for document in xml.getiterator("document"):
            while (True):
                # Collect elements into dictionaries
                entityById = {}
                entities = []
                for entity in document.getiterator("entity"):
                    entityById[entity.get("id")] = entity
                    entities.append(entity)
                interactionsByE1 = defaultdict(list)
                arguments = []
                relations = []
                keptInteractions = set()
                keptEntities = set()
                for interaction in document.getiterator("interaction"):
                    interactionsByE1[interaction.get("e1")].append(interaction)
                    if interaction.get("event") == "True":
                        arguments.append(interaction)
                    else:
                        relations.append(interaction)
                
                for relation in relations:
                    issues = defaultdict(int)
                    if self.isValidRelation(relation, entityById, issues):
                        keptInteractions.add(relation)
                    else:
                        counts["RELATION:"+relation.get("type")] += 1
                        if debug: print >> sys.stderr, "Removing invalid relation", issues
                
                for argument in arguments:
                    issues = defaultdict(int)
                    if self.isValidArgument(argument, entityById, issues):
                        keptInteractions.add(argument)
                    else:
                        counts["ARG:"+argument.get("type")] += 1
                        if debug: print >> sys.stderr, "Removing invalid argument", argument.get("id"), argument.get("type"), issues
                
                for entityId in sorted(entityById):
                    entity = entityById[entityId]
                    entityType = entity.get("type")
                    if entityType in self.events:
                        issues = defaultdict(int)
                        eventArgs = []
                        for arg in interactionsByE1[entityId]:
                            if arg in keptInteractions:
                                eventArgs.append(arg)
                        if self.isValidEvent(entity, eventArgs, entityById, issues=issues):
                            keptEntities.add(entity)
                        else:
                            counts["EVENT:"+entity.get("type")] += 1
                            if debug: print >> sys.stderr, "Removing invalid event", entityId, issues
                    elif entityType in self.entities:
                        keptEntities.add(entity)
                    else:
                        counts["ENTITY:"+entity.get("type")] += 1
                        if debug: print >> sys.stderr, "Removing unknown entity", entityId
            
                # clean XML
                interactions = arguments + relations
                if not simulation:
                    for interaction in interactions:
                        if interaction not in keptInteractions:
                            self._removeNestedElement(document, interaction)
                    for entityId in sorted(entityById):
                        entity = entityById[entityId]
                        if entity not in keptEntities:
                            self._removeNestedElement(document, entity)
                
                if len(interactions) == len(keptInteractions) and len(entities) == len(keptEntities):
                    break

        print >> sys.stderr, "Validation removed:", counts
        return counts
    
    # Saving and Loading ######################################################
    
    def toString(self):
        if self.events == None: 
            raise Exception("No structure definition loaded")
        s = ""
        for entity in sorted(self.entities):
            s += str(self.entities[entity]) + "\n"
        for event in sorted(self.events):
            s += str(self.events[event]) + "\n"
        for relation in sorted(self.relations):
            s += str(self.relations[relation]) + "\n"
        for modifier in sorted(self.modifiers):
            s += str(self.modifiers[modifier]) + "\n"
        for target in sorted(self.targets):
            s += str(self.targets[target]) + "\n"
        for given in sorted(self.givens):
            s += str(self.givens[given]) + "\n"
        return s
    
    def save(self, model, filename=None):
        if filename == None:
            filename = self.modelFileName
        if model != None:
            if hasattr(self, "typeMap"):
                print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
                self.saveTypeMap(model, filename + "_type_map.json")
            filename = model.get(filename, True)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        f = open(filename, "wt")
        f.write(self.toString())
        f.close()
        if model != None:
            model.save()
    
    def saveTypeMap(self, model, filename):
        filename = model.get(filename, addIfNotExist=True)
        print >> sys.stderr, "Saving StructureAnalyzer.typeMap to", filename
        f = open(filename, "wt")
        json.dump(self.typeMap, f, indent=4)
        f.close()
    
    def loadTypeMap(self, model, filename):
        filename = model.get(filename, defaultIfNotExist=None)
        if filename:
            f = open(filename, "rt")
            self.typeMap = json.load(f)
            f.close()
    
    def load(self, model, filename=None):
        # load definitions
        if filename == None:
            filename = self.modelFileName
        if model != None:
            self.loadTypeMap(model, filename + "_type_map.json")
            filename = model.get(filename)
        f = open(filename, "rt")
        lines = f.readlines()
        f.close()
        # initialize
        self._init()
        # add definitions
        for line in lines:
            if line.startswith("ENTITY"):
                definition = Entity()
                definitions = self.entities
            elif line.startswith("EVENT"):
                definition = Event()
                definitions = self.events
            elif line.startswith("RELATION"):
                definition = Relation()
                definitions = self.relations
            elif line.startswith("MODIFIER"):
                definition = Modifier()
                definitions = self.modifiers
            elif line.startswith("TARGET"):
                definition = Group("TARGET")
                definitions = self.targets
            elif line.startswith("GIVEN"):
                definition = Group("GIVEN")
                definitions = self.givens
            else:
                raise Exception("Unknown definition line: " + line.strip())
                
            definition.load(line)
            definitions[definition.type] = definition
        
        self._updateSupportingAnalyses()

def rangeToTuple(string):
    assert string.startswith("["), string
    assert string.endswith("]"), string
    string = string.strip("[").strip("]")
    begin, end = string.split(",")
    begin = int(begin)
    end = int(end)
    return (begin, end)

class Group():
    def __init__(self, name, targetClass=None):
        self.name = name
        if targetClass != None:
            assert targetClass in ["INTERACTION", "ENTITY"]
        self.type = targetClass
        self.targetTypes = set()
    
    def __repr__(self):
        return self.name + " " + self.type + "\t" + ",".join(sorted(list(self.targetTypes)))
    
    def load(self, line):
        line = line.strip()
        if not line.startswith(self.name):
            raise Exception("Not a '" + self.name + "' definition line: " + line)
        tabSplits = line.split("\t")
        self.type = tabSplits[0].split()[1]
        assert self.type in ["INTERACTION", "ENTITY"]
        self.targetTypes = set(tabSplits[1].split(","))

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
        self.minArgs = -1
        self.maxArgs = -1
        self.arguments = {}
        self._argumentsByE1Instance = defaultdict(lambda:defaultdict(int)) # event instance cache
        self._firstInstanceCache = True
    
    def addTriggerInstance(self, entityId):
        self._argumentsByE1Instance[entityId] = defaultdict(int)
    
    def addArgumentInstance(self, e1Id, argType, e1Type, e2Type, siteOfTypes):
        # add argument to event definition
        if argType not in self.arguments:
            argument = Argument(argType)
            if not self._firstInstanceCache: # there have been events before but this argument has not been seen
                argument.min = 0
            self.arguments[argType] = argument
        if siteOfTypes != None and len(siteOfTypes) > 0:
            self.arguments[argType].siteOfTypes = self.arguments[argType].siteOfTypes.union(siteOfTypes)
        self.arguments[argType].targetTypes.add(e2Type)
        # add to event instance cache
        self._argumentsByE1Instance[e1Id][argType] += 1
        
    def countArguments(self):
        # Update argument limits for each argument definition
        for eventInstance in self._argumentsByE1Instance.values():
            for argType in self.arguments: # check all possible argument types for each event instance
                if argType in eventInstance:
                    self.arguments[argType].addCount(eventInstance[argType])
                else: # argument type does not exist in this event instance
                    self.arguments[argType].addCount(0) 
            # Update event definition argument limits
            totalArgs = sum(eventInstance.values())
            if self.minArgs == -1 or self.minArgs > totalArgs:
                self.minArgs = totalArgs
            if self.maxArgs == -1 or self.maxArgs < totalArgs:
                self.maxArgs = totalArgs
        
        # Set valid min and max for events with no arguments
        if self.minArgs == -1:
            self.minArgs = 0
        if self.maxArgs == -1:
            self.maxArgs = 0
            
        # Reset event instance cache
        self._argumentsByE1Instance = defaultdict(lambda:defaultdict(int))
        self._firstInstanceCache = False
    
    def __repr__(self):
        s = "EVENT " + self.type + " [" + str(self.minArgs) + "," + str(self.maxArgs) + "]"
        for argType in sorted(self.arguments.keys()):
            s += "\t" + str(self.arguments[argType])
        return s
    
    def load(self, line):
        line = line.strip()
        if not line.startswith("EVENT"):
            raise Exception("Not an event definition line: " + line)
        tabSplits = line.split("\t")
        self.type = tabSplits[0].split()[1]
        for tabSplit in tabSplits[1:]:
            argument = Argument()
            argument.load(tabSplit)
            self.arguments[argument.type] = argument
        # Define maximum and minimum depending on model
        if "[" in tabSplits[0]:
            self.minArgs, self.maxArgs = rangeToTuple(tabSplits[0].split()[2])
        else: # old model file
            for argument in self.arguments.values():
                if self.minArgs == -1 or (self.minArgs == 0 and argument.min > 0) or (argument.min > 0 and argument.min < self.minArgs):
                    self.minArgs = argument.min
            if self.minArgs == -1:
                self.minArgs = 0
            self.maxArgs = 999
            print >> sys.stderr, "Warning, EVENT " + self.type + " does not have argument limits. Possibly using a model file from version <2.2. Argument limits set to [" + str(self.minArgs) + "-" + str(self.maxArgs) + "]."

class Argument():
    def __init__(self, argType=None):
        self.type = argType
        self.min = -1
        self.max = -1
        self.targetTypes = set()
        self.siteOfTypes = set()
    
    def addCount(self, count):
        if self.min == -1 or self.min > count:
            self.min = count
        if self.max == -1 or self.max < count:
            self.max = count

    def __repr__(self):
        s = self.type
        if len(self.siteOfTypes) > 0:
            s += " {" + ",".join(sorted(list(self.siteOfTypes))) + "}"
        return s + " [" + str(self.min) + "," + str(self.max) + "] " + ",".join(sorted(list(self.targetTypes)))
    
    def load(self, string):
        splits = string.strip().split()
        self.type = splits[0]
        assert len(splits) in (3,4), string
        if len(splits) == 4:
            assert splits[1].startswith("{") and splits[1].endswith("}"), string
            self.siteOfTypes = set(splits[1].strip("{").strip("}").split(","))
        self.min, self.max = rangeToTuple(splits[1 + len(splits) - 3])
        self.targetTypes = set(splits[2 + len(splits) - 3].split(","))

class Modifier():
    def __init__(self, modType=None):
        self.type = modType
        self.entityTypes = set()

    def __repr__(self):
        return "MODIFIER " + self.type + "\t" + ",".join(sorted(list(self.entityTypes)))
    
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
            
    def addInstance(self, e1Type, e2Type, directed=None, e1Role=None, e2Role=None, id="undefined"):
        self.e1Types.add(e1Type)
        self.e2Types.add(e2Type)
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
        if len(tabSplits[0].split()) == 3:
            self.type = tabSplits[0].split()[1]
            self.directed = tabSplits[0].split()[2] == "directed"
            offset = 0
        else:
            print >> sys.stderr, "Warning, RELATION " + tabSplits[0] + " uses model file format <2.2."
            self.type = tabSplits[0].split()[1]
            self.directed = tabSplits[1] == "directed"
            offset = 1
        if " " in tabSplits[1+offset]:
            self.e1Role = tabSplits[1+offset].split()[0]
            self.e1Types = set(tabSplits[1+offset].split()[1].split(","))
        else:
            self.e1Types = set(tabSplits[1+offset].split(","))
        if " " in tabSplits[2+offset]:
            self.e2Role = tabSplits[2+offset].split()[0]
            self.e2Types = set(tabSplits[2+offset].split()[1].split(","))
        else:
            self.e2Types = set(tabSplits[2+offset].split(","))
    
    def __repr__(self):
        s = "RELATION " + self.type + " "
        if self.directed:
            s += "directed\t"
        else:
            s += "undirected\t"
        if self.e1Role != None:
            s += self.e1Role + " "
        s += ",".join(sorted(list(self.e1Types))) + "\t"
        if self.e2Role != None:
            s += self.e2Role + " "
        s += ",".join(sorted(list(self.e2Types)))
        return s

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
    print >> sys.stderr, "--- Structure Analysis ----"
    print >> sys.stderr, s.toString()
    if options.validate != None:
        print >> sys.stderr, "--- Validation ----"
        xml = ETUtils.ETFromObj(options.validate)
        s.validate(xml, simulation=False, debug=options.debug)
        if options.output != None:
            ETUtils.write(xml, options.output)
    elif options.output != None:
        print >> sys.stderr, "Structure analysis saved to", options.output
        s.save(None, options.output)
