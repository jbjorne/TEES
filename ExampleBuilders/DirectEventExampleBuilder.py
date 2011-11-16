import sys, types, random
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
from PathGazetteer import PathGazetteer
from Core.Gazetteer import Gazetteer
#import networkx as NX
import Graph.networkx_v10rc1 as NX10
import combine
import Stemming.PorterStemmer as PorterStemmer

class DirectEventExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","directed","headsOnly"], length=None, types=[], featureSet=None, classSet=None, gazetteer=None, pathGazetteer=None, negFrac=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        if gazetteer != None:
            print >> sys.stderr, "Loading gazetteer from", gazetteer
            self.gazetteer=Gazetteer.loadGztr(gazetteer)
        else:
            print >> sys.stderr, "No gazetteer loaded"
            self.gazetteer=None
        
        self.pathGazetteer=None
        self.pathGazetteerDependencies = None
        self.pathGazetteerPairs = None
        if pathGazetteer != None:
            print >> sys.stderr, "Loading path gazetteer from", pathGazetteer
            self.pathGazetteer=PathGazetteer.load(pathGazetteer)
            self.pathGazetteerDependencies = PathGazetteer.getDependencies(self.pathGazetteer)
            self.pathGazetteerPairs = PathGazetteer.getPairs(self.pathGazetteer)
        else:
            print >> sys.stderr, "No path gazetteer loaded"
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        self.styles = style
        self.negFrac = negFrac
        print >> sys.stderr, "Downsampling negatives to", negFrac
        self.negRand = random.Random()
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        if True:#"noAnnType" in self.styles:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if "noMasking" in self.styles:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if "maxFeatures" in self.styles:
            self.multiEdgeFeatureBuilder.maximum = True
        
        self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)
        #self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        #if "ontology" in self.styles:
        #    self.multiEdgeFeatureBuilder.ontologyFeatureBuilder = BioInferOntologyFeatureBuilder(self.featureSet)
        self.pathLengths = length
        assert(self.pathLengths == None)
        self.types = types
        
        self.eventsByOrigId = {}
        self.headTokensByOrigId = {}
        self.interSentenceEvents = set()
        
        self.examplesByEventOrigId = {}
        self.skippedByType = {}
        self.skippedByTypeAndReason = {}
        self.builtByType = {}
        
        self.gazMatchCache = {}
        
        #self.outFile = open("exampleTempFile.txt","wt")

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteer=None, pathGazetteer=None, negFrac=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = DirectEventExampleBuilder(style=style, classSet=classSet, featureSet=featureSet, gazetteer=gazetteer, pathGazetteer=pathGazetteer, negFrac=negFrac)
        else:
            e = DirectEventExampleBuilder(classSet=classSet, featureSet=featureSet, gazetteer=gazetteer, pathGazetteer=pathGazetteer, negFrac=negFrac)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
        e.printStats()
    
    def getGazetteerMatch(self, string):
        if string in self.gazMatchCache:
            return self.gazMatchCache[string]
        
        origString = string
        if "stem_gazetteer" in self.styles:
            string = PorterStemmer.stem(string)
        
        if string in self.gazetteer:
            self.gazMatchCache[origString] = string
            return string
        elif string.find("-") != -1:
            replaced = string.replace("-","")
        else:
            self.gazMatchCache[origString] = None
            return None
        
        if replaced in self.gazetteer:
            self.gazMatchCache[origString] = replaced
            return replaced
        else:
            splitted = string.rsplit("-",1)[-1]
        
        if splitted  in self.gazetteer:
            self.gazMatchCache[origString] = splitted
            return splitted
        else:
            self.gazMatchCache[origString] = None
            return None
    
    def isInGazetteer(self, string):
        return self.getGazetteerMatch(string) != None
    
    def printStats(self):
        eventsByType = {}
        for event in self.eventsByOrigId.values():
            eventsByType[event.get("type")] = eventsByType.get(event.get("type"),0) + 1
        
        f = open("missed-events", "wt")
        missedEvents = {}
        for key in self.examplesByEventOrigId.keys():
            if self.examplesByEventOrigId[key] == 0:
                if not missedEvents.has_key(self.eventsByOrigId[key].get("type")):
                    missedEvents[self.eventsByOrigId[key].get("type")] = []
                missedEvents[self.eventsByOrigId[key].get("type")].append(key)

        for key in sorted(missedEvents.keys()):
            f.write(key + "\n")
            for id in sorted(missedEvents[key]):
                f.write(" " + id + " ")
                if id in self.interSentenceEvents:
                    f.write("intersentence ")
                text = self.headTokensByOrigId[id].get("text").lower()
                if not self.isInGazetteer(text):
                    text = self.headTokensByOrigId[id].get("text").lower()
                    if "stem_gazetteer" in self.styles:
                        stemmed = PorterStemmer.stem(text)
                    f.write("not-in-gazetteer (" + text + " / " + stemmed +")" )
                f.write("\n")
        f.close()

        print >> sys.stderr, "Example selection missed events (other, intersentence, non-gazetteer)"
        for key in sorted(eventsByType.keys()):
            inter = 0
            other = 0
            nongaz = 0
            if missedEvents.has_key(key):
                for id in missedEvents[key]:
                    tokText = self.headTokensByOrigId[id].get("text").lower()
                    if id in self.interSentenceEvents:
                        inter += 1
                    elif not self.isInGazetteer(tokText):
                        nongaz += 1
                    else:
                        other += 1
            if inter == other == nongaz == 0:
                print >> sys.stderr, " " + key + " (" + str(eventsByType[key]) + "): missed none"
            else:
                print >> sys.stderr, " " + key + " (" + str(eventsByType[key]) + "): " + str(other) + ", " + str(inter) + ", " + str(nongaz)
        print >> sys.stderr, "Example generation (total, built/skipped)"
        for key in sorted(list(set(self.skippedByType.keys() + self.builtByType.keys()))):
            string = " " + key + ": (" + str(self.builtByType.get(key,0)+self.skippedByType.get(key,0)) + ", " + str(self.builtByType.get(key,0)) + "/" + str(self.skippedByType.get(key,0)) + ") ["
            for key2 in sorted(self.skippedByTypeAndReason[key].keys()):
                string += key2 + ":" + str(self.skippedByTypeAndReason[key][key2]) + " "
            string += "]"
            print >> sys.stderr, string
    
    def definePredictedValueRange(self, sentences, elementName):
        self.multiEdgeFeatureBuilder.definePredictedValueRange(sentences, elementName)                        
    
    def getPredictedValueRange(self):
        return self.multiEdgeFeatureBuilder.predictedRange
    
    def preProcessExamples(self, allExamples):
        if "normalize" in self.styles:
            print >> sys.stderr, " Normalizing feature vectors"
            ExampleUtils.normalizeFeatureVectors(allExamples)
        return allExamples   
    
#    def isPotentialGeniaInteraction(self, e1, e2):
#        if e1.get("isName") == "True" and e2.get("isName") == "True":
#            return False
#        elif e1.get("isName") == "True" and e2.get("isName") == "False":
#            return False
#        else:
#            return True
    
    def getArgumentEntities(self, sentenceGraph, entityNode):
        eId = entityNode.get("id")
        assert(eId != None)
        themeNodes = []
        causeNodes = []
        for edge in sentenceGraph.interactions:
            if edge.get("e1") == eId:
                edgeType = edge.get("type")
                assert(edgeType in ["Theme", "Cause"]), edgeType
                if edgeType == "Theme":
                    themeNodes.append( sentenceGraph.entitiesById[edge.get("e2")] )
                elif edgeType == "Cause":
                    causeNodes.append( sentenceGraph.entitiesById[edge.get("e2")] )
        return themeNodes, causeNodes
    
    def makeGSEvents(self, sentenceGraph):
        self.namedEntityHeadTokenIds = set()
        self.gsEvents = {} # [token]->[event-type]->[1-n argument sets]
        for token in sentenceGraph.tokens:
            self.gsEvents[token] = {}
        
        for entity in sentenceGraph.entities:
            if entity.get("type") == "neg":
                continue
            elif entity.get("isName") == "True":
                self.namedEntityHeadTokenIds.add(sentenceGraph.entityHeadTokenByEntity[entity].get("id"))
                continue
            
            eId = entity.get("id")
            eOrigId = entity.get("origId")
            assert not self.eventsByOrigId.has_key(eOrigId)
            self.eventsByOrigId[eOrigId] = entity
            if not self.examplesByEventOrigId.has_key(eOrigId):
                self.examplesByEventOrigId[eOrigId] = 0
            if len(sentenceGraph.interSentenceInteractions) > 0:
                for interaction in sentenceGraph.interSentenceInteractions:
                    if interaction.get("e1") == eId:
                        self.interSentenceEvents.add(eOrigId)
            eType = entity.get("type")
            arguments = set()
            for interaction in sentenceGraph.interactions:
                if interaction.get("e1") == eId:
                    e2 = sentenceGraph.entitiesById[interaction.get("e2")]
                    e2TokenId = sentenceGraph.entityHeadTokenByEntity[e2].get("id")
                    arguments.add( (interaction.get("type"), e2TokenId ) )
                    #arguments.add( (interaction.get("type"), interaction.get("e2") ) )
            arguments = tuple(sorted(list(arguments)))
            eHeadToken = sentenceGraph.entityHeadTokenByEntity[entity]
            self.headTokensByOrigId[eOrigId] = eHeadToken
            if not self.gsEvents[eHeadToken].has_key(eType):
                self.gsEvents[eHeadToken][eType] = {}
            if len(arguments) > 0:
                if not self.gsEvents[eHeadToken][eType].has_key(arguments):
                    self.gsEvents[eHeadToken][eType][arguments] = []
                self.gsEvents[eHeadToken][eType][arguments].append(eOrigId)
    
    def getGSEventType(self, sentenceGraph, eHeadToken, themeTokens, causeTokens):
        #eHeadToken = sentenceGraph.entityHeadTokenByEntity[entity]
        #eType = entity.get("type")
        if len(self.gsEvents[eHeadToken]) == 0:
            return "neg", []
            
        argumentSet = set()
        for themeNode in themeTokens:
            if themeNode != None:
                argumentSet.add( ("Theme", themeNode.get("id")) )
        for causeNode in causeTokens:
            if causeNode != None:
                argumentSet.add( ("Cause", causeNode.get("id")) )
        argumentSet = tuple(sorted(list(argumentSet)))
        
        gsTypes = set()
        eventIds = []
        for eventType in sorted(self.gsEvents[eHeadToken].keys()):
            if argumentSet in self.gsEvents[eHeadToken][eventType].keys():
                gsTypes.add(eventType)
                eventIds.extend(self.gsEvents[eHeadToken][eventType][argumentSet])
        
        if len(gsTypes) == 0:
            return "neg", eventIds
        elif len(gsTypes) == 1:
            return list(gsTypes)[0], eventIds
        else:
            gsTypes = sorted(list(gsTypes))
            string = gsTypes[0]
            for gsType in gsTypes[1:]:
                string += "---" + gsType
            return string, eventIds

    def nxMultiDiGraphToUndirected(self, graph):
        undirected = NX10.MultiGraph(name=graph.name)
        undirected.add_nodes_from(graph)
        undirected.add_edges_from(graph.edges_iter())
        return undirected
                        
    def buildExamples(self, sentenceGraph):
        self.makeGSEvents(sentenceGraph)
        self.multiEdgeFeatureBuilder.setFeatureVector(resetCache=True)
        self.triggerFeatureBuilder.initSentence(sentenceGraph)
        
        examples = []
        exampleIndex = 0
        
        #undirected = sentenceGraph.dependencyGraph.to_undirected()
        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        
        eventTokens = []
        nameTokens = []
        gazCategories = {None:{"neg":-1}}
        #stems = {}
        for token in sentenceGraph.tokens:
            gazText = self.getGazetteerMatch(token.get("text").lower())
            if gazText != None:
                gazCategories[token] = self.gazetteer[gazText]
            else:
                gazCategories[token] = {"neg":-1}
            
            if token.get("id") in self.namedEntityHeadTokenIds:
                nameTokens.append(token)
            elif gazText != None:
                eventTokens.append(token)
        allTokens = eventTokens + nameTokens
        
        #if len(nameTokens) == 0: # there can be no events in this sentence
        #    self.gsEvents = None
        #    return []
        
        for token in eventTokens:
            #gazCategories = self.gazetteer[token.get("text").lower()]
            #print token.get("text").lower(), gazCategories
            
            #multiargument = False
            potentialRegulation = False
            potentialBinding = False
            for key in gazCategories[token].keys():
                if key in ["Regulation","Positive_regulation","Negative_regulation"]:
                    #multiargument = True
                    potentialRegulation = True
                    break
            for key in gazCategories[token].keys():
                if key in ["Binding"]:
                    #multiargument = True
                    potentialBinding = True
                    break
            
            if potentialRegulation:
                combinations = combine.combine(allTokens, allTokens+[None])
            else:
                combinations = []
                for t2 in nameTokens: #allTokens:
                    combinations.append( (t2, None) )
            
            if potentialBinding:
                for i in range(len(nameTokens) - 1):
                    for j in range(i+1, len(nameTokens)):
                        combinations.append( ((nameTokens[i],nameTokens[j]), None) )
                
            for combination in combinations:
                theme2Binding = False
                if type(combination[0]) == types.ListType or type(combination[0]) == types.TupleType:
                    theme2Binding = True
                    categoryName, eventIds = self.getGSEventType(sentenceGraph, token, combination[0], [combination[1]])
                else:
                    categoryName, eventIds = self.getGSEventType(sentenceGraph, token, [combination[0]], [combination[1]])
                
                for id in eventIds:
                    self.examplesByEventOrigId[id] += 1
                

                skip = False
                s = self.skippedByTypeAndReason
                if not s.has_key(categoryName):
                    s[categoryName] = {}
                if gazCategories[token].get("neg",-1) > 0.99:
                    pass
                if combination[0] == combination[1]:
                    pass #skip = True
                if combination[0] == token or combination[1] == token:
                    if theme2Binding or gazCategories[combination[0]].get("Positive_regulation",-1) < 0:
                        skip = True
                        s[categoryName]["duparg"] = s[categoryName].get("duparg", 0) + 1
                if combination[0] == None and combination[1] == None:
                    skip = True
                    s[categoryName]["noncmb"] = s[categoryName].get("noncmb", 0) + 1
                
                validCat = self.isValidEvent(paths, sentenceGraph, token, combination)
                if validCat != "OK": #not self.isValidEvent(paths, sentenceGraph, token, combination):
                    skip = True
                    #s[categoryName]["valid"] = s[categoryName].get("valid", 0) + 1
                    s[categoryName][validCat] = s[categoryName].get(validCat, 0) + 1
                
                if len(nameTokens) == 0:
                    skip = True
                    s[categoryName]["non"] = s[categoryName].get("non", 0) + 1
                
                if theme2Binding:
                    if gazCategories[combination[0][0]].get("neg",-1) > 0.99 or gazCategories[combination[0][1]].get("neg",-1) > 0.99:
                        skip = True
                        s[categoryName]["gazarg"] = s[categoryName].get("gazarg", 0) + 1
                else:
                    if gazCategories[combination[0]].get("neg",-1) > 0.99 or gazCategories[combination[1]].get("neg",-1) > 0.99:
                        skip = True
                        s[categoryName]["gazarg"] = s[categoryName].get("gazarg", 0) + 1
                
                if (skip and self.negFrac == None) or (skip and self.negFrac != None and categoryName == "neg"):
                    self.skippedByType[categoryName] = self.skippedByType.get(categoryName, 0) + 1
                else:
                    if self.negFrac == None or categoryName != "neg" or (categoryName == "neg" and self.negRand.random() < self.negFrac):
                        self.builtByType[categoryName] = self.builtByType.get(categoryName, 0) + 1
                        if theme2Binding:
                            newExample = self.buildExample(exampleIndex, sentenceGraph, paths, token, combination[0], [combination[1]])
                        else:
                            newExample = self.buildExample(exampleIndex, sentenceGraph, paths, token, [combination[0]], [combination[1]])
                        if len(eventIds) > 0: 
                            newExample[3]["numEv"] = str(len(eventIds))
                        examples.append( newExample )
                        exampleIndex += 1
        
        self.gsEvents = None
        return examples
    
    def isValidEvent(self, paths, sentenceGraph, eventToken, argTokens):
        # This one lets through Positive_regulations that are
        # excluded from the duparg-rule
        oneTokenEvent = True
        for argToken in argTokens:
            if argToken != None and eventToken != argToken:
                oneTokenEvent = False
                break
        if oneTokenEvent:
            return "OK" #True
            
        if not paths.has_key(eventToken):
            return "nopaths" #False
        
        newArgTokens = []
        for argToken in argTokens:
            if type(argToken) == types.ListType or type(argToken) == types.TupleType:
                newArgTokens.extend(argToken)
            else:
                newArgTokens.append(argToken)
        argTokens = newArgTokens
        
        oneArgValid = True
        if False:
            oneArgValid = False    
            for argToken in argTokens:
                if argToken == None:
                    continue
                if paths[eventToken].has_key(argToken):
                    path = paths[eventToken][argToken]
                else:
                    #print argToken, argToken.get("text")
                    #return False
                    continue
                depPaths = self.multiEdgeFeatureBuilder.getEdgeCombinations(sentenceGraph.dependencyGraph, path)
                validArg = False
                for p in depPaths:
                    if p in self.pathGazetteer and self.pathGazetteer[p][0] > 0:
                        validArg = True
                        break
                if validArg:
                    oneArgValid = True
        
        # The first and last dependency of a path
        if False:
            oneEdgeValid = False
            for argToken in argTokens:
                if argToken == None:
                    continue
                if paths[eventToken].has_key(argToken):
                    path = paths[eventToken][argToken]
                else:
                    #print argToken, argToken.get("text")
                    #return False
                    continue
                depPaths = self.multiEdgeFeatureBuilder.getEdgeCombinations(sentenceGraph.dependencyGraph, path)
                validArg = False
                for p in depPaths:
                    p = p.replace("<","")
                    p = p.replace(">","")
                    p = p.split(".")
                    pair = (p[0], p[-1])
                    if pair in self.pathGazetteerPairs:
                        validArg = True
                        break
                if validArg:
                    oneEdgeValid = True
                    break
            if not oneEdgeValid:
                return "pair"

        # Event must not have unseen dependencies in any of its paths
        if False:
            for argToken in argTokens:
                if argToken == None:
                    continue
                if paths[eventToken].has_key(argToken):
                    path = paths[eventToken][argToken]
                else:
                    continue
                deps = self.multiEdgeFeatureBuilder.getEdgeSet(sentenceGraph.dependencyGraph, path)
                for d in deps:
                    if d[2].get("type") not in self.pathGazetteerDependencies:
                        #print "Unk", d[2].get("type")
                        return "unkdep"
                
#            validArg = True
#            for p in depPaths:
#                if p in self.pathGazetteer and self.pathGazetteer[p][0] == 0:
#                    validArg = False
#                    break
            
#            if not validArg:
#                return False
        if not oneArgValid:
            return "novalidarg" #False
        return "OK" #True
    
    def setGazetteerFeatures(self, token, tag):
        gazText = self.getGazetteerMatch(token.get("text").lower())
        if gazText != None:
            gazCategories = self.gazetteer[gazText]
            for k,v in gazCategories.iteritems():
                self.setFeature(tag+"gaz_event_value_"+k, v)
                self.setFeature(tag+"gaz_event_"+k, 1)
                if k.find("egulation") != -1:
                    self.setFeature(tag+"potReg", 1)
        else:
            self.setFeature(tag+"notInGaz", 1)
    
    def buildExample(self, exampleIndex, sentenceGraph, paths, eventToken, themeTokens, causeTokens=None):
        features = {}
        self.features = features
        
        categoryName, eventIds = self.getGSEventType(sentenceGraph, eventToken, themeTokens, causeTokens)
        category = self.classSet.getId(categoryName)
        
        potentialRegulation = False
        eventTokenText = eventToken.get("text").lower()
        gazText = self.getGazetteerMatch(eventTokenText)
        gazCategories = self.gazetteer[gazText]
        for k,v in gazCategories.iteritems():
            if k.find("egulation") != -1:
                potentialRegulation = True
        self.setGazetteerFeatures(eventToken,"")
        
        self.triggerFeatureBuilder.setFeatureVector(self.features)
        self.triggerFeatureBuilder.tag = "trg_"
        self.triggerFeatureBuilder.buildFeatures(eventToken)
        
        themeEntities = []
        hasTheme = False
        if len(themeTokens) > 1:
            self.setFeature("multiTheme", 1)
            potentialRegulation = False
        for themeToken in themeTokens:
            if themeToken != None:
                hasTheme = True
                self.setGazetteerFeatures(themeToken,"theme_")
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, themeToken, "theme_")
                self.triggerFeatureBuilder.tag = "ttrg_"
                self.triggerFeatureBuilder.buildFeatures(themeToken)
                themeEntity = None
                if sentenceGraph.entitiesByToken.has_key(themeToken):
                    for themeEntity in sentenceGraph.entitiesByToken[themeToken]:
                        if themeEntity.get("isName") == "True":
                            self.setFeature("themeProtein", 1)
                            if potentialRegulation:
                                self.setFeature("regulationThemeProtein", 1)
                            themeEntities.append(themeEntity)
                            break
                if not features.has_key("themeProtein"):
                    self.setFeature("themeEvent", 1)
                    self.setFeature("nestingEvent", 1)
                    if potentialRegulation:
                        self.setFeature("regulationThemeEvent", 1)
        if hasTheme:
            self.setFeature("noTheme", 1)
        
        causeEntities = []
        hasCause = False
        for causeToken in causeTokens:
            if causeToken != None:
                hasCause = True
                self.setGazetteerFeatures(causeToken,"cause_")
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, causeToken, "cause_")
                self.triggerFeatureBuilder.tag = "ctrg_"
                self.triggerFeatureBuilder.buildFeatures(causeToken)
                causeEntity = None
                if sentenceGraph.entitiesByToken.has_key(causeToken):
                    for causeEntity in sentenceGraph.entitiesByToken[causeToken]:
                        if causeEntity.get("isName") == "True":
                            self.setFeature("causeProtein", 1)
                            if potentialRegulation:
                                self.setFeature("regulationCauseProtein", 1)
                            causeEntities.append(causeEntity)
                            break
                if not features.has_key("causeProtein"):
                    self.setFeature("causeEvent", 1)
                    self.setFeature("nestingEvent", 1)
                    if potentialRegulation:
                        self.setFeature("regulationCauseEvent", 1)
        if not hasCause:
            self.setFeature("noCause", 1)
        
        self.triggerFeatureBuilder.tag = ""
        self.triggerFeatureBuilder.setFeatureVector(None)
        
        # Common features
#        if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
#            if entity2.get("isName") == "True":
#                features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
#            else:
#                features[self.featureSet.getId("GENIA_regulation_of_event")] = 1

        # define extra attributes
        extra = {"xtype":"event","type":categoryName}
        extra["et"] = eventToken.get("id")
        if len(eventIds) > 0:
            eventIds.sort()
            extra["eids"] = ""
            for eventId in eventIds:
                extra["eids"] += str(eventId) + ","
            extra["eids"] = extra["eids"][:-1]
        for themeToken in themeTokens:
            if themeToken != None:
                if extra.has_key("tt"):
                    extra["tt"] = extra["tt"] + "," + themeToken.get("id")
                else:
                    extra["tt"] = themeToken.get("id")
        for themeEntity in themeEntities:
            if extra.has_key("t"):
                extra["t"] = extra["t"] + "," + themeEntity.get("id")
            else:
                extra["t"] = themeEntity.get("id")
        for causeToken in causeTokens:
            if causeToken != None:
                extra["ct"] = causeTokens[0].get("id")
        if len(causeEntities) > 0:
            extra["c"] = causeEntities[0].get("id")
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId       
        # make example
        #assert (category == 1 or category == -1)
        self.features = None      
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)
    
    def buildArgumentFeatures(self, sentenceGraph, paths, features, eventToken, argToken, tag):
        #eventToken = sentenceGraph.entityHeadTokenByEntity[eventNode]
        #argToken = sentenceGraph.entityHeadTokenByEntity[argNode]
        self.multiEdgeFeatureBuilder.tag = tag
        self.multiEdgeFeatureBuilder.setFeatureVector(features, None, None, False)
        
        if eventToken != argToken and paths.has_key(eventToken) and paths[eventToken].has_key(argToken):
            path = paths[eventToken][argToken]
            edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
        else:
            path = [eventToken, argToken]
            edges = None
        
#        if not "disable_entity_features" in self.styles:
#            # doesn't improve beyond 52.32
#            self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
#        # buildPathLengthFeatures 52.32 -> 51-51
#        self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
#        if not "disable_terminus_features" in self.styles:
#            # didn't improve from 52.32
#            self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
        if not "disable_single_element_features" in self.styles:
            # 50.74 -> 52.32
            self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, edges, sentenceGraph)
        if not "disable_ngram_features" in self.styles:
            # ngrams alone - 50.74
            self.multiEdgeFeatureBuilder.buildPathGrams(2, path, edges, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(3, path, edges, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(4, path, edges, sentenceGraph) # remove for fast
            # disabling length 4 drops performance
#        if not "disable_path_edge_features" in self.styles:
#            self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, edges, sentenceGraph)
#        self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
# buildSentenceFeatures seems to decrease performance by 8 %-points
        self.multiEdgeFeatureBuilder.setFeatureVector(None, None, None, False)
        self.multiEdgeFeatureBuilder.tag = ""
