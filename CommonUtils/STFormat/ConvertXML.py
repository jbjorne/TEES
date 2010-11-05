from STTools import *
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import Range

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
        if doc.dataSet != None:
            docEl.set("set", doc.dataSet)
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
            entEl.set("charOffset", str(protein.charBegin) + "-" + str(protein.charEnd-1))
            entEl.set("type", protein.type)
            if protein.type == "Protein":
                entEl.set("isName", "True")
            else:
                entEl.set("isName", "False")
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
        # Write relations
        for relation in doc.relations:
            assert len(relation.arguments) >= 2, (relation.id, relation.type, relation.arguments)
            a1 = relation.arguments[0]
            a2 = relation.arguments[1]
#            if a1[0] == "Arg2":
#                temp = a1
#                a1 = a2
#                a2 = temp
            assert a1[0] == "Arg1" or a1[0] == "Former" or a1[0] == "Anaphora", (a1, relation.arguments) 
            assert a2[0] == "Arg2" or a2[0] == "New" or a2[0] == "Antecedent", (a2, relation.arguments)
            intEl = ET.Element("interaction")
            intEl.set("directed", "True")
            intEl.set("id", docId + ".i" + str(elCounter))
            elCounter += 1
            intEl.set("origId", str(doc.id) + "." + str(relation.id))
            intEl.set("e1", tMap[a1[1].id])
            intEl.set("e2", tMap[a2[1].id])
            intEl.set("type", relation.type)
            if len(relation.arguments) > 2:
                assert relation.type == "Coref", (relation.id, docId, relation.type)
                for connProt in relation.arguments[2:]:
                    intEl = ET.Element("interaction")
                    intEl.set("directed", "True")
                    intEl.set("id", docId + ".i" + str(elCounter))
                    elCounter += 1
                    intEl.set("origId", str(doc.id) + "." + str(relation.id))
                    intEl.set("e1", tMap[a2[1].id]) # link proteins to antecedent
                    intEl.set("e2", tMap[connProt[1].id])
                    intEl.set("type", "CorefProt")
            docEl.append(intEl)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return ET.ElementTree(corpusRoot)

def toSTFormat(input, output=None):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    documents = []
    for document in corpusRoot.findall("document"):
        stDoc = Document()
        stDoc.proteins = []
        stDoc.triggers = []
        stDoc.events = []
        stDoc.relations = []
        stDoc.id = document.get("pmid")
        stDoc.text = ""
        documents.append(stDoc)
        eMap = {}
        tMap = {}
        sites = []
        sentenceOffsets = {}
        for sentence in document.findall("sentence"):
            stDoc.text += sentence.get("text")
            tail = sentence.get("tail")
            if tail != None:
                stDoc.text += tail
            sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            sentenceOffsets[sentence.get("id")] = sentenceOffset
        for entity in document.getiterator("entity"):
            entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
            ann = Annotation()
            ann.type = entity.get("type")
            ann.text = entity.get("text")
            ann.charBegin = entityOffset[0]
            ann.charEnd = entityOffset[1]
            idStem = entity.get("id").rsplit(".", 1)[0]
            if sentenceOffsets.has_key(idStem):
                sentenceOffset = sentenceOffsets[idStem]
                ann.charBegin += sentenceOffset[0]
                ann.charEnd += sentenceOffset[0] - 1
            if entity.get("speculation") == "True":
                ann.speculation = True
            if entity.get("negation") == "True":
                ann.negation = True
            if entity.get("isName"):
                stDoc.proteins.append(ann)
            else:
                stDoc.triggers.append(ann)
            tMap[entity.get("id")] = ann
        for interaction in document.getiterator("interaction"):
            intType = interaction.get("type")
            if intType in ["Site", "Gene_expression", "Transcription", "Protein_catabolism", "Localization", "Binding", "Phosphorylation", "Positive_regulation", "Negative_regulation", "Regulation"]:
                if intType == "Site":
                    sites.append(interaction)
                else:
                    e1 = interaction.get("e1")
                    if eMap.has_key(e1):
                        event = eMap[e1]
                    else:
                        event = Annotation()
                        event.trigger = tMap[interaction.get("e1")]
                        eMap[e1] = event
                        stDoc.events.append(event)
                    arg = [interaction.get("type"), interaction.get("e2"), None]
                    event.arguments.append(arg)
            else: # interaction is a relation
                rel = Annotation()
                rel.type = interaction.get("type")
                e1 = interaction.get("e1")
                e2 = interaction.get("e2")
                rel.arguments.append(["Arg1", tMap[e1], None])
                rel.arguments.append(["Arg2", tMap[e2], None])
                stDoc.relations.append(rel)
        # Map argument targets
        for eKey in sorted(eMap.keys()):
            event = eMap[eKey]
            for arg in event.arguments:
                if tMap.has_key(arg[2]):
                    arg[2] = tMap[arg2]
                else:
                    arg[2] = eMap[arg2]
        # Create STFormat ids
        updateIds(stDoc.proteins)
        updateIds(stDoc.triggers, getMaxId(stDoc.proteins) + 1)
        updateIds(stDoc.events)
        updateIds(stDoc.relations)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        writeSet(documents, output)
    return documents
                
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
    
    #p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
    p = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_development_data"
    print "Loading documents"
    documents = loadSet(p)
    print "Writing XML"
    xml = toInteractionXML(documents, "GENIA", "/home/jari/data/temp/new-devel.xml")
    print "Converting back"
    toSTFormat(xml, "/home/jari/data/temp/new-devel-stformat")