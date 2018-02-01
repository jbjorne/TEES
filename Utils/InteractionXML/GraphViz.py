import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
import subprocess
import codecs
import SentenceElements
from Core.SentenceGraph import SentenceGraph

def getId(element, attribute="id"):
    return element.get(attribute).replace(".", "_").replace("-", "_");

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

def toGraphViz(xml, sentenceRange, output=None, parse="McCC", color=None, colorNum=None, colorParse=None, colorNumParse=None, width=None, height=None):
    print >> sys.stderr, "====== Visualizing Sentences with GraphViz (www.graphviz.org) ======"
    
    #if output == None:
    #    output = os.path.join(tempfile.gettempdir(), id + ".gv")
    
    if sentenceRange == None:
        begin, end = 0, sys.maxint
    else:
        begin, end = sentenceRange, None
        if "," in sentenceRange:
            begin, end = sentenceRange.split(",")
            if begin.isdigit():
                assert end.isdigit()
                begin = int(begin)
                end = int(end)
    
    # Get the sentences
    xml = ETUtils.ETFromObj(xml)
    root = xml.getroot()
    sentences = []
    sentenceCount = 0
    breakLoop = False
    documentBySentence = {}
    for document in root.findall("document"):
        for sentence in document.findall("sentence"):
            if len(sentences) == 0 and (sentence.get("id") == begin or sentenceCount == begin):
                sentences.append(sentence)
                documentBySentence[sentence] = document
            if len(sentences) > 0:
                if sentence != sentences[-1]:
                    sentences.append(sentence)
                    documentBySentence[sentence] = document
                if end == None or sentence.get("id") == end or sentenceCount == end:
                    breakLoop = True
                    break
            sentenceCount += 1
        if breakLoop:
            break
    
    print >> sys.stderr, "Sentence Range:", (begin, end), len(sentences)
    if sentences == None:
        print >> sys.stderr, "No sentences for ids", sentenceRange
        return
    
    results = []
    for sentence in sentences:
        elements = SentenceElements.SentenceElements(sentence, parse)
        graph = SentenceGraph(elements.sentence, elements.tokens, elements.dependencies)
        graph.mapInteractions(elements.entities, elements.interactions)
        
        s = ""
        s += "digraph " + sentence.get("id").replace(".", "_").replace("-", "_") + " {\n"
        #f.write("graph [label=\"Orthogonal edges\", splines=ortho, nodesep=0.1];\n")
        if width != None and height != None:
            s += "graph [nodesep=0.1,size=\"" + str(width) + "," + str(height) + "!\", resolution=1];\n"
        else:
            s += "graph [nodesep=0.1];\n"
        s += "node [shape=box];\n\n"
        #f.write("ranksep=0.5;")
        
        s += "subgraph tokens {\n"
        s += "edge [weight=1000, arrowhead=none];\n"
        s += "rankdir = LR;\n"
        s += "rank=\"same\";\n"
        s += "nodesep=0.01;\n"
        #f.write("{ rank=\"same\";\n")
        tokenIds = []
        for token in elements.tokens:
            tokenIds.append(token.get("id").replace(".", "_"))
            s += getId(token) + " [margin=0 label=\"" + token.get("text") + "\\n" + token.get("POS") + "\"];\n"
        s += "->".join(tokenIds) + ";\n"
        s += "}\n\n"
        
        s += "subgraph dependencies {\n"
        s += "edge[weight=0.001 " + getColorScheme(colorParse) + "];\n"
        s += "node[" + getColorScheme(colorParse) + "];\n"
        depStructs = groupDependencies(elements)
        for depStruct in depStructs:
            dep = depStruct["dep"]
            depColor = getColor(dep.get("type"), colorParse, colorNumParse)
            s += getId(dep, "id") + "[" + depColor + " margin=0 label=\"" + dep.get("type") + "\"];\n"
            s += getId(dep, "t1") + " -> " + getId(dep, "id") + "[" + depColor + " weight=10];\n"
            s += getId(dep, "id") + " -> " + getId(dep, "t2") + "[" + depColor + " weight=10];\n"
            if depStruct["child"] != None:
                #f.write(getId(dep) + " -> " + getId(depStruct["child"]["dep"]) + " [color=red];\n")
                s += getId(depStruct["child"]["dep"]) + " -> " + getId(dep) + " [weight=1, color=red style=invis];\n"
            
        s += "}\n\n"
    
        s += "subgraph entities {\n"
        s += "edge[weight=1];\n"
        for entity in elements.entities:
            if entity.get("event") != "True":
                s += getId(entity) + " [label=\"" + entity.get("type") + "\"];\n"
                headToken = graph.entityHeadTokenByEntity[entity]
                if headToken != None:
                    s += getId(entity) + " -> " + getId(headToken) + " [weight=1 style=dashed color=black];\n"
            else:
                s += getId(entity) + " [label=\"" + entity.get("type") + "\"];\n"
        s += "}\n\n"
        
        s += "subgraph event_to_token {\n"
        s += "edge[weight=1 style=dashed color=gray];\n"
        for entity in elements.entities:
            if entity.get("event") == "True":
                headToken = graph.entityHeadTokenByEntity[entity]
                if headToken != None:
                    s += getId(entity) + " -> " + getId(headToken) + ";\n"
        s += "}\n\n"
        
        s += "subgraph interactions {\n"
        s += "edge[" + getColorScheme(color) + "];\n"
        for interaction in elements.interactions:
            intColor = getColor(interaction.get("type"), color, colorNum)
            s += getId(interaction, "e1") + " -> " + getId(interaction, "e2") + "[" + intColor + " fontsize=10 label=\"" + interaction.get("type") + "\"];\n"
        s += "}\n\n"
        s += "}\n"
        
        if output != None:
            currentOutput = output.replace("%i", sentence.get("id")).replace("%o", documentBySentence[sentence].get("origId", ""))
            outDir = os.path.dirname(currentOutput)
            if not os.path.exists(outDir):
                os.makedirs(outDir)
            outStem, ext = os.path.splitext(currentOutput)
            exts = None
            if ext != None:
                ext = ext.strip(".")
                if ext in ("gv", "pdf", "gif"):
                    exts = [ext]
                    currentOutput = outStem
            if exts == None:
                exts = ("gv", "pdf")
            if "gv" in exts:
                gvPath = currentOutput + ".gv"
                print >> sys.stderr, "Graph file saved to: " + gvPath
                with codecs.open(gvPath, "wt", "utf-8") as f:
                    f.write(s)
            for imageExt in ("gif", "pdf"):
                if imageExt in exts:
                    print >> sys.stderr, imageExt.upper(), "file saved to: " + currentOutput + "." + imageExt
                    #subprocess.call("dot -T" + imageExt + " " + gvPath + " > " + currentOutput + "." + imageExt, shell=True)
                    p = subprocess.Popen(["dot -T" + imageExt + " > " + currentOutput + "." + imageExt], stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
                    out, err = p.communicate(input=s.encode(sys.getfilesystemencoding()))
                    for stream in out, err:
                        if stream != None and stream.strip() != "":
                            print stream.strip()
        else:
            p = subprocess.Popen(["dot", "-Tgif"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = p.communicate(input=s.encode(sys.getfilesystemencoding()))
            results.append(out)
    
    if len(results) == 1:
        return results[0]
    else:
        return results

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
    optparser.add_option("--width", default=None, type="int")
    optparser.add_option("--height", default=None, type="int")
    (options, args) = optparser.parse_args()
    
    toGraphViz(options.input, options.id, options.output, options.parse, options.color, options.colorNum, options.colorParse, options.colorNumParse, options.width, options.height)