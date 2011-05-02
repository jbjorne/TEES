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

def readEventsFromSR(eventType, srDir, events):
    for dataSet in ["train", "test"]:
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
            norText = text.replace(" ", "")
            if norText not in events:
                events[norText] = []
            events[norText].append({"id":id, "text":text, "entity":entity, "namedEntity":namedEntity, "interaction":interaction, "dataSet":dataSet, "eventType":eventType})
        f.close()

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
            offset, entityText = event["entity"].split("\t")
            if offset not in usedOffsets:
                entity = ET.Element("entity")
                entity.set("charOffset", offset)
                entity.set("text", entityText)
                entity.set("type", "Entity")
                entity.set("isName", "False")
                entity.set("id", "e" + str(entityCount))
                entityCount += 1
                usedOffsets.add(offset)
                entitiesByOffset[offset] = entity
                xmlEvents[norText]["entities"].append(entity)
            else:
                entity = entitiesByOffset[offset]
            # Add named entity
            offset, entityText = event["entity"].split("\t")
            if offset not in usedOffsets:
                namedEntity = ET.Element("entity")
                namedEntity.set("charOffset", offset)
                namedEntity.set("text", entityText)
                namedEntity.set("type", "Entity")
                entity.set("isName", "True")
                namedEntity.set("id", "e" + str(entityCount))
                entityCount += 1
                usedOffsets.add(offset)
                entitiesByOffset[offset] = namedEntity
                xmlEvents[norText]["entities"].append(namedEntity)
            else:
                namedEntity = entitiesByOffset[offset]
            # Add interactions
            if event["interaction"] == "Yes":
                interaction = ET.Element("interaction")
                interaction.set("directed", "False")
                interaction.set("e1", entity.get("id"))
                interaction.set("e2", namedEntity.get("id"))
                interaction.set("id", "i" + str(interactionCount))
                xmlEvents[norText]["interactions"].append(interaction)
                interactionCount += 1
            else:
                assert event["interaction"] == "No", event["interaction"]
        dataSets[norText] = dataSet
    #return xmlEvents, dataSets

def insertEvents(xmlEvents, dataSets, srTexts, xml, corpusName):
    counts = collections.defaultdict(int)
    counts["SR-sentences"] = len(xmlEvents.keys())
    for document in xml.getiterator("document"):
        document.set("id", corpusName + "." + document.get("id").split(".", 1)[-1])
        for sentence in document.findall("sentence"):
            counts["sentences-total"] += 1
            sentNorText = sentence.get("text").replace(" ", "")
            sentText = sentence.get("text")
            if sentNorText not in xmlEvents:
                document.remove(sentence)
                counts["sentences-removed"] += 1
            else:
                alignment = alignStrings(srTexts[sentNorText], sentence.get("text"))
                if dataSets[sentNorText] == "test":
                    document.set("set", "devel")
                else:
                    assert dataSets[sentNorText] != "devel"
                    document.set("set", dataSets[sentNorText])
                counts["sentences-kept"] += 1
                sentenceId = corpusName + "." + sentence.get("id").split(".", 1)[-1]
                sentence.set("id", sentenceId)
                sentenceAnalysesElement = None
                for element in sentence.getchildren():
                    if element.tag in ["entity", "interaction"]:
                        sentence.remove(element)
                    elif element.tag == "sentenceanalyses":
                        sentence.remove(element)
                        sentenceAnalysesElement = element
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
                for interaction in xmlEvents[sentNorText]["interactions"]:
                    interaction.set("id", sentenceId + "." + interaction.get("id"))
                    interaction.set("e1", sentenceId + "." + interaction.get("e1"))
                    interaction.set("e2", sentenceId + "." + interaction.get("e2"))
                    sentence.append(entity)
                    counts["interactions-added"] += 1
                if sentenceAnalysesElement != None:
                    sentence.append(sentenceAnalysesElement)
    print "Finished inserting SR", counts
    
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

def convert(srFiles, xmlFileName, outdir, corpusName):
    print >> sys.stderr, "Loading Static Relations"
    events = {}
    for srFile in srFiles:
        readEventsFromSR(srFile[0], srFile[1], events)
    xmlEvents = {}
    dataSets = {}
    srTexts = {} # original, unnormalized sentence texts from the SR corpus
    eventsToXML(events, xmlEvents, dataSets, srTexts)
    
    print >> sys.stderr, "Loading XML"
    xml = ETUtils.ETFromObj(xmlFileName)
    print >> sys.stderr, "Inserting XML events"
    insertEvents(xmlEvents, dataSets, srTexts, xml, corpusName)
    ETUtils.write(xml, outdir+corpusName+"-srevents.xml")
    
    print >> sys.stderr, "Protein Name Splitting"
    splitTarget = "McClosky"
    ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
    print >> sys.stderr, "Head Detection"
    xml = FindHeads.findHeads(xml, "split-McClosky", tokenization=None, output=outdir+corpusName+"-split.xml", removeExisting=True)
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(xml, outDir, corpusName + "-", ".xml", [("devel", "train")])
    #if "devel" in [x[0] for x in datasets]:
    #    print >> sys.stderr, "Creating empty devel set"
    #    deletionRules = {"interaction":{},"entity":{"isName":"False"}}
    #    InteractionXML.DeleteElements.processCorpus(corpusName + "-devel.xml", corpusName + "-devel-empty.xml", deletionRules)
    return xml

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    relCorpusPath = "/home/jari/biotext/BioNLP2011/data/supporting-tasks/REL/rel-devel-and-train-and-test-stanford.xml"

    # non-embed
    outDir = "/usr/share/biotext/StaticRelations/data/nonembed/"
    datasets = [("memberof", "/home/jari/data/StaticRelations/sr_data/nonembed/GGP_memberof_Term"), 
                ("subunitof", "/home/jari/data/StaticRelations/sr_data/nonembed/GGP_subunitof_Term"), 
                ("partof", "/home/jari/data/StaticRelations/sr_data/nonembed/Term_partof_GGP")]
    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "sr-nonembed-conversion-log.txt")
    convert(datasets, relCorpusPath, outDir, "SRNE")
    os.chdir(cwd)
    
    # embed
    outDir = "/usr/share/biotext/StaticRelations/data/embed/"
    datasets = [("memberof", "/home/jari/data/StaticRelations/sr_data/embed/GGP_memberof_Term"), 
                ("subunitof", "/home/jari/data/StaticRelations/sr_data/embed/GGP_subunitof_Term"), 
                ("partof", "/home/jari/data/StaticRelations/sr_data/embed/Term_partof_GGP")]
    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "sr-embed-conversion-log.txt")
    convert(datasets, relCorpusPath, outDir, "SRE")
    os.chdir(cwd)
