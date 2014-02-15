import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
import subprocess
import SentenceElements
from Core.SentenceGraph import SentenceGraph
import tempfile

def getId(element, attribute="id"):
    return element.get(attribute).replace(".", "_");

def getColorScheme(scheme):
    if scheme != None:
        return "colorscheme="+scheme
    else:
        return None

def getColor(string, scheme, numColors):
    if scheme == None:
        return ""
    return "color=" + str(numColors - hash(string) % numColors)

def getHeadScore(token):
    headScore = 0
    if token.get("headScore") != None:
        headScore = int(token.get("headScore"))
    return headScore

def orderTokens(token1, token2):
    offset1 = Range.charOffsetToSingleTuple(token1.get("charOffset"))
    offset2 = Range.charOffsetToSingleTuple(token1.get("charOffset"))
    return Range.order(offset1, offset2)

def groupDependencies(elements):
    tokens = sorted(elements.tokens, cmp=orderTokens)
    indexByTokenId = {}
    for i in range(len(tokens)):
        indexByTokenId[tokens[i].get("id")] = i
    
    depStructs = []
    for dependency in elements.dependencies:
        depD = {"range":(indexByTokenId[dependency.get("t1")], indexByTokenId[dependency.get("t2")])}
        if depD["range"][0] > depD["range"][1]:
            depD["range"] = (depD["range"][1], depD["range"][0])
        depD["dep"] = dependency
        depD["child"] = None
        depD["childScore"] = 9999
        depStructs.append(depD)
    for d1 in depStructs:
        for d2 in depStructs:
            if d1 == d2:
                continue
            if d1["range"] != d2["range"] and Range.contains(d1["range"], d2["range"]):
                score = abs((d2["range"][0] - d1["range"][0]) - (d1["range"][1] - d2["range"][1]))
                if score < d1["childScore"]:
                    d1["child"] = d2
    return depStructs         

def toGraphViz(input, id, output=None, parse="McCC", color=None, colorNum=None, colorParse=None, colorNumParse=None):
    print >> sys.stderr, "====== Visualizing Sentence with GraphViz (www.graphviz.org) ======"
    
    if output == None:
        output = os.path.join(tempfile.gettempdir(), id + ".gv")
    
    # Get the sentence
    xml = ETUtils.ETFromObj(input).getroot()
    sentence = None
    for document in xml.findall("document"):
        for s in document.findall("sentence"):
            if s.get("id") == id:
                sentence = s
                break
    if sentence == None:
        print >> sys.stderr, "No sentence for id", id
        return
    
    elements = SentenceElements.SentenceElements(sentence, parse)
    graph = SentenceGraph(elements.sentence, elements.tokens, elements.dependencies)
    graph.mapInteractions(elements.entities, elements.interactions)
    
    print >> sys.stderr, "Graph file saved to: " + output
    f = open(output, "wt")
    f.write("digraph " + id.replace(".", "_") + " {\n")
    #f.write("graph [label=\"Orthogonal edges\", splines=ortho, nodesep=0.1];\n")
    f.write("graph [nodesep=0.1];\n")
    f.write("node [shape=box];\n\n")
    #f.write("ranksep=0.5;")
    
    f.write("subgraph tokens {\n")
    f.write("edge [weight=1000, arrowhead=none];\n")
    f.write("rankdir = LR;\n")
    f.write("rank=\"same\";\n")
    f.write("nodesep=0.01;\n")
    #f.write("{ rank=\"same\";\n")
    tokenIds = []
    for token in elements.tokens:
        tokenIds.append(token.get("id").replace(".", "_"))
        f.write(getId(token) + " [margin=0 label=\"" + token.get("text") + "\\n" + token.get("POS") + "\"];\n")
    f.write("->".join(tokenIds) + ";\n")
    f.write("}\n\n")
    
    f.write("subgraph dependencies {\n")
    f.write("edge[weight=0.001 " + getColorScheme(colorParse) + "];\n")
    f.write("node[" + getColorScheme(colorParse) + "];\n")
    depStructs = groupDependencies(elements)
    for depStruct in depStructs:
        dep = depStruct["dep"]
        depColor = getColor(dep.get("type"), colorParse, colorNumParse)
        f.write(getId(dep, "id") + "[" + depColor + " margin=0 label=\"" + dep.get("type") + "\"];\n")
        f.write(getId(dep, "t1") + " -> " + getId(dep, "id") + "[" + depColor + " weight=10];\n")
        f.write(getId(dep, "id") + " -> " + getId(dep, "t2") + "[" + depColor + " weight=10];\n")
        if depStruct["child"] != None:
            #f.write(getId(dep) + " -> " + getId(depStruct["child"]["dep"]) + " [color=red];\n")
            f.write(getId(depStruct["child"]["dep"]) + " -> " + getId(dep) + " [weight=1, color=red style=invis];\n")
        
    f.write("}\n\n")

    f.write("subgraph entities {\n")
    f.write("edge[weight=1];\n")
    for entity in elements.entities:
        if entity.get("event") != "True":
            f.write(getId(entity) + " [label=\"" + entity.get("type") + "\"];\n")
            headToken = graph.entityHeadTokenByEntity[entity]
            if headToken != None:
                f.write(getId(entity) + " -> " + getId(headToken) + " [weight=1 style=dashed color=black];\n")
        else:
            f.write(getId(entity) + " [label=\"" + entity.get("type") + "\"];\n")
    f.write("}\n\n")
    
    f.write("subgraph event_to_token {\n")
    f.write("edge[weight=1 style=dashed color=gray];\n")
    for entity in elements.entities:
        if entity.get("event") == "True":
            headToken = graph.entityHeadTokenByEntity[entity]
            if headToken != None:
                f.write(getId(entity) + " -> " + getId(headToken) + ";\n")
    f.write("}\n\n")
    
    f.write("subgraph interactions {\n")
    f.write("edge[" + getColorScheme(color) + "];\n")
    for interaction in elements.interactions:
        intColor = getColor(interaction.get("type"), color, colorNum)
        f.write(getId(interaction, "e1") + " -> " + getId(interaction, "e2") + "[" + intColor + " fontsize=10 label=\"" + interaction.get("type") + "\"];\n")
    f.write("}\n\n")
    
    f.write("}\n")
    f.close()
    
    print >> sys.stderr, "PDF file saved to: " + output + ".pdf"
    subprocess.call("dot -Tpdf " + output + " > " + output + ".pdf", shell=True)
    

if __name__=="__main__":
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input interaction XML file")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output interaction XML file")
    optparser.add_option("-d", "--id", default=None, dest="id", help="sentence id")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="parse name")
    optparser.add_option("-c", "--color", default="set27", dest="color", help="Event color scheme")
    optparser.add_option("-e", "--colorParse", default="set27", dest="colorParse", help="Parse color scheme")
    optparser.add_option("-n", "--colorNum", default=7, type="int", dest="colorNum", help="Event color scheme")
    optparser.add_option("-m", "--colorNumParse", default=7, type="int", dest="colorNumParse", help="Event color scheme")
    (options, args) = optparser.parse_args()
    
    toGraphViz(options.input, options.id, options.output, options.parse, options.color, options.colorNum, options.colorParse, options.colorNumParse)