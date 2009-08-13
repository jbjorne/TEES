import InteractionXML.CorpusElements as CorpusElements
import sys, os, shutil, copy
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source")
from Utils.ProgressCounter import ProgressCounter
import Range
import tarfile
import combine
from optparse import OptionParser

def getEntityIndex(entities, index=0, task=1):
    origIds = []
    for entity in entities:
#        if not entity.get("isName") == "True": # limit to named entites
#            continue
        if task == 1 and entity.get("type") == "Entity":
            continue
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

def processCorpus(inputCorpus, outputFolder, task=1):
    counter = ProgressCounter(len(inputCorpus.documents), "Document")
    # Each document is written to an output file
    for document in inputCorpus.documents:
        documentId = document.find("sentence").get("origId").split(".")[0]
        counter.update(1, "Processing document " + document.get("id") + " (origId " + documentId + "): ")
        
        # Write a1 file
        outputFile = open(os.path.join(outputFolder,documentId + ".a1"), "wt")
        namedEntityTriggerIds = writeProteins(document, inputCorpus, outputFile)
        outputFile.close()

        # Write a2.t1 file
        outputFile = open(os.path.join(outputFolder,documentId + ".a2.t1"), "wt")
        events, entityMap = getEvents(document, inputCorpus, outputFile, 1)
        triggerIds = copy.copy(namedEntityTriggerIds)
        writeEventTriggers(document, inputCorpus, outputFile, events, triggerIds, 1)
        writeEvents(document, inputCorpus, outputFile, events, entityMap, triggerIds)
        outputFile.close()
        
        # Write a2.t12 file
        if task == 2:
            outputFile = open(os.path.join(outputFolder,documentId + ".a2.t12"), "wt")
            events, entityMap = getEvents(document, inputCorpus, outputFile, 2)
            triggerIds = copy.copy(namedEntityTriggerIds)
            writeEventTriggers(document, inputCorpus, outputFile, events, triggerIds, 2)
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

def writeEventTriggers(document, inputCorpus, outputFile, events, triggerIds, task=1):
    entityIndex = 0
    # Find new entity index
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        entityIndex = getEntityIndex(sentence.entities, entityIndex, task)
    
    eventIdStems = set()
    for key in events.keys():
        for interaction in events[key]:
            site = interaction[1]
            if site != None:
                eventIdStems.add(site.get("e1"))
        if key.find("comb") != -1:
            eventIdStems.add(key.rsplit(".",1)[0])
        else:
            eventIdStems.add(key)
    # Write entities
    offsetMap = {}
    entityIndex += 1
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        sentenceOffset = Range.charOffsetToSingleTuple(sentenceElement.get("charOffset"))
        for entity in sentence.entities:
            if entity.get("isName") == "False":
                if entity.get("id") in eventIdStems:
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

def getEvents(document, inputCorpus, outputFile, task=1):
    events = {} # event trigger entity : list of interactions pairs
    entityMap = {}
    siteMap = {}
    for sentenceElement in document.findall("sentence"):
        sentence = inputCorpus.sentencesById[sentenceElement.get("id")]
        
        # Put entities into a dictionary where they are accessible by their id
        for entity in sentence.entities:
            if task == 1 and entity.get("type") == "Entity":
                continue
            if entityMap.has_key(entity.get("id")):
                print >> sys.stderr, "Warning: Duplicate entity", entity.get("id")
            entityMap[entity.get("id")] = entity
            
            if not siteMap.has_key(entity.get("id")):
                siteMap[entity.get("id")] = []
        # Group interactions by their interaction word, i.e. the event trigger
        for interaction in sentence.interactions + sentence.pairs:
            intType = interaction.get("type")
            if intType == "neg": # negative prediction
                continue
            if not (intType == "Theme" or intType == "Cause"):
                if task == 1:
                    continue
                elif task == 2:
                    # task 2 edges are directed (e1/site->e2/protein), so e2 is always the target
                    siteMap[interaction.get("e2")].append(interaction)
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
    
    # Create duplicate events for events with multiple sites
    newEvents = {} # Create new events here, old events will be completely replaced
    for key in sorted(events.keys()): # process all events
        eventType = entityMap[key].get("type")
        interactions = events[key]
        sites = [[]] * len(interactions) # initialize an empty list of sites for each interaction
        
        # Pick corretc sites for each interaction from siteMap
        intCount = 0
        for interaction in interactions:
            sites[intCount] = siteMap[interaction.get("e2")][:]
            intCount += 1
        
        # remove invalid sites
        for i in range(len(interactions)):
            interactionType = interactions[i].get("type")
            siteList = sites[i]
            for site in siteList[:]:
                siteType = site.get("type")
                locType = siteType.find("Loc") != -1
                if locType and (eventType == "Regulation" or eventType == "Gene_expression"):
                    siteList.remove(site)
                if siteType == "Site" and eventType == "Transcription":
                    siteList.remove(site)
                if siteType == "Site" and eventType == "Cause":
                    siteList.remove(site)
                if siteType == "CSite" and eventType == "Theme":
                    siteList.remove(site)
        
        # Replace emtpy site lists with "None", because combine.combine does not work well
        # with empty lists. With None, you get None in the correct places at the combinations    
        for i in range(len(sites)):
            if len(sites[i]) == 0:
                sites[i] = [None]
        
        # Get all combinations of sites for the interactions of the events
        combinations = combine.combine(*sites)
        combCount = 0
        # Create a new event for each combination of sites. If there were no sites, there
        # is only one combination, [None]*len(interactions).
        for combination in combinations:
            # Make up a new id that couldn't have existed before
            newEventTriggerId = key+".comb"+str(combCount)
            # Provide the new id with access to the trigger entity
            entityMap[newEventTriggerId] = entityMap[key]
            # Define the new event
            newEvents[newEventTriggerId] = []
            for i in range(len(interactions)):
                # events consist of lists of (interaction, site)-tuples
                newEvents[newEventTriggerId].append( (interactions[i], combination[i]) )
            combCount += 1
    events = newEvents
                        
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
    eventIdsByStem = {}
    for entityId in sorted(events.keys()):
        eventIds[entityId] = "E" + str(eventIndex)
        if entityId.find("comb") != -1:
            stem = entityId.rsplit(".",1)[0]
            if not eventIdsByStem.has_key(stem):
                eventIdsByStem[stem] = []
            eventIdsByStem[stem].append("E" + str(eventIndex))
        else:
            eventIdsByStem[entityId] = ["E" + str(eventIndex)]
        eventIndex += 1
    
#    seenOutputLines = []
    # Write the events
    sites = []
    for key in sorted(events.keys()):
        entity = entityMap[key]
        eventType = entity.get("type")
        assert(key == entity.get("id") or key.rsplit(".",1)[0] == entity.get("id"))
        outputLine = eventIds[key] + "\t" + eventType + ":" + triggerIds[entity.get("id")]
        siteLine = ""
        assert( len(events[key]) > 0 )
        themeCount = 0
        causeCount = 0
        interactionStrings = set()
        for interactionTuple in events[key]:
            interaction = interactionTuple[0]
            site = interactionTuple[1]
            type = interaction.get("type")
            assert(type=="Theme" or type=="Cause")
            if site != None:
                siteType = site.get("type")
                if type == "Theme" and siteType == "CSite":
                    siteType = "Site"
                elif type == "Cause" and siteType == "Site":
                    siteType = "CSite"
            
            e1 = entityMap[interaction.get("e1")]
            e2 = entityMap[interaction.get("e2")]
            assert(e1 == entity)
            if e2.get("id") in eventIdsByStem: # e2 is a nested event
                e2Id = eventIdsByStem[e2.get("id")][0]
            else: # e2 should be a named entity, i.e. protein
                assert( e2.get("isName") != "False") # a trigger with no interactions
                e2Id = triggerIds[e2.get("id")]
            
            # Look out for duplicates, and add numbering as needed
            interactionString = interaction.get("type") + ":" + e2Id
            if interactionString not in interactionStrings:
                if type == "Theme" and themeCount > 0:
                    outputLine += " " + interaction.get("type") + str(themeCount+1) + ":" + e2Id
                    if site != None:
                        siteLine += " " + siteType + str(themeCount) + ":" + triggerIds[site.get("e1")]
                else:
                    outputLine += " " + interactionString
                    if site != None:
                        siteLine += " " + siteType + ":" + triggerIds[site.get("e1")]
            interactionStrings.add(interactionString) 
            
            if type == "Theme":
                themeCount += 1
            else:
                causeCount += 1
        assert( not(causeCount == 0 and themeCount == 0) )
        assert( not(causeCount > 0 and themeCount == 0) )
# wondering about duplicates, but they were a result of how sites are defined
#        outputLineWithoutId = outputLine.split("\t",1)[-1]
#        if outputLineWithoutId in seenOutputLines:
#            print >> sys.stderr, "Warning: Duplicate output line", outputLine
#        else:
#            seenOutputLines.append(outputLineWithoutId)
        outputLine += siteLine
        outputFile.write( outputLine + "\n" )           

def gifxmlToGenia(input, output, task=1):
    assert(task == 1 or task == 2)
    
    # Make or clear output directory
    if os.path.exists(output):
        print >> sys.stderr, "Output directory exists, removing", output
        shutil.rmtree(output)
    os.mkdir(output)
    
    # Convert the gifxml to the genia format files
    inputCorpus = CorpusElements.loadCorpus(input, removeIntersentenceInteractions=False)
    processCorpus(inputCorpus, output, task)
    
    # Make the tar.gz-fiel for submission
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
    optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    (options, args) = optparser.parse_args()
    
    assert(options.input != None)
    assert(options.output != None)    
    gifxmlToGenia(options.input, options.output, options.task)
