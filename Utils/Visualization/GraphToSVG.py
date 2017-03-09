import draw_dg
import cElementTreeUtils as ETUtils

def tokensToSVG(tokenElements, showPOS=False, entitiesByToken=None, extraByToken=None, isNameByToken=None):
    #svgTokensById = {}
    svgTokens = []
    position = 0
    maxOtherLines = 0
    for token in tokenElements:
        if entitiesByToken != None and entitiesByToken.has_key(token):
            if len(entitiesByToken[token]) > maxOtherLines:
                maxOtherLines = len(entitiesByToken[token])
                
    for token in tokenElements:
        svgToken = draw_dg.Token(token.attrib["text"], int(token.attrib["id"].split("_")[-1])-1)
        if isNameByToken != None and isNameByToken[token]:
            svgToken.styleDict["fill"] = "brown"
        if showPOS:
            svgToken.otherLines.append(token.attrib["POS"])
        if entitiesByToken != None and entitiesByToken.has_key(token):
            count = maxOtherLines
            for entity in entitiesByToken[token]:
                if entity.get("highlight") == "True":
                    svgToken.styleDict["fill"] = "green"

                if entity.attrib["isName"] == "True":
                    svgToken.otherLines.append("["+entity.get("type")+"]")
                else:
                    svgToken.otherLines.append(entity.get("type"))
                count -= 1
            for i in range(0,count):
                svgToken.otherLines.append("")
        else:
            for i in range(0,maxOtherLines):
                svgToken.otherLines.append("")
        if extraByToken != None:
            if extraByToken.has_key(token):
                svgToken.otherLines.append(extraByToken[token][0])
                for k,v in extraByToken[token][1].items():
                    svgToken.styleDict[k]=v
            else:
                svgToken.otherLines.append("")
        #svgTokensById[token.attrib["id"]] = svgToken
        svgToken.id = token.attrib["id"]
        svgTokens.append(svgToken)
        position += 1
    #return svgTokensById, svgTokens
    return svgTokens

def edgesToSVG(svgTokens, graph, edgeTypeAttrib="type", edgeTypes={}):
    svgTokensById = {}
    for token in svgTokens:
        svgTokensById[token.id] = token
    
    edges = graph.edges(data=True)
    #edges = []
    #for nxEdge in nxEdges:
    #    if nxEdge[0] != nxEdge[1]: # Within-token edges cannot be displayed
    #        edges.append( (nxEdge[0], nxEdge[1], nxEdge[2]["element"]) )
    
    svgEdges = []    
    for edge in edges:
        token1 = edge[0].get("id")
        token2 = edge[1].get("id")
        if token1 == token2:
            continue
        
        if edgeTypeAttrib != None:
            type = edge[2]["element"].get(edgeTypeAttrib)
            if int(token1.split("_")[-1]) < int(token2.split("_")[-1]):
                type += ">"
                svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], type)
            else:
                type = "<" + type
                svgEdge = draw_dg.Dep(svgTokensById[token2], svgTokensById[token1], type)
        else:
            if edgeTypes.has_key(edge):
                svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], edgeTypes[edge])
            else:
                svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], "i")
        
        if edge[2]["element"].get("highlight") == "True":
            svgEdge.arcStyleDict["stroke-width"] = "3"
            svgEdge.arcStyleDict["stroke"] = "green"

        # Set styles
        if edge[2].has_key("arcStyles"):
            for key in sorted(edge[2]["arcStyles"].keys()):
                svgEdge.arcStyleDict[key] = edge[2]["arcStyles"][key]
        if edge[2].has_key("labelStyles"):
            for key in sorted(edge[2]["labelStyles"].keys()):
                svgEdge.labelStyleDict[key] = edge[2]["labelStyles"][key]
        # Add to list
        svgEdges.append(svgEdge)
    return svgEdges

def makeSVG(svgTokens, svgEdges):
    draw_dg.SVGOptions.fontSize = 12
    draw_dg.SVGOptions.labelFontSize = 10
    draw_dg.SVGOptions.tokenSpace = 5
    draw_dg.SVGOptions.depVertSpace = 10#15
    draw_dg.SVGOptions.minDepPadding = 3
    return draw_dg.generateSVG(svgTokens, svgEdges)

def writeSVG(svgTokens, svgEdges, fileName):
    svgElement = makeSVG(svgTokens, svgEdges)
    ETUtils.write(svgElement, fileName)
    return svgElement