parse__version__ = "$Revision: 1.3 $"

import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.IDUtils as IDUtils
import types
from collections import defaultdict
import Utils.FindHeads as FindHeads

def getText(element):
    text = ""
    if element.text != None:
        text += element.text
    for child in list(element):
        text += getText(child)
    if element.tail != None:
        text += element.tail
    return text

def getClue(element):
    if element.tag == "clueType":
        clueText = element.text
        return [clueText, 0, 0]
    
    text = ""
    if element.text != None:
        text += element.text
    for child in list(element):
        childText = getClue(child) 
        if type(childText) == types.StringType:
            text += childText
        else:
            childText[1] = len(text)
            childText[2] = len(text) + len(childText[0]) - 1
            return childText
    if element.tail != None:
        text += element.tail
    return text

def loadEventXML(path, verbose=False):
    xml = ETUtils.ETFromObj(path)
    sentDict = {}
    for sentence in xml.getiterator("sentence"):
        sentenceText = getText(sentence).strip()
        if not sentDict.has_key(sentenceText):
            sentDict[sentenceText] = []

    for event in xml.getiterator("event"):
        sentenceText = getText(event).strip()
        if not sentDict.has_key(sentenceText):
            sentDict[sentenceText] = []
        events = sentDict[sentenceText]
        
        clue = event.find("clue")
        clueTuple = getClue(clue)
        eventType = event.find("type").get("class")
        if eventType == "Protein_amino_acid_phosphorylation":
            eventType = "Phosphorylation"
        if type(clueTuple) == types.StringType:
            if verbose: print "Event", eventType, "clue with no clueType:", ETUtils.toStr(clue)
        else:
            assert sentenceText[clueTuple[1]:clueTuple[2]+1] == clueTuple[0], (sentenceText, sentenceText[clueTuple[1]:clueTuple[2]+1], clueTuple)
            event = (clueTuple[1], clueTuple[2], eventType, clueTuple[0])
            if event not in events:
                events.append(event)
    return sentDict

def keepEvent(eventType):
    if eventType in ["Gene_expression", "Transcription", "Protein_catabolism", "Localization", "Binding", "Phosphorylation", "Positive_regulation", "Negative_regulation", "Regulation"]:
        return True
    else:
        return False

def removeDuplicates(input):
    print "Removing duplicate triggers"
    counts = {}
    for sentence in input.getiterator("sentence"):
        origTriggers = []
        newTriggers = []
        for entity in sentence.findall("entity"):
            if entity.get("given") in (None, "False"):
                if entity.get("source") == "GENIA_event_annotation_0.9":
                    newTriggers.append(entity)
                else:
                    origTriggers.append(entity)
        for origTrig in origTriggers:
            countType = "origTrig-" + origTrig.get("type")
            if not counts.has_key(countType):
                counts[countType] = 0
            counts[countType] += 1            
        for newTrig in newTriggers[:]:
            removed = False
            for origTrig in origTriggers:
                if newTrig.get("headOffset") == origTrig.get("headOffset"):
                    sentence.remove(newTrig)
                    newTriggers.remove(newTrig)
                    removed = True
                    countType = "removed-N/O-" + newTrig.get("type") + "/" + origTrig.get("type")
                    if not counts.has_key(countType):
                        counts[countType] = 0
                    counts[countType] += 1
                    break
            if not removed:
                countType = "newTrig-" + newTrig.get("type")
                if not counts.has_key(countType):
                    counts[countType] = 0
                counts[countType] += 1
    print "Counts:"
    for k in sorted(counts.keys()):
        print " ", k, counts[k]

def run(input, output, eventDir, parse="split-mccc-preparsed", verbose=False):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    counts = defaultdict(int)
    for document in corpusRoot.findall("document"):
        sentDict = None
        pmid = document.get("pmid")
        isPMC = False
        for sentence in document.findall("sentence"):
            counts["sentences"] += 1
            sentenceId = str(sentence.get("id")) + "/" + str(sentence.get("origId"))
            if verbose: print "Processing", sentenceId
            if sentDict == None:
                if sentence.get("origId") != None:
                    assert pmid == None
                    sentDict = loadEventXML( eventDir + "/" + sentence.get("origId").split(".")[0] + ".xml" , verbose=verbose)
                else:
                    #pmid = sentence.get("pmid")
                    assert pmid != None
                    if pmid.startswith("PMC"):
                        isPMC = True
                        sentDict = {}
                    else:
                        assert pmid.startswith("PMID")
                        sentDict = loadEventXML( eventDir + "/" + pmid.split("-", 1)[-1] + ".xml" , verbose=verbose)
            interactionXMLText = sentence.get("text")
            if not sentDict.has_key(interactionXMLText):
                counts["missing-sentences"] += 1
                if isPMC: counts["missing-sentences-PMC"] += 1
                if verbose: print "Missing sentence:", pmid, (sentenceId, sentDict, sentence.get("text"))
            else:
                sentenceAnalyses = sentence.find("sentenceanalyses")
                if sentenceAnalyses != None:
                    sentence.remove(sentenceAnalyses)
                entityIdCount = IDUtils.getNextFreeId(sentence.findall("entity"))
                events = sentDict[interactionXMLText]
                events.sort()
                for event in events:
                    if not keepEvent(event[2]):
                        counts["filtered-triggers"] += 1
                        continue
                    trigger = ET.Element("entity")
                    #trigger.set("given", "False")
                    trigger.set("charOffset", str(event[0]) + "-" + str(event[1]))
                    trigger.set("type", str(event[2]))
                    trigger.set("text", str(event[3]))
                    trigger.set("source", "GENIA_event_annotation_0.9")
                    trigger.set("id", sentence.get("id") + ".e" + str(entityIdCount))
                    entityIdCount += 1
                    counts["added-triggers"] += 1
                    sentence.append(trigger)
                if sentenceAnalyses != None:
                    sentence.append(sentenceAnalyses)
    
    FindHeads.findHeads(corpusTree, parse, removeExisting=False)
    removeDuplicates(corpusRoot)
    print counts
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree
    
if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-e", "--eventDir", default="/home/jari/data/GENIA_event_annotation_0.9/GENIAcorpus_event", dest="eventDir", help="Output file in interaction xml format.")
    optparser.add_option("-p", "--parse", default="split-mccc-preparsed", dest="parse", help="Parse XML element name")
    optparser.add_option("-v", "--verbose", default=False, action="store_true", dest="verbose", help="verbose mode")
    (options, args) = optparser.parse_args()
    assert options.input != None
    
    run(input=options.input, output=options.output, eventDir=options.eventDir, parse=options.parse, verbose=options.verbose)
    