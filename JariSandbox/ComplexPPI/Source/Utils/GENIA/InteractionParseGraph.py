# A parsegraph for connecting paths that go from named entities to their shared
# roots.

from InteractionXML.ParseGraph import ParseGraph
from InteractionXML.ParseGraph import ParseGraphNode
import draw_dg

class AnalysisPath:
    def __init__(self, namedEntityId):
        self.namedEntityId = namedEntityId
        self.shortId = namedEntityId.rsplit(".",1)[-1]
        self.nodes = []
    
    def isBlocked(self):
        for node in self.nodes:
            if node.type == "BLOCKED":
                return True
        return False
    
    def hasNode(self, parseGraphNode):
        for node in self.nodes:
            if node.parseGraphNode == parseGraphNode:
                return True
        return False
    
    def hasEntity(self, entity):
        for node in self.nodes:
            if entity in node.parseGraphNode.entities:
                return True
        return False
    
    def addNode(self, parseGraphNode):
        self.nodes.append(AnalysisPathNode(parseGraphNode))
    
    def clone(self):
        newPath = AnalysisPath(self.namedEntityId)
        for node in self.nodes:
            newPath.nodes.append(node.clone())
        return newPath
    
#    def defineDependency(self):
#        for i in range(len(self.nodes)-1,-1,-1):
#            dependencies 

    def setNodeType(self, node, prevNode, prevNode2):
        if node.parseGraphNode.pos[0] == "N":
            if prevNode.parseGraphNode.dependencyType == "nn":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    if node.parseGraphNode.text[-2:] == "on":
                        node.type = "PROCESS"
                    else:
                        node.type = "ENTITY"
            elif prevNode.parseGraphNode.dependencyType == "prep_of":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    if node.parseGraphNode.text[-2:] == "on":
                        node.type = "PROCESS_OF"
                    else:
                        node.type = "FEATURE"
            elif prevNode.parseGraphNode.dependencyType == "prep_with":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    if node.parseGraphNode.text[-2:] == "on":
                        node.type = "PROCESS_WITH"
                    else:
                        node.type = "FEATURE"
            elif prevNode.parseGraphNode.dependencyType == "prep_on":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    node.type = "PROCESS_ON"
        elif node.parseGraphNode.pos[0] == "V":
            if prevNode.parseGraphNode.dependencyType == "nsubj":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    node.type = "VERB"
                    node.argumentType = "SUBJECT"
            elif prevNode.parseGraphNode.dependencyType == "dobj":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    node.type = "VERB"
                    node.argumentType = "OBJECT"
            elif prevNode.parseGraphNode.dependencyType == "prep_via":
                if prevNode2.parseGraphNode.pos[0] == "N":
                    prevNode.type = "PASS"
                    node.type = "VERB"
                    node.argumentType = "VIA"
    
    def analyze(self):
        #if len(self.nodes) == 1 and len(self.nodes[0].parseGraphNode.entities) > 0:
        self.nodes[0].type = "NAMED_ENT"
        self.nodes[-1].type = "ROOT"
        
        prevNode = None
        prevNode2 = None
        for node in self.nodes:
            if prevNode2 != None and prevNode.parseGraphNode.isDependency:
                self.setNodeType(node, prevNode, prevNode2)
            prevNode2 = prevNode
            prevNode = node
        
    def getStructureString(self, useActualText=False, cutoff = 0):
        string = ""
        closingParentheses = 0
        isFirstNode = True
        for i in range(len(self.nodes)-cutoff):
            node = self.nodes[i]
            text = node.getStructureText(useActualText)
            if node.type == "BLOCKED":
                break
            elif node.type == "PASS":
                continue
            else:
                if isFirstNode:
                    string = text
                    closingParentheses -= 1
                elif node.argumentType == "SINGLE":
                    string = text + "(" + string
                elif node.argumentType == "SUBJECT":
                    if node.linkedPath != None:
                        arg = node.linkedPath.getStructureString(useActualText,1)
                    else:
                        arg = "X"
                    string = text + "(" + string + closingParentheses * ")" + ", " + arg
                    closingParentheses = 0
                elif node.argumentType == "OBJECT":
                    if node.linkedPath != None:
                        arg = node.linkedPath.getStructureString(useActualText,1)
                    else:
                        arg = "X"
                    string = text + "("+arg+", " + string + closingParentheses * ")"
                    closingParentheses = 0
                closingParentheses += 1
            isFirstNode = False
        string += ")" * closingParentheses
        return string
    
    def toString(self):
        string = ""
        string += "<FONT COLOR='FFFFFF'>__</FONT>" + self.shortId + ":"
        for i in range(len(self.nodes)):
            if self.nodes[i].type != "BLOCKED":
                string += "<FONT COLOR='00FF00'>"
            else:
                string += "<FONT COLOR='FF0000'>"
            string += self.nodes[i].parseGraphNode.toString()
            string += "</FONT>"
        string += ":" + self.getStructureString()
        return string

class AnalysisPathNode:
    def __init__(self, parseGraphNode):
        self.parseGraphNode = parseGraphNode
        self.parseGraphNode.isInInteractionGraph = False
        self.parseGraphNode.entityType = " "
        self.type = "BLOCKED"
        self.argumentType = "SINGLE"
        self.linkedPath = None
    
    def clone(self):
        newNode = AnalysisPathNode(self.parseGraphNode)
        newNode.type = self.type
        return newNode
    
    def getStructureText(self, useActualText):
        if useActualText:
            if self.type == "VERB":
                return self.parseGraphNode.stem
            else:
                return self.parseGraphNode.text
        else:
            return self.type

class InteractionGraphDependency:
    def __init__(self, parseGraphNode, tokenFrom=None, tokenTo=None):
        self.fro = tokenFrom
        self.to = tokenTo
        self.parseGraphNode = parseGraphNode

class InteractionParseGraph(ParseGraph):
    def __init__(self, sentence):
        self.sentence = sentence
        ParseGraph.__init__(self, sentence.tokens, sentence.dependencies)
        
        #self.interactionGraphTokens = []
        self.interactionGraphDependencies = []
        
        self.sentence.annotationDependencies = []
        self.sentence.annotationDependenciesWithParseDependency = 0
        #for token in self.tokensById.values():
        #    self.interactionGraphTokens.append(InteractionGraphNode(token))
    
    def addAnnotationDependency(self, token1, token2, type, directionality="UNIDIRECTIONAL"):
#        print "TBefore:", token1, token2
        token1 += 1 
        token2 += 1
#        print "TBefore+1:", token1, token2        
        # POSITION 1 BEGIN
        # POSITION 1 END        
#        print "TAfter1:", token1, token2
       
        annotationDependency =  ParseGraphNode(True)
        annotationDependency.fro = self.tokensById[token1]
        annotationDependency.to = self.tokensById[token2]
        annotationDependency.dependencyType = type
        annotationDependency.directionality = directionality
        
        # Check for duplicates
        for annDep in self.sentence.annotationDependencies:
            if annDep.fro == annotationDependency.fro and \
            annDep.to == annotationDependency.to and \
            annDep.dependencyType == annotationDependency.dependencyType and \
            annDep.directionality == annotationDependency.directionality:
                return None
        
        #self.sentence.annotationDependencies.append( (token1, token2, type) )
#        print "TAfter2:", token1, token2
        #self.sentence.annotationDependencies.append( (True,True,True) )
        self.sentence.annotationDependencies.append( annotationDependency )
        # POSITION 2 BEGIN
        rv = False
        for dependency in self.dependenciesById.values():
            if (dependency.fro == self.tokensById[token1] and dependency.to == self.tokensById[token2]) or (dependency.fro == self.tokensById[token2] and dependency.to == self.tokensById[token1]):
                self.sentence.annotationDependenciesWithParseDependency += 1
                rv = True
        # POSITION 2 END
        return rv
    
    def countAnnotationDependencyTypes(self, typeDict):
        for annDep in self.sentence.annotationDependencies:
            annDep.hasCorrespondingParseDependency = False
            for dep in self.dependenciesById.values():
                if (dep.fro == annDep.fro and dep.to == annDep.to) or (dep.fro == annDep.to and dep.to == annDep.fro):
                    if not typeDict.has_key(dep.dependencyType):
                        typeDict[dep.dependencyType] = {}
                    if not typeDict[dep.dependencyType].has_key(annDep.dependencyType):
                        typeDict[dep.dependencyType][annDep.dependencyType] = 0
                    typeDict[dep.dependencyType][annDep.dependencyType] += 1
                    annDep.hasCorrespondingParseDependency = True
    
    def analyzeComplexAnnotationDependencies(self, lengthDict, stringDict):
        for annDep in self.sentence.annotationDependencies:
            annDep.parsePath = None
            #if not annDep.hasCorrespondingParseDependency:
            parsePath = self.buildShortestPathNX(annDep.fro.id, annDep.to.id)
            annDep.parsePath = parsePath
            length = 0
            string = ""
            for node in parsePath:
                if node.isDependency: 
                    length += 1
                    string += node.toString()
            # add the count
            if not lengthDict.has_key(annDep.dependencyType):
                lengthDict[annDep.dependencyType] = {}
            if not lengthDict[annDep.dependencyType].has_key(length):
                lengthDict[annDep.dependencyType][length] = 0
            lengthDict[annDep.dependencyType][length] += 1
            # add the path
            if not stringDict.has_key(string):
                stringDict[string] = {}
            if not stringDict[string].has_key(annDep.dependencyType):
                stringDict[string][annDep.dependencyType] = 0
            stringDict[string][annDep.dependencyType] += 1
                                                                       
    def buildPathsToRoots(self):
        for token in self.tokensById.values():
            token.rootPaths = []
        for token in self.tokensById.values():
            if len(token.entities) > 0:
                #print len(token.entities)
                for entity in token.entities:
                    self.__buildPathsToRoots(token, entity)
        for token in self.tokensById.values():
            self.analyzePaths(token)
            
    def __buildPathsToRoots(self, node, entity, path=None):
        #if not hasattr(node, "rootPaths"):
        #    node.rootPaths = []
            #node.rootPathWalks = []
        
        if path == None:
            path = AnalysisPath(entity)
        if len(path.nodes) > 0 and entity in node.entities:
            return
        path.addNode(node)
        node.rootPaths.append( path.clone() )

        for dependency in node.dependencies:
            if dependency.to == node:
                if (not path.hasNode(dependency)) and not (path.hasNode(dependency.fro)):
                    newPath = path.clone()
                    newPath.addNode(dependency)
                    dependency.isRootPath = True
                    self.__buildPathsToRoots(dependency.fro, entity, newPath)
    
    def analyzePaths(self, node):
#        if hasattr(node, "rootPaths"):
        for path in node.rootPaths:
            path.analyze()
    
    def addInteraction(self, path1, path2):
        isInteraction = False
        for pair in self.sentence.pairs:
            if pair.attrib["interaction"] == "True":
                if (pair.attrib["e1"] == path1.namedEntityId and \
                    pair.attrib["e2"] == path2.namedEntityId) or \
                   (pair.attrib["e2"] == path1.namedEntityId and
                    pair.attrib["e1"] == path2.namedEntityId ):
                    isInteraction = True
                    break
                
        if not hasattr(self.sentence, "extractedInteractions"):
            self.sentence.extractedInteractions = set()
        #if int(path1.namedEntityId.rsplit(".",1)[-1][1:]) > int(path2.namedEntityId.rsplit(".",1)[-1][1:]):
        #    path1, path2 = path2, path1
        self.sentence.extractedInteractions.add( (path1.namedEntityId, path2.namedEntityId, isInteraction) ) 
        return isInteraction
    
    def testInterPathInteraction(self, path1, path2):
        type = path1.nodes[-1].type
        if len(path1.nodes) == 1 or len(path2.nodes) == 1:
            return False
        if type == "VERB":
            if path1.nodes[-2].parseGraphNode.dependencyType == "nsubj":
                if path2.nodes[-2].parseGraphNode.dependencyType == "dobj":
                    return True
            if path1.nodes[-2].parseGraphNode.dependencyType == "dobj":
                if path2.nodes[-2].parseGraphNode.dependencyType == "nsubj":
                    return True
    
    def findInterPathInteractions(self):
        statements = []
        interactions = []
        tokens = self.tokensById.values()
        for token in tokens:
#            if hasattr(token, "rootPaths"):
            paths = token.rootPaths
            for i in range(len(paths)-1):
                if not paths[i].isBlocked():
                    for j in range(i+1,len(paths)):
                        #testInterPathInteraction(paths[i], paths[j])
                        if not paths[j].isBlocked():
                            #if paths[i].nodes[-1].type == "VERB":
                            if self.testInterPathInteraction(paths[i], paths[j]):
                                isTrue = self.addInteraction(paths[i], paths[j])
                                paths[i].nodes[-1].linkedPath = paths[j]
                                statements.append(paths[i].getStructureString(True) + " " + str(isTrue))
                                paths[i].nodes[-1].linkedPath = None
                                interactions.append( (paths[i], paths[j]) )
                                    
        return statements, interactions
    
    def buildInteractionGraph(self):
        for token in self.tokensById.values():
            rootDependencies = []
            for path in token.rootPaths:
                if len(path.nodes) < 2:
                    continue
                if not path.isBlocked():
                    assert(path.nodes[-2].parseGraphNode.dependencyType != None)
                    rootDependencies.append(path.nodes[-2].parseGraphNode.dependencyType)
            for path in token.rootPaths:
                if len(path.nodes) < 2:
                    continue
                if not path.isBlocked():
                    if path.nodes[-2].parseGraphNode.dependencyType == "nsubj" and "dobj" in rootDependencies:
                        self.addPathToInteractionGraph(path)
                    elif path.nodes[-2].parseGraphNode.dependencyType == "dobj" and "nsubj" in rootDependencies:
                        self.addPathToInteractionGraph(path)
                    elif path.nodes[-2].parseGraphNode.dependencyType == "prep_via" and "nsubj" in rootDependencies and "dobj" in rootDependencies:
                        self.addPathToInteractionGraph(path)
    
    def addPathToInteractionGraph(self, path):
        prevNode2 = prevNode = None
        for node in path.nodes:
            if prevNode != None and prevNode.parseGraphNode.isDependency and prevNode2 != None:
                if not prevNode.parseGraphNode.isInInteractionGraph:
                    dep = InteractionGraphDependency(prevNode.parseGraphNode, node.parseGraphNode, prevNode2.parseGraphNode)
                    dep.type = node.argumentType
                    self.interactionGraphDependencies.append(dep)
                    #if not hasattr(node.parseGraphNode, "interactionFro")
                    prevNode.parseGraphNode.isInInteractionGraph = True
            if (not node.parseGraphNode.isDependency) and node.type != None:
                node.parseGraphNode.entityType = node.type
            prevNode2 = prevNode
            prevNode = node
    
    def writeDep(self, f):
        tokenKeys = self.tokensById.keys()
        tokenKeys.sort()
        f.write("tokens:")
        for key in tokenKeys:
            f.write(" " + self.tokensById[key].text)
        f.write("\n")
        f.write("tokens:")
        for key in tokenKeys:
            f.write(" " + self.tokensById[key].pos)
        f.write("\n")
                
        for dependency in self.sentence.annotationDependencies:
            token1 = dependency.fro
            token2 = dependency.to
            type = dependency.dependencyType
            if token1.id < token2.id:
                type += ">"
                f.write(token1.text + " " + type + " " + token2.text)
            else:
                type = "<" + type
                f.write(token2.text + " " + type + " " + token1.text)
            f.write(" #ARC stroke:black;stroke-width:2;fill:none #LAB font-weight:bold;fill:black" + "\n")
            
        for dependency in self.dependenciesById.values():
            token1 = dependency.fro
            token2 = dependency.to
            type = dependency.dependencyType
            if token1.id < token2.id:
                type += ">"
                f.write(token1.text + " " + type + " " + token2.text)
            else:
                type = "<" + type
                f.write(token2.text + " " + type + " " + token1.text)
            f.write(" #ARC stroke:gray;stroke-width:1;fill:none #LAB fill:gray" + "\n")

    def dependencyGraphToSVG(self, showPOS=True):
        svgTokens = []
        svgTokensById = {}
        for token in self.tokensById.values():
            svgToken = draw_dg.Token(token.text, token.id-1)
            if showPOS:
                svgToken.otherLines.append(token.pos)
            if hasattr(token, "entityType"):
                svgToken.otherLines.append(token.entityType)
            else:
                svgToken.otherLines.append(" ")
            svgTokens.append(svgToken)
            svgTokensById[token.id] = svgToken
    
        svgDependencies = []    
        for dependency in self.dependenciesById.values():
            token1 = dependency.fro.id
            token2 = dependency.to.id
            type = dependency.dependencyType
            if token1 < token2:
                type += ">"
                svgDependency = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], type)
            else:
                type = "<" + type
                svgDependency = draw_dg.Dep(svgTokensById[token2], svgTokensById[token1], type)
            svgDependencies.append(svgDependency)
        
        return svgTokens, svgDependencies

    def annotationGraphToSVG(self, showPOS=True):
        svgTokens = []
        svgTokensById = {}
        for token in self.tokensById.values():
            svgToken = draw_dg.Token(token.text, token.id-1)
            if showPOS:
                svgToken.otherLines.append(token.pos)
            if hasattr(token, "entityType"):
                svgToken.otherLines.append(token.entityType)
            else:
                svgToken.otherLines.append(" ")
            svgTokens.append(svgToken)
            svgTokensById[token.id] = svgToken
    
        svgDependencies = []    
        for dependency in self.sentence.annotationDependencies:
            token1 = dependency.fro.id
            token2 = dependency.to.id
            type = dependency.dependencyType
            if token1 < token2:
                type += ">"
                svgDependency = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], type)
            else:
                type = "<" + type
                svgDependency = draw_dg.Dep(svgTokensById[token2], svgTokensById[token1], type)
            if dependency.hasCorrespondingParseDependency:
                # Hot Pink: #F660AB
                #        svgDependency.arcStyleDict["stroke"] = "yellow"
                #        svgDependency.labelStyleDict["fill"] = "yellow"
                svgDependency.arcStyleDict["stroke"] = "orange"
                svgDependency.labelStyleDict["fill"] = "orange"
            else:
                svgDependency.arcStyleDict["stroke"] = "#F660AB"
                svgDependency.labelStyleDict["fill"] = "#F660AB"
            svgDependencies.append(svgDependency)
        
        return svgTokens, svgDependencies
    
    def interactionGraphToSVG(self, showPOS=True):
        svgTokens = []
        svgTokensById = {}
        for token in self.tokensById.values():
            svgToken = draw_dg.Token(token.text, token.id-1)
            if showPOS:
                svgToken.otherLines.append(token.pos)
            #if hasattr(token, "entityType"):
            #    svgToken.otherLines.append(token.entityType)
            #else:
            #    svgToken.otherLines.append(" ")
            svgTokens.append(svgToken)
            svgTokensById[token.id] = svgToken
    
        svgDependencies = []    
#        for dependency in self.interactionGraphDependencies:
#            token1 = dependency.fro.id
#            token2 = dependency.to.id
#            type = dependency.type
#            if token1 < token2:
#                type += ">"
#                svgDependency = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], type)
#            else:
#                type = "<" + type
#                svgDependency = draw_dg.Dep(svgTokensById[token2], svgTokensById[token1], type)
#            svgDependencies.append(svgDependency)
        
        return svgTokens, svgDependencies
#        
#        draw_dg.SVGOptions.fontSize = 12
#        draw_dg.SVGOptions.labelFontSize = 10
#        draw_dg.SVGOptions.tokenSpace = 5
#        draw_dg.SVGOptions.depVertSpace = 15
#        draw_dg.SVGOptions.minDepPadding = 3    
#        return draw_dg.generateSVG(svgTokens,svgDependencies)

    ###########################################################################
    # SVM Stuff
    ###########################################################################
    
    def buildSVMSamples(self):
        samples = []
        for dep in self.dependenciesById.values():
            if hasattr(dep,"isRootPath"):
                sample = [{},False,self.sentence.sentence.attrib["id"]+".d"+str(dep.id)]
                sample[0]["dependencyType_"+dep.dependencyType] = 1
                sample[0]["froTokenPOS_"+dep.fro.pos] = 1
                sample[0]["froTokenText_"+dep.fro.text] = 1
                sample[0]["toTokenPOS_"+dep.to.pos] = 1
                sample[0]["toTokenText_"+dep.to.text] = 1
                for annDep in self.sentence.annotationDependencies:
                    if (dep.fro == annDep.fro and dep.to == annDep.to) or (dep.fro == annDep.to and dep.to == annDep.fro):
                        sample[1] = True
                samples.append(sample)
        return samples
            