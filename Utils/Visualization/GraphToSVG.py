import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import draw_dg
from Core.SentenceGraph import SentenceGraph

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

def edgesToSVG(svgTokens, graph):
    svgTokensById = {}
    for token in svgTokens:
        svgTokensById[token.id] = token
    
    #edges = graph.edges(data=True)
    ##edges = []
    ##for nxEdge in nxEdges:
    ##    if nxEdge[0] != nxEdge[1]: # Within-token edges cannot be displayed
    ##        edges.append( (nxEdge[0], nxEdge[1], nxEdge[2]["element"]) )
    
    svgEdges = []    
    for interaction in graph.interactions:
        print graph.tokens, graph.tokensById.keys(), graph.entitiesById.keys(), graph.entityHeadTokenByEntity
        e1 = graph.entitiesById[interaction.get("e1")]
        e2 = graph.entitiesById[interaction.get("e2")]
        t1 = graph.entityHeadTokenByEntity[e1]
        t2 = graph.entityHeadTokenByEntity[e2]
        #token1 = edge[0].get("id")
        #token2 = edge[1].get("id")
        if t1 == t2:
            continue
        reverse = int(t1.get("charOffset").split("-")[0]) > int(t2.get("charOffset").split("-")[0])
        if reverse:
            t1, t2 = t2, t1
        edgeType = interaction.get("type")
        if reverse:
            edgeType = "<" + edgeType
        else:
            edgeType = edgeType + ">"
        svgEdge = draw_dg.Dep(svgTokensById[t1.get("id")], svgTokensById[t2.get("id")], edgeType)
        svgEdges.append(svgEdge)
        
#         if edgeTypeAttrib != None:
#             type = edge[2]["element"].get(edgeTypeAttrib)
#             if int(token1.split("_")[-1]) < int(token2.split("_")[-1]):
#                 type += ">"
#                 svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], type)
#             else:
#                 type = "<" + type
#                 svgEdge = draw_dg.Dep(svgTokensById[token2], svgTokensById[token1], type)
#         else:
#             if edgeTypes.has_key(edge):
#                 svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], edgeTypes[edge])
#             else:
#                 svgEdge = draw_dg.Dep(svgTokensById[token1], svgTokensById[token2], "i")
#         
#         if edge[2]["element"].get("highlight") == "True":
#             svgEdge.arcStyleDict["stroke-width"] = "3"
#             svgEdge.arcStyleDict["stroke"] = "green"
#
#        # Set styles
#         if edge[2].has_key("arcStyles"):
#             for key in sorted(edge[2]["arcStyles"].keys()):
#                 svgEdge.arcStyleDict[key] = edge[2]["arcStyles"][key]
#         if edge[2].has_key("labelStyles"):
#             for key in sorted(edge[2]["labelStyles"].keys()):
#                 svgEdge.labelStyleDict[key] = edge[2]["labelStyles"][key]
#        # Add to list
#        svgEdges.append(svgEdge)
    return svgEdges

def setSVGOptions():
    draw_dg.SVGOptions.fontSize = 12
    draw_dg.SVGOptions.labelFontSize = 10
    draw_dg.SVGOptions.tokenSpace = 5
    draw_dg.SVGOptions.depVertSpace = 10#15
    draw_dg.SVGOptions.minDepPadding = 3

def writeSVG(svgTokens, svgEdges, fileName):
    svgElement = draw_dg.generateSVG(svgTokens, svgEdges)
    ETUtils.write(svgElement, fileName)
    return svgElement

def visualize(inPath, outPath, sentId, parseName):
    setSVGOptions()
    
    xml = ETUtils.ETFromObj(inPath)
    sentences = {x.get("id"):x for x in xml.iter("sentence")}
    if sentId not in sentences:
        print >> sys.stderr, "Sentence id '" + sentId + "' not found"
        return
    sentence = sentences[sentId]
    parse = IXMLUtils.getParseElement(sentence, parseName)
    if not parse:
        print >> sys.stderr, "Sentence has no parse with name '" + parseName + "'"
        return
    
    tokenization = IXMLUtils.getTokenizationElement(sentence, parse.get("tokenizer"))
    graph = SentenceGraph(sentence, [x for x in tokenization.findall("token")], [x for x in parse.findall("dependency")])
    graph.mapInteractions([x for x in sentence.findall("entity")], [x for x in sentence.findall("interaction")])
    svgTokens = tokensToSVG(tokenization.findall("token"))
    svgEdges = edgesToSVG(svgTokens, graph)
    #writeSVG({x.id:x for x in svgTokens}, svgEdges, outPath)
    writeSVG(svgTokens, svgEdges, outPath)

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("-d", "--id", default=None, dest="id", help="sentence id")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="parse name")
    (options, args) = optparser.parse_args()
    
    visualize(options.input, options.output, options.id, options.parse)