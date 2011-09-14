import sys, os, time
import subprocess
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.Stream as Stream
import Utils.FindHeads as FindHeads
import Tools.GeniaSentenceSplitter
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../../../../GeniaChallenge/formatConversion")))
import ProteinNameSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import InteractionXML.CopyParse
import InteractionXML.DeleteElements
import collections
from collections import defaultdict
import Range
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
import cElementTreeUtils as ETUtils

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def readEventsFromSR(eventType, srDir, events, idByNorText=True):
    for dataSet in ["train", "test"]:
        print "Reading events from", os.path.join(srDir, dataSet + ".txt")
        f = open(os.path.join(srDir, dataSet + ".txt"))
        lines = f.readlines()
        i = 0
        while i < len(lines):
            id = lines[i].strip()
            text = lines[i+1].strip()
            entity = lines[i+2].strip()
            namedEntity = lines[i+3].strip()
            interaction = lines[i+4].strip()
            assert lines[i+5].strip() == ""
            i += 6
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            if idByNorText:
                norText = text.replace(" ", "")
                groupId = norText
            else:
                groupId = id.rsplit("-", 1)[0] 
            if groupId not in events:
                events[groupId] = []
            event = {"id":id, "text":text, "entity":entity, "namedEntity":namedEntity, "interaction":interaction, "dataSet":dataSet, "eventType":eventType}
            events[groupId].append(event)
        f.close()

def getOffset(string):
    a, b = string.split("-")
    a = int(a)
    b = int(b)
    return (a,b-1)

def eventsToNewXML(events):
    xml = ET.Element("corpus")
    xml.set("source", "Static Relations")
    docCount = 0
    sentenceById = {}
    for sentenceId in sorted(events.keys()):
        entities = []
        interactions = []
        entityByOffset = {}
        for event in events[sentenceId]:
            #print event
            if sentenceId not in sentenceById:
                document = ET.SubElement(xml, "document")
                document.set("id", "SR.d"+str(docCount))
                document.set("origId", sentenceId)
                document.set("set", event["dataSet"])
                sentence = ET.SubElement(document, "sentence")
                sentence.set("id", "SR.d"+str(docCount)+".s"+str(docCount))
                sentence.set("origId", sentenceId)
                sentence.set("text", event["text"])
                sentence.set("charOffset", "0-"+str(len(event["text"])-1))
                docCount += 1
                sentenceById[sentenceId] = sentence
            else:
                sentence = sentenceById[sentenceId]
                assert sentence.get("text") == event["text"], (sentence.get("text"), event["text"])
            # Add entities
            e1Offset = event["entity"].split("\t")[0]
            e2Offset = event["namedEntity"].split("\t")[0]
            if e1Offset not in entityByOffset:
                e1 = ET.Element("entity")
                e1.set("text", event["entity"].split("\t")[1].strip())
                e1.set("id", sentence.get("id")+".e"+str(len(entities)))
                offset = getOffset(event["entity"].split("\t")[0])
                assert sentence.get("text")[offset[0]:offset[1]+1] == e1.get("text"), (event, sentence.get("text"), e1.get("text"))
                e1.set("charOffset", str(offset[0]) + "-" + str(offset[1]))
                e1.set("isName", "False")
                e1.set("type", "Entity")
                entities.append(e1)
                entityByOffset[e1Offset] = e1
            else:
                e1 = entityByOffset[e1Offset]
            if e2Offset not in entityByOffset:
                e2 = ET.Element("entity")
                e2.set("text", event["namedEntity"].split("\t")[1].strip())
                e2.set("id", sentence.get("id")+".e"+str(len(entities)))
                offset = getOffset(event["namedEntity"].split("\t")[0])
                assert sentence.get("text")[offset[0]:offset[1]+1] == e2.get("text"), (event, sentence.get("text"), e2.get("text"))
                e2.set("charOffset", str(offset[0]) + "-" + str(offset[1]))
                e2.set("isName", "True")
                e2.set("type", "Protein")
                entities.append(e2)
                entityByOffset[e2Offset] = e2
            else:
                e2 = entityByOffset[e2Offset]
            # Add interactions
            interaction = ET.Element("interaction")
            interaction.set("id", sentence.get("id")+".i"+str(len(interactions)))
            interaction.set("origId", event["id"])
            interaction.set("type", event["eventType"])
            interaction.set("e1", e1.get("id"))
            interaction.set("e2", e2.get("id"))
            interactions.append(interaction)
        for entity in entities:
            sentence.append(entity)
        for interaction in interactions:
            sentence.append(interaction)
    return xml

def eventsToXML(events, xmlEvents, dataSets, srTexts):
    for norText in events.keys():
        usedOffsets = set()
        entitiesByOffset = {}
        entityCount = 0
        interactionCount = 0
        xmlEvents[norText] = {"entities":[], "interactions":[]}
        dataSet = None
        for event in events[norText]:
            srTexts[norText] = event["text"]
            if dataSet == None:
                dataSet = event["dataSet"]
            else:
                assert dataSet == event["dataSet"]
            # Add entity
            offset, entityText = event["entity"].replace("\t", " ").split(" ", 1)
            if offset not in usedOffsets:
                entity = ET.Element("entity")
                entity.set("charOffset", offset)
                entity.set("text", entityText)
                entity.set("type", "Entity")
                entity.set("isName", "False")
                entity.set("id", "e" + str(entityCount))
                entity.set("srId", event["id"])
                entityCount += 1
                usedOffsets.add(offset)
                entitiesByOffset[offset] = entity
                xmlEvents[norText]["entities"].append(entity)
            else:
                entity = entitiesByOffset[offset]
            # Add named entity
            offset, entityText = event["namedEntity"].replace("\t", " ").split(" ", 1)
            if offset not in usedOffsets:
                namedEntity = ET.Element("entity")
                namedEntity.set("charOffset", offset)
                namedEntity.set("text", entityText)
                namedEntity.set("type", "Protein")
                namedEntity.set("isName", "True")
                namedEntity.set("id", "e" + str(entityCount))
                namedEntity.set("srId", event["id"])
                entityCount += 1
                usedOffsets.add(offset)
                entitiesByOffset[offset] = namedEntity
                xmlEvents[norText]["entities"].append(namedEntity)
            else:
                namedEntity = entitiesByOffset[offset]
            # Add interactions
            if event["interaction"] == "Yes":
                interaction = ET.Element("interaction")
                interaction.set("type", "SR-" + event["eventType"])
                interaction.set("directed", "False")
                interaction.set("e1", entity.get("id"))
                interaction.set("e2", namedEntity.get("id"))
                interaction.set("id", "i" + str(interactionCount))
                interaction.set("srId", event["id"])
                xmlEvents[norText]["interactions"].append(interaction)
                interactionCount += 1
            else:
                assert event["interaction"] == "No", event["interaction"]
        dataSets[norText] = dataSet
    #return xmlEvents, dataSets

def insertEvents(xmlEvents, dataSets, srTexts, xml, corpusName):
    counts = collections.defaultdict(int)
    counts["SR-sentences"] = len(xmlEvents.keys())
    foundSRSentences = set()
    root = xml.getroot()
    documentsToKeep = set()
    for document in xml.getiterator("document"):
        namedEntityCount = 1
        document.set("id", corpusName + "." + document.get("id").split(".", 1)[-1])
        for sentence in document.findall("sentence"):
            sentenceId = corpusName + "." + sentence.get("id").split(".", 1)[-1]
            sentence.set("id", sentenceId)
            counts["sentences-total"] += 1
            sentNorText = sentence.get("text").replace(" ", "")
            sentText = sentence.get("text")
            sentenceAnalysesElement = None
            # Remove existing elements
            for element in sentence.getchildren():
                if element.tag in ["entity", "interaction"]:
                    sentence.remove(element)
                elif element.tag == "sentenceanalyses":
                    sentence.remove(element)
                    sentenceAnalysesElement = element
            # Add new elements
            if sentNorText not in xmlEvents:
                #document.remove(sentence)
                counts["sentences-nostatic"] += 1
                sentenceAnalysesElement = None
                sentence.text = None
                #if sentenceAnalysesElement != None:
                    #for element in sentenceAnalysesElement.getchildren():
                    #    sentenceAnalysesElement.remove(element)
            else:
                documentsToKeep.add(document)
                foundSRSentences.add(sentNorText)
                alignment = alignStrings(srTexts[sentNorText], sentence.get("text"))
                if dataSets[sentNorText] == "test":
                    document.set("set", "devel")
                else:
                    assert dataSets[sentNorText] != "devel"
                    document.set("set", dataSets[sentNorText])
                counts["sentences-kept"] += 1
                for entity in xmlEvents[sentNorText]["entities"]:
                    entity.set("id", sentenceId + "." + entity.get("id"))
                    entityOffset = entity.get("charOffset")
                    entity.set("srOffset", entityOffset)
                    entityOffset = Range.charOffsetToSingleTuple(entityOffset)
                    entityOffset = (entityOffset[0], entityOffset[1] - 1)
                    assert len(entityOffset) == 2, entityOffset
                    assert entityOffset[0] < len(alignment) and entityOffset[1] < len(alignment), (entity.get("text"), entityOffset, alignment)
                    entityOffset = (alignment[entityOffset[0]], alignment[entityOffset[1]])
                    entity.set("charOffset", str(entityOffset[0]) + "-" + str(entityOffset[1]))
                    assert sentText[entityOffset[0]:entityOffset[1]+1].replace(" ", "") == entity.get("text").replace(" ", ""), (sentText[entityOffset[0]:entityOffset[1]+1], entity.get("text"))
                    sentence.append(entity)
                    counts["entities-added"] += 1
                    if entity.get("isName") == "True":
                        entity.set("origId", "SR.T"+str(namedEntityCount))
                        namedEntityCount += 1
                for interaction in xmlEvents[sentNorText]["interactions"]:
                    interaction.set("id", sentenceId + "." + interaction.get("id"))
                    interaction.set("e1", sentenceId + "." + interaction.get("e1"))
                    interaction.set("e2", sentenceId + "." + interaction.get("e2"))
                    sentence.append(interaction)
                    counts["interactions-added"] += 1
            # Reattach analyses
            if sentenceAnalysesElement != None:
                sentence.append(sentenceAnalysesElement)
    for document in root.findall("document"):
        if document not in documentsToKeep:
            counts["documents-removed"] += 1
            root.remove(document)
    print "Finished inserting SR", counts
    for key in srTexts:
        if key not in foundSRSentences:
            print "Missing sentence", xmlEvents[key]["entities"][0].get("srId"), srTexts[key]
    
def alignStrings(s1, s2):
    mapping = []
    s2Pos = 0
    for char1 in s1:
        if char1.isspace():
            mapping.append(None)
            continue
        while s2[s2Pos] != char1:
            s2Pos += 1
        mapping.append(s2Pos)
        s2Pos += 1
    return mapping

def convert(srFiles, xmlFileName, outdir, corpusName, idByNorText=False):
    print >> sys.stderr, "Loading Static Relations"
    events = {}
    for srFile in srFiles:
        readEventsFromSR(srFile[0], srFile[1], events, idByNorText=idByNorText)
    
    if xmlFileName != None:
        xmlEvents = {}
        dataSets = {}
        srTexts = {} # original, unnormalized sentence texts from the SR corpus
        eventsToXML(events, xmlEvents, dataSets, srTexts)
        
        print >> sys.stderr, "Loading XML"
        xml = ETUtils.ETFromObj(xmlFileName)
        print >> sys.stderr, "Inserting XML events"
        insertEvents(xmlEvents, dataSets, srTexts, xml, corpusName)
        ETUtils.write(xml, outdir+corpusName+"-srevents.xml")
        # update pre-existing parses
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(xml, "split-mccc-preparsed", tokenization=None, output=outdir+corpusName+"-heads.xml", removeExisting=True)
        print >> sys.stderr, "Dividing into sets"
        InteractionXML.DivideSets.processCorpus(xml, outDir, corpusName + "-", ".xml", [("devel", "train")])
        print >> sys.stderr, "Converting back"
        STConvert.toSTFormat(outdir+corpusName + "-devel.xml", outDir + corpusName + "-stformat-devel", outputTag="rel", task=2, debug=True, validate=False)
        STConvert.toSTFormat(outdir+corpusName + "-train.xml", outDir + corpusName + "-stformat-train", outputTag="rel", task=2, debug=True, validate=False)
    else:
        xml = eventsToNewXML(events)
        xmlTree = ET.ElementTree(xml)
        ETUtils.write(xml, outdir+corpusName+"-srevents.xml")
        xml = xmlTree
        # Parse
        bigfileName = outdir+corpusName
        print >> sys.stderr, "Parsing"
        Tools.CharniakJohnsonParser.parse(xml, bigfileName+"-parsed.xml", tokenizationName="PARSED_TEXT", parseName="McClosky", requireEntities=True, timeout=60)
        print >> sys.stderr, "Stanford Conversion"
        Tools.StanfordParser.convertXML("McClosky", xml, bigfileName+"-stanford.xml")
        print >> sys.stderr, "Protein Name Splitting"
        splitTarget = "McClosky"
        xml = ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(xml, "split-McClosky", tokenization=None, output=bigfileName+".xml", removeExisting=True)
        print >> sys.stderr, "Dividing into sets"
        InteractionXML.DivideSets.processCorpus(xml, outDir, "SRNE-", ".xml")    

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    #relCorpusPath = "/home/jari/biotext/BioNLP2011/data/main-tasks/GE/GE-devel-and-train-and-test.xml"
    relCorpusPath = None

    if True:
        # non-embed
        outDir = "/usr/share/biotext/StaticRelations/data/nonembed/"
        datasets = [("memberof", "/home/jari/data/StaticRelations/sr_data/nonembed/GGP_memberof_Term"), 
                    ("subunitof", "/home/jari/data/StaticRelations/sr_data/nonembed/GGP_subunitof_Term"), 
                    ("partof", "/home/jari/data/StaticRelations/sr_data/nonembed/Term_partof_GGP")]
        
        cwd = os.getcwd()
        if not os.path.exists(outDir): os.makedirs(outDir)
        os.chdir(outDir)
        log(False, False, "sr-nonembed-conversion-log.txt")
        convert(datasets, relCorpusPath, outDir, "SRNE")
        os.chdir(cwd)
    
    # embed
    outDir = "/usr/share/biotext/StaticRelations/data/embed/"
    datasets = [("subunitof", "/home/jari/data/StaticRelations/sr_data/embed/GGP_subunitof_EmbeddingTerm"), 
                ("equivto", "/home/jari/data/StaticRelations/sr_data/embed/Term_equivto_EmbeddedGGP"), 
                ("partof", "/home/jari/data/StaticRelations/sr_data/embed/Term_partof_EmbeddedGGP")]
    
    cwd = os.getcwd()
    if not os.path.exists(outDir): os.makedirs(outDir)
    os.chdir(outDir)
    log(False, False, "sr-embed-conversion-log.txt")
    convert(datasets, relCorpusPath, outDir, "SRE", idByNorText=False)
    os.chdir(cwd)
