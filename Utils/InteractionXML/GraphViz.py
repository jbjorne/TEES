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
    #f.write("graph [label=\"Orthogonal edges\", splines=ortho, nodesep=0.1];\n")
    f.write("graph [nodesep=0.1];\n")
    f.write("node [shape=box];")
    
    f.write("subgraph tokens {\n")
    f.write("edge[weight=1000, arrowhead=none];\n")
    f.write("rankdir = LR;\n")
    f.write("rank=\"same\";\n")
    f.write("nodesep=0.01;\n")
    tokenIds = []
    for token in elements.tokens:
        tokenIds.append(token.get("id").replace(".", "_"))
        f.write(token.get("id").replace(".", "_") + " [margin=0 label=\"" + token.get("text") + "\\n[" + token.get("POS") + "]\"];\n")
    f.write("->".join(tokenIds) + ";\n")
    f.write("}\n")
    
    f.write("subgraph cluster_1m {\n")
    f.write("color=invis;\n")
    f.write("a12m [style=invisible]\n")
    f.write("}\n")
    
    f.write("subgraph dependencies {\n")
    f.write("node [shape=ellipse margin=0];")
    f.write("edge[weight=1 color=green];\n")
    for dep in elements.dependencies:
        f.write(dep.get("id").replace(".", "_") + " [margin=0 label=\"" + dep.get("type") + "\"];\n")
        f.write(dep.get("t1").replace(".", "_") + " -> " + dep.get("id").replace(".", "_") + ";\n")
        f.write(dep.get("id").replace(".", "_") + " -> " + dep.get("t2").replace(".", "_") + ";\n")
    f.write("}\n")

    f.write("subgraph entities {\n")
    #f.write("rank=\"same\";\n")
    f.write("edge[weight=1];\n")
    for entity in elements.entities:
        if entity.get("event") != "True":
            f.write(entity.get("id").replace(".", "_") + " [label=\"" + entity.get("type") + "\"];\n")
            headToken = graph.entityHeadTokenByEntity[entity]
            if headToken != None:
                f.write(entity.get("id").replace(".", "_") + " -> " + headToken.get("id").replace(".", "_") + ";\n")
        else:
            f.write(entity.get("id").replace(".", "_") + " [label=\"" + entity.get("type") + "\"];\n")
    f.write("}\n")
    
    f.write("subgraph event_to_token {\n")
    f.write("edge[weight=1 color=blue];\n")
    for entity in elements.entities:
        if entity.get("event") == "True":
            headToken = graph.entityHeadTokenByEntity[entity]
            if headToken != None:
                f.write(entity.get("id").replace(".", "_") + " -> " + headToken.get("id").replace(".", "_") + ";\n")
    f.write("}\n")
    
    f.write("subgraph interactions {\n")
    for interaction in elements.interactions:
        f.write(interaction.get("e1").replace(".", "_") + " -> " + interaction.get("e2").replace(".", "_") + " [fontsize=8 label=\"" + interaction.get("type") + "\"];\n")
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