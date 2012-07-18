import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
sys.path.append(extraPath)
from Utils.ProgressCounter import ProgressCounter
import Core.SentenceGraph as SentenceGraph

if __name__=="__main__":
    print >> sys.stderr, "##### Resolve identity chains #####"
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="File from which is read the XML-structure from which elements are copied", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="The file to which the new XML structure is saved. If None, will be the same as target.", metavar="FILE")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization element name")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse element name")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Loading input file", options.input
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    
    counter = ProgressCounter(len(corpusElements.sentences), "Resolving chains")
    tags = ["e1","e2"]
    for sentence in corpusElements.sentences:
        counter.update(1, "Resolving chains for ("+sentence.sentence.attrib["id"]+"): ")
        identityChainDict = {}
        tokenHeadScores = sentence.sentenceGraph.getTokenHeadScores()
        for interaction in sentence.interactions:
            if interaction.attrib["type"] == "identity":
                e1 = sentence.entitiesById[interaction.attrib["e1"]]
                e2 = sentence.entitiesById[interaction.attrib["e2"]]
                t1 = sentence.sentenceGraph.entityHeadTokenByEntity[e1]
                t2 = sentence.sentenceGraph.entityHeadTokenByEntity[e2]
                if tokenHeadScores[t2] > tokenHeadScores[t1]:
                    identityChainDict[interaction.attrib["e1"]] = interaction.attrib["e2"]
                else:
                    identityChainDict[interaction.attrib["e2"]] = interaction.attrib["e1"]
        for interaction in sentence.interactions:
            if interaction.attrib["type"] != "identity":
                for tag in tags:
                    id = interaction.attrib[tag]
                    while identityChainDict.has_key(id):
                        id = identityChainDict[id]
                    if id != interaction.attrib[tag]:
                        interaction.attrib[tag] = id
    
    print >> sys.stderr, "Writing output", options.output
    ETUtils.write(corpusElements.rootElement, options.output)


