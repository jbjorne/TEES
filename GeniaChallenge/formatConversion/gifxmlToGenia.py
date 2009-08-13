import InteractionXML.CorpusElements as CorpusElements
import sys, os, shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source")
from Utils.ProgressCounter import ProgressCounter
import Range
import tarfile
from optparse import OptionParser

def getEntityIndex(entities, index=0):
    origIds = []
    for entity in entities:
        origId = entity.get("origId")
        if origId != None:
            origIds.append(origId)
    for origId in origIds:
        splits = origId.split(".")
        idPart = splits[1]
        #print origId
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
        counter.update(1, "Processing document " + document.get("id") + " (origId " + documentId + "): ")
        
        # Write a1 file
        outputFile = open(os.path.join(outputFolder,documentId + ".a1"), "wt")
        triggerIds = writeProteins(document, inputCorpus, outputFile)
        outputFile.close()

        # Write a2.t1 file
        outputFile = open(os.path.join(outputFolder,documentId + ".a2.t1"), "wt")
        events, entityMap = getEvents(document, inputCorpus, outputFile)
        writeEventTriggers(document, inputCorpus, outputFile, events, triggerIds)
        writeEvents(document, inputCorpus, outputFile, events, entityMap, triggerIds)
        outputFile.close()
        
        # Write txt file
        outputFile = open(os.path.join(outputFolder,documentId + ".txt"), "wt")
        writeDocumentText(document, outputFile)
        outputFile.close()

def writeDocumentText(document, outputFile):
    """
    Write the sentences that came from the same document into the same genia-file
    """
    isFirstSentence = True
    for sentenceElement in document.findall("sentence"):
        text = sentenceElement.get("text")
        outputFile.write(text + " ")
        if isFirstSentence:
            outputFile.write("\n")
            isFirstSentence = False

def getGeniaOffset(sentenceOffset, entityOffset):
    return [entityOffset[0] + sentenceOffset[0], entityOffset[1] + sentenceOffset[0] + 1] 

def writeProteins(document, inputCorpus, outputFile):
    entityMap = {}
    offsetMap = {}
    triggerMap = {}
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        sentenceOffset = Range.charOffsetToSingleTuple(sentenceElement.get("charOffset"))
        for entity in sentence.entities:
            if entity.get("isName") == "True":
                origId = entity.get("origId").split(".")[-1]
                origIdNumber = int(origId[1:])
                assert(origIdNumber not in entityMap.keys())
                entityMap[origIdNumber] = entity
                
                entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
                offsetMap[origIdNumber] = getGeniaOffset(sentenceOffset, entityOffset)
                triggerMap[entity.get("id")] = origId
    for key in sorted(entityMap.keys()):
        entity = entityMap[key]
        outputFile.write(triggerMap[entity.get("id")] + "\tProtein " + str(offsetMap[key][0]) + " " + str(offsetMap[key][1]) + "\t" + entity.get("text") + "\n")
    return triggerMap

def writeEventTriggers(document, inputCorpus, outputFile, events, triggerIds):
    entityIndex = 0
    # Find new entity index
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        entityIndex = getEntityIndex(sentence.entities, entityIndex)
    # Write entities
    offsetMap = {}
    entityIndex += 1
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        sentenceOffset = Range.charOffsetToSingleTuple(sentenceElement.get("charOffset"))
        for entity in sentence.entities:
            if entity.get("isName") == "False":
                if entity.get("id") in events:
                    entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
                    newOffset = getGeniaOffset(sentenceOffset, entityOffset)
                    match = Range.tuplesToCharOffset(newOffset) + "_" + entity.get("type")
                    if match in offsetMap.keys():
                        #assert(not triggerIds.has_key(entity.get("id")))
                        if triggerIds.has_key(entity.get("id")):
                            print >> sys.stderr, "Warning: Duplicate entity (trigger)", entity.get("id")
                        triggerIds[entity.get("id")] = offsetMap[match]
                    else:
                        triggerId = "T" + str(entityIndex)
                        outputFile.write( triggerId + "\t" + entity.get("type") + " " + str(newOffset[0]) + " " + str(newOffset[1]) + "\t" + entity.get("text") + "\n" )
                        offsetMap[match] = triggerId
                        assert(not triggerIds.has_key(entity.get("id")))
                        triggerIds[entity.get("id")] = triggerId
                        entityIndex += 1
    return triggerIds

def getEvents(document, inputCorpus, outputFile):
    events = {} # event trigger entity : list of interactions pairs
    entityMap = {}
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        
        # Put entities into a dictionary where they are accessible by their id
        for entity in sentence.entities:
            if entityMap.has_key(entity.get("id")):
                print >> sys.stderr, "Warning: Duplicate entity", entity.get("id")
            entityMap[entity.get("id")] = entity
        # Group interactions by their interaction word, i.e. the event trigger
        for interaction in sentence.interactions + sentence.pairs:
            if interaction.get("type") == "neg": # negative prediction
                continue
            # All interactions are directed (e1->e2), so e1 is always the trigger
            e1 = sentence.entitiesById[interaction.get("e1")]
            assert(e1.get("isName") == "False")
            if not events.has_key(interaction.get("e1")):
                events[interaction.get("e1")] = [] # mark entity as an event trigger
            events[interaction.get("e1")].append(interaction)
            #if interaction.get("e1") == "GENIA.d10.s5.e2":
            #    print events[interaction.get("e1")]
    
    # remove empty events
    removeCount = 1
    while removeCount > 0:
        removeCount = 0
        for key in sorted(events.keys()):
            if events.has_key(key):
                themeCount = 0
                causeCount = 0
                for interaction in events[key][:]:
                    type = interaction.get("type")
                    assert(type=="Theme" or type=="Cause")
                    e2 = entityMap[interaction.get("e2")]
                    if e2.get("isName") == "False":
                        if not events.has_key(e2.get("id")):
                            #print "Jep"
                            events[key].remove(interaction)
                            continue
                    if type == "Theme":
                        themeCount += 1
                    else:
                        causeCount += 1
                if causeCount == 0 and themeCount == 0:
                    print >> sys.stderr, "Removing: Event with no arguments", key
                    del events[key]
                    removeCount += 1
                elif causeCount > 0 and themeCount == 0:
                    print >> sys.stderr, "Removing: Event with Cause and no Themes", key
                    del events[key]
                    removeCount += 1
    return events, entityMap                  

def writeEvents(document, inputCorpus, outputFile, events, entityMap, triggerIds):
    """
    Writes events defined as trigger words that have one or more interactions
    leaving from them. When the Theme or Cause of such an event refers to a
    trigger that is also an event, the Theme or Cause will point to that event (E).
    Note that if the Theme or Cause is an event-trigger, and even if that trigger
    has no defined interactions, and empty event will be generated to mark the 
    nested event.
    """
    # Predefine event ids because all ids must be defined so that
    # we can refer to nested events
    eventIds = {}
    eventIndex = 1
    for entityId in sorted(events.keys()):
        eventIds[entityId] = "E" + str(eventIndex)
        eventIndex += 1
    
    # Write the events
    for key in sorted(events.keys()):
        entity = entityMap[key]
        eventType = entity.get("type")
        assert(key == entity.get("id"))
        outputLine = eventIds[key] + "\t" + eventType + ":" + triggerIds[key]
        assert( len(events[key]) > 0 )
        themeCount = 0
        causeCount = 0
        interactionStrings = set()
        for interaction in events[key]:
            type = interaction.get("type")
            assert(type=="Theme" or type=="Cause")
            e1 = entityMap[interaction.get("e1")]
            e2 = entityMap[interaction.get("e2")]
            assert(e1 == entity)
            if eventIds.has_key(e2.get("id")): # e2 is a nested event
                e2Id = eventIds[e2.get("id")]
            else: # e2 should be a named entity, i.e. protein
                assert( e2.get("isName") != "False") # a trigger with no interactions
                e2Id = triggerIds[e2.get("id")]
            
            # Look out for duplicates
            interactionString = interaction.get("type") + ":" + e2Id
            if interactionString not in interactionStrings:
                if type == "Theme" and themeCount > 0:
                    outputLine += " " + interaction.get("type") + str(themeCount+1) + ":" + e2Id
                else:
                    outputLine += " " + interactionString
            interactionStrings.add(interactionString) 
            
            if type == "Theme":
                themeCount += 1
            else:
                causeCount += 1
        assert( not(causeCount == 0 and themeCount == 0) )
        assert( not(causeCount > 0 and themeCount == 0) )
        outputFile.write( outputLine + "\n" )           

def gifxmlToGenia(input, output):
    if os.path.exists(output):
        print >> sys.stderr, "Output directory exists, removing", output
        shutil.rmtree(output)
    os.mkdir(output)
        
    inputCorpus = CorpusElements.loadCorpus(input, removeIntersentenceInteractions=False)
    processCorpus(inputCorpus, output)

    submissionFileName = output.split("/")[-1] + ".tar.gz"    
    print >> sys.stderr, "Making submission file", submissionFileName
    allFiles = os.listdir(output)
    tarFiles = []
    for file in allFiles:
        if file.find("a2.t1") != -1:
            tarFiles.append(file)
    submissionFile = tarfile.open(os.path.join(output,submissionFileName), "w:gz")
    tempCwd = os.getcwd()
    os.chdir(output)
    for file in tarFiles:
        submissionFile.add(file)#, exclude = lambda x: x == submissionFileName)
    os.chdir(tempCwd)
    submissionFile.close()
#    #tar -cvzf 090224-results.tar.gz *.a2.t1
#    #print os.getcwd()
#    tarCall = ["tar", "-cvzf", submissionFileName, "\"*.a2.t1\""]
#    #print zipCall
#    subprocess.call(tarCall)

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
    gifxmlToGenia(options.input, options.output)
