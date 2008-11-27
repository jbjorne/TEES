try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import sys
from optparse import OptionParser
import os, shutil
from InteractionXML.CorpusElements import CorpusElements
from InteractionXML.SentenceElements import SentenceElements
from InteractionXML.IDUtils import sortInteractionIds
from InteractionParseGraph import InteractionParseGraph
import Range
from BIGraph.core.sentence import RelEdge

import GeniaParseGraph
import os

sys.path.append("../..")
import Core.Split as Split

def getNestedChildren(text, children):
    for child in children:
        #assert(child.tag == "term")
        if child.text != None:
            text += child.text
        text = getNestedChildren(text,child.getchildren())
        if child.tail != None:
            text += child.tail
    return text 

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    defaultGeniaBioInferFilename = "/usr/share/biotext/genia/treebank/Stanford-GTB/GTB_BI-xml-collapsed-realigned.xml"
    #defaultGeniaBioInferFilename = "/usr/share/biotext/ABC_data/sentences.edited.tree.tag_fixed.SF2007_collapsed.xml"
    #defaultGeniaBioInferFilename = "/usr/share/biotext/ABC_data/sentences.edited.tree.tag_fixed.xml"
    defaultEventFolder = "/usr/share/biotext/genia/GENIA_event_annotation_0.9/GENIAcorpus_event"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultGeniaBioInferFilename, dest="input", help="", metavar="FILE")
    optparser.add_option("-e", "--events", default=defaultEventFolder, dest="events", help="", metavar="FILE")
#    optparser.add_option("-l", "--limit", type="int", default=None, dest="limit", help="Max number of paths to load.")
    optparser.add_option("-v", "--visibleSet", type="float", default=1.0, dest="visibleSet", help="Visible set fraction")
    optparser.add_option("-o", "--output", default="/usr/share/biotext/ComplexPPI/GENIAForComplexPPI.xml", dest="output", help="Output directory.")
    optparser.add_option("-r", "--reverse", dest="reverseDependencies", default=False, help="Reverse direction of BioInfer-style dependencies", action="store_true")
    (options, args) = optparser.parse_args()

    if options.input == None:
        print >> sys.stderr, "Error, input (analysis) file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output path not defined."
        optparser.print_help()
        sys.exit(1)
    
    parseGraphsByText = GeniaParseGraph.loadSentences(options.input, options.reverseDependencies)
    parseGraphsById = {}
    
    eventFileNames = os.listdir(options.events)
    if os.path.exists(options.events + "/event_files_with_parse.txt"):
        eventFileNames.remove("event_files_with_parse.txt")
    numSentences = 0
    numSentencesWithParse = 0
    eventFilesWithParse = set()
    articleCount = 0
    docCount = 0
#    corpusElement = ET.Element("corpus")
#    corpusElement.attrib["source"] = "GENIA"
    documentElements = []
    for eventFileName in eventFileNames:
        #print >> sys.stderr, "Processing", eventFileName
        eventTree = ET.parse(options.events + "/" + eventFileName)
        annotationElement = eventTree.getroot()
        articleSet = annotationElement.find("PubmedArticleSet")
        articles = articleSet.findall("PubmedArticle")
        for article in articles:
            medlineCitation = article.find("MedlineCitation")
            documentElement = ET.Element("document")
            documentElement.attrib["origId"] = medlineCitation.find("PMID").text
            documentElement.attrib["id"] = "GENIA.d"+str(docCount)
            documentElement.attrib["parseGraphs"] = []
            documentElements.append(documentElement)
            #print >> sys.stderr, "Article:",medlineCitation.find("PMID").text,
            articleParts = []
            if medlineCitation.find("Article") != None:
                articleParts.extend(medlineCitation.find("Article").findall("ArticleTitle"))
                if medlineCitation.find("Article").find("Abstract") != None:
                    articleParts.extend(medlineCitation.find("Article").find("Abstract").findall("AbstractText"))
            sentenceCount = 0
            for articlePart in articleParts:
                articleElements = articlePart.getchildren()
                prevParseGraph = None
                for articleElement in articleElements:
                    if articleElement.tag == "sentence":
                        sentenceCount += 1
                        sentence = articleElement
                        prevParseGraph = None
                        print >> sys.stderr, "\rArticle:",articleCount,medlineCitation.find("PMID").text, " Sentence:",sentence.attrib["id"],"       ",
                        #print >> sys.stderr, "\rSentence:",sentence.attrib["id"],
                        text = ""
                        if sentence.text != None:
                            text += sentence.text
                        children = sentence.getchildren()
                        text = getNestedChildren(text, children)
                        mergedText = text.strip()
                        mergedText = mergedText.replace(" ","").lower()
                        numSentences += 1
                        BioInferId = "UNKNOWN"
                        sentenceId = medlineCitation.find("PMID").text + "." + sentence.attrib["id"]
                        if parseGraphsByText.has_key(mergedText):
#                            if options.printSentenceText:
#                                BioInferId = parseGraphsByText[mergedText].sentence.sentence.attrib["id"]
                            eventFilesWithParse.add(eventFileName)
                            numSentencesWithParse += 1
                            #parseGraphsByText[mergedText].addEvents(sentence)
                            assert(not parseGraphsById.has_key(sentenceId))
                            parseGraphsById[sentenceId] = parseGraphsByText[mergedText]
                            parseGraphsById[sentenceId].id = sentenceId
                            parseGraph = parseGraphsById[sentenceId]
                            documentElement.attrib["parseGraphs"].append(parseGraph)
                            parseGraph.addEntities(sentence)
                            parseGraph.origGeniaId = articleElement.attrib["id"]
                            parseGraph.origGeniaDocumentId = documentElement.attrib["origId"]
                            prevParseGraph = parseGraph
#                        if options.printSentenceText:
#                            print BioInferId + ";" + sentenceId + ";" + text
                    elif articleElement.tag == "event":
                        if prevParseGraph != None:
                            prevParseGraph.addEvent(articleElement)
                    else:
                        print >> sys.stderr, "Unknown element:", articleElement.tag
                        #sys.exit(1)
            docCount += 1
        articleCount += 1
    print >> sys.stderr
    # Map events
    print >> sys.stderr, "Mapping events to parse"
    count = 1
    for parseGraph in parseGraphsById.values():
        print >> sys.stderr, "\rMapping sentence: "+parseGraph.id+", "+str(count)+"/"+str(len(parseGraphsById)),
        parseGraph.mapEventsToParse()
        count += 1
    print >> sys.stderr
    
    print >> sys.stderr, str(numSentences), "sentences,", str(numSentencesWithParse), "with parse"
    
    print >> sys.stderr, "Writing Interaction XML to", options.output
    corpusElement = ET.Element("corpus")
    corpusElement.attrib["source"] = "GENIA"
    totalSentences = 0
    documentsWithSentences = []
    for documentElement in documentElements:
        parseGraphs = documentElement.attrib["parseGraphs"]
        del documentElement.attrib["parseGraphs"]
        sentenceCount = 0
        for parseGraph in parseGraphs:
            parseGraph.writeToInteractionXML(documentElement, sentenceCount)
            sentenceCount += 1
        if sentenceCount > 0:
            documentsWithSentences.append(documentElement)
        totalSentences += sentenceCount
    
    visibleSet = Split.getSample(len(documentsWithSentences), options.visibleSet, 0)
    visibleSetDocuments = 0
    visibleSetSentences = 0
    for i in range(len(documentsWithSentences)):
        if visibleSet[i] == 0:
            documentElement = documentsWithSentences[i]
            corpusElement.append(documentElement)
            visibleSetDocuments += 1
            visibleSetSentences += len(documentElement.findall("sentence"))
    ETUtils.write(corpusElement, options.output)
    print >> sys.stderr, "Total:", str(len(documentElements)) + " documents"
    print >> sys.stderr, "Total:", str(len(documentsWithSentences)) + " documents with sentences"
    print >> sys.stderr, "Total:", str(totalSentences) + " sentences"
    print >> sys.stderr, "Visible Set:", str(visibleSetDocuments) + " documents"
    print >> sys.stderr, "Visible Set:", str(visibleSetSentences) + " sentences"
