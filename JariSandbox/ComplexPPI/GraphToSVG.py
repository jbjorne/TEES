import draw_dg
import cElementTreeUtils as ETUtils

def tokensToSVG(tokenElements, showPOS=False):
    svgTokensById = {}
    svgTokens = []
    position = 0
    for token in tokenElements:
        svgToken = draw_dg.Token(token.attrib["text"], int(token.attrib["id"].split("_")[-1])-1)
        if showPOS:
            svgToken.otherLines.append(token.pos)
        if hasattr(token, "entityType"):
            svgToken.otherLines.append(token.entityType)
        else:
            svgToken.otherLines.append(" ")
        svgTokensById[token.attrib["id"]] = svgToken
        svgTokens.append(svgToken)
        position += 1
    return svgTokensById, svgTokens

def edgesToSVG(svgTokensById, graph, edgeTypeAttrib="type"):
    edges = graph.edges()
    svgEdges = []    
    for edge in edges:
        token1 = edge[0].attrib["id"]
        token2 = edge[1].attrib["id"]
        type = edge[2].attrib[edgeTypeAttrib]
        if int(token1.split("_")[-1]) < int(token2.split("_")[-1]):
            type += ">"
            svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], type)
        else:
            type = "<" + type
            svgEdge = draw_dg.Dep(svgTokensById[token2], svgTokensById[token1], type)
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
    ETUtils.write(makeSVG(svgTokens, svgEdges), fileName)