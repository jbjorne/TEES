import Core.ExampleUtils as Example
import sys, os, shutil
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
from InteractionXML.CorpusElements import CorpusElements
from Core.SentenceGraph import *
from Visualization.CorpusVisualizer import CorpusVisualizer
from optparse import OptionParser

if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible_noCL.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory, useful for debugging")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="parse")
    (options, args) = optparser.parse_args()
    
    corpusElements = loadCorpus(options.input, options.parse, options.tokenization)
    sentences = []
    for sentence in corpusElements.sentences:
        sentences.append( [sentence.sentenceGraph,None] )
    
    print >> sys.stderr, "Visualizing"
    visualizer = CorpusVisualizer(options.output, True)
    for i in range(len(sentences)):
        sentence = sentences[i]
        print >> sys.stderr, "\rProcessing sentence", sentence[0].getSentenceId(), "          ",
        prevAndNextId = [None,None]
        if i > 0:
            prevAndNextId[0] = sentences[i-1][0].getSentenceId()
        if i < len(sentences)-1:
            prevAndNextId[1] = sentences[i+1][0].getSentenceId()
        visualizer.makeSentencePage(sentence[0],sentence[1],None,prevAndNextId)
    visualizer.makeSentenceListPage()
    print >> sys.stderr