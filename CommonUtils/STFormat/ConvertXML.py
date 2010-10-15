from STTools import *
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

def toInteractionXML(documents, corpusName="GENIA", output=None):
    corpusRoot = ET.Element("corpus")
    corpusRoot.set("source", "GENIA")
    docCounter = 0
    for doc in documents:
        docEl = ET.Element("document")
        docId = corpusName + ".d" + str(docCounter)
        docEl.set("id", docId)
        docCounter += 1
        docEl.set("pmid", str(doc.id))
        docEl.set("text", doc.text)
        corpusRoot.append(docEl)
        # Write triggers and entities
        elCounter = 0
        tMap = {}
        for protein in doc.proteins + doc.triggers:
            entEl = ET.Element("entity")
            protId = docId + ".e" + str(elCounter)
            entEl.set("id", protId)
            entEl.set("origId", str(doc.id) + "." + str(protein.id))
            entEl.set("text", protein.text)
            entEl.set("charOffset", str(protein.charBegin) + "-" + str(protein.charEnd))
            entEl.set("type", protein.type)
            if protein.type == "Protein":
                entEl.set("isName", "True")
            elCounter += 1
            docEl.append(entEl)
            assert not tMap.has_key(protId)
            tMap[protein.id] = protId
        # Pre-define XML interaction ids
        elCounter = 0
        # Write events
        for event in doc.events:
            argCount = 0
            for arg in event.arguments:
                intEl = ET.Element("interaction")
                intEl.set("directed", "True")
                intEl.set("id", docId + ".i" + str(elCounter))
                elCounter += 1
                intEl.set("origId", str(doc.id) + "." + str(event.id) + "." + str(argCount))
                intEl.set("e1", tMap[event.trigger.id])
                if arg[1].trigger != None:
                    intEl.set("e2", tMap[arg[1].trigger.id])
                else:
                    intEl.set("e2", tMap[arg[1].id])
                intEl.set("type", arg[0])
                docEl.append(intEl)
                argCount += 1
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return ET.ElementTree(corpusRoot)
                
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    #proteins, triggers, events = load(1335418, "/home/jari/biotext/tools/TurkuEventExtractionSystem-1.0/data/evaluation-data/evaluation-tools-devel-gold")
    #write(1335418, "/home/jari/data/temp", proteins, triggers, events )
    
    p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
    print "Loading documents"
    documents = loadSet(p)
    print "Writing XML"
    toInteractionXML(documents, "GENIA", "/home/jari/data/temp/new-devel.xml")