import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
import Utils.ElementTreeUtils as ETUtils
import subprocess
import SentenceElements
from Core.SentenceGraph import SentenceGraph

def toGraphViz(input, output, id, parse="McCC"):
    print >> sys.stderr, "====== Making Graphs ======"
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
    
    f = open(output, "wt")
    f.write("digraph " + id.replace(".", "_") + " {\n")
    f.write("node [shape=box];")
    
    #f.write("subgraph tokens {\n rank=\"same\";\n")
    f.write("subgraph tokens {\n")
    f.write("edge[weight=20, arrowhead=none];\n")
    f.write("rankdir = LR;\n");
    f.write("rank=\"same\";\n");
    tokenIds = []
    for token in elements.tokens:
        tokenIds.append(token.get("id").replace(".", "_"))
        f.write(token.get("id").replace(".", "_") + " [label=\"" + token.get("text") + " [" + token.get("POS") + "]\"];\n")
    f.write("->".join(tokenIds) + ";\n")
    f.write("}\n")
    
    f.write("subgraph entities {\n")
    for entity in elements.entities:
        f.write(entity.get("id").replace(".", "_") + " [label=\"" + entity.get("type") + "\"];\n")
    f.write("}\n")
    
    for entity in elements.entities:
        headToken = graph.entityHeadTokenByEntity[entity]
        if headToken != None:
            f.write(entity.get("id").replace(".", "_") + " -> " + headToken.get("id").replace(".", "_") + ";\n")
    
    f.write("subgraph interactions {\n")
    for interaction in elements.interactions:
        f.write(interaction.get("e1").replace(".", "_") + " -> " + interaction.get("e2").replace(".", "_") + " [label=\"" + interaction.get("type") + "\"];\n")
    f.write("}\n")
    
    f.write("}\n")
    f.close()
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
    (options, args) = optparser.parse_args()
    
    toGraphViz(options.input, options.output, options.id)