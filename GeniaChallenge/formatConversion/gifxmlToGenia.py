import InteractionXML.CorpusElements as CorpusElements
import sys, os, shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source")
from Utils.ProgressCounter import ProgressCounter
import Range
from optparse import OptionParser

def getEntityIndex(entities, index=0):
    origIds = []
    for entity in entities:
        origId = entity.get("origId")
        if origId != None:
            origIds.append(origId)
    for origId in origIds:
        idPart = origId.split(".")[-1]
        assert(idPart[0] == "T")
        newIndex = int(idPart[1:])
        if newIndex > index:
            index = newIndex
    return index

def processCorpus(inputCorpus, outputFolder):
    counter = ProgressCounter(len(inputCorpus.documents), "Document")
    # Each document is written to an output file
    for document in inputCorpus.documents:
        documentId = document.find("sentence").get("origId").split(".")[0]
        outputFile = open(os.path.join(outputFolder,documentId + ".a2"), "wt")
        counter.update()
        
        writeEventTriggers(document, inputCorpus, outputFile)
        findThemeCausePairs(document, inputCorpus)
        writeEvents(document, inputCorpus, outputFile)
        
        outputFile.close()

def writeEventTriggers(document, inputCorpus, outputFile):
    entityIndex = 0
    # Find new entity index
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        entityIndex = getEntityIndex(sentence.entities, entityIndex)
    # Write entities
    entityIndex += 1
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        sentenceOffset = Range.charOffsetToSingleTuple(sentenceElement.get("charOffset"))
        for entity in sentence.entities:
            if entity.get("isName") == "False":
                newId = "T" + str(entityIndex)
                entity.set("temp_newId", newId)
                entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
                newOffset = [entityOffset[0] + sentenceOffset[0], entityOffset[1] + sentenceOffset[1]]
                outputFile.write( newId + "\t" + entity.get("type") + " " + str(newOffset[0]) + " " + str(newOffset[1]) + "\t" + entity.get("text") + "\n" )
                entityIndex += 1
            else:
                entity.set("temp_newId", entity.get("origId").split(".")[-1])

def findThemeCausePairs(document, inputCorpus):
    for sentenceElement in document.findall("sentence"): 
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        sentenceOffset = sentenceElement.get("charOffset")
        for interaction in sentence.interactions:
            if interaction.get("type") == "Cause":
                for interaction2 in sentence.interactions:
                    if interaction2.get("type") == "Theme":
                        if interaction2.get("temp_eventCause") != None:
                            assert(interaction2.get("temp_eventCause") != interaction)
                        else:
                            interaction2.set("temp_eventCause", interaction)
                            interaction.set("temp_eventTheme", interaction2)
                            print sentence.get("origId")

def writeEvents(document, inputCorpus, outputFile):
    # Write events
    eventIndex = 1
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        sentenceOffset = sentenceElement.get("charOffset")
        interactions = sentence.interactions + sentence.pairs
        for interaction in interactions:
            type = interaction.get("type")
            if type == "Theme" or (type == "Cause" and interaction.get("temp_eventTheme") == None):
                eventId = "E" + str(eventIndex)
                e1 = sentence.entitiesById[interaction.get("e1")]
                eventType = e1.get("type")
                outputLine = eventId + "\t" + eventType + ":" + e1.get("temp_newId")
                # Add primary Theme/Cause
                e2 = sentence.entitiesById[interaction.get("e2")]
                outputLine += " " + type + ":" + e2.get("temp_newId")
                # Add secondary Cause if it exists
                if interaction.get("temp_eventCause") != None:
                    causeTarget = sentence.entitiesById[interaction.get("temp_eventCause").get("e2")]
                    outputLine += " Cause:" + causeTarget.get("temp_newId")
                outputFile.write( outputLine + "\n" )
                eventIndex += 1

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nConvert interaction XML to GENIA shared task format.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="interaction xml input file", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    (options, args) = optparser.parse_args()
    
    assert(options.input != None)
    assert(options.output != None)
    if os.path.exists(options.output):
        print >> sys.stderr, "Output directory exists, removing", options.output
        shutil.rmtree(options.output)
    os.mkdir(options.output)
        
    inputCorpus = CorpusElements.loadCorpus(options.input)
    processCorpus(inputCorpus, options.output)
    
    
