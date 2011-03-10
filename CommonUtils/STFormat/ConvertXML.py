import sys, os
from STTools import *
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import Range

#def compareArguments(a, b):
#    if a[0] == "Cause":
#        return 1
#    elif b[0] == "Cause":
#        return -1
#    return 0

def toInteractionXML(documents, corpusName="GENIA", output=None):
    corpusRoot = ET.Element("corpus")
    corpusRoot.set("source", corpusName)
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
        # If this is a sentence, make one
        isSentence = len(doc.words) > 0
        if isSentence:
            sentEl = ET.SubElement(docEl, "sentence")
            sentEl.set("id", docId + ".s0")
            sentEl.set("text", doc.text)
            sentEl.set("charOffset", "0-" + str(len(doc.text)-1))
            docId = sentEl.get("id") # hack to get all subelements here
            docEl = sentEl # hack to get all subelements here
        # Write triggers and entities
        elCounter = 0
        triggerToEvents = {}
        for trigger in doc.triggers:
            triggerId = trigger.id
            triggerToEvents[triggerId] = []
            for event in doc.events:
                if event.trigger == trigger:
                    triggerToEvents[triggerId].append(event.id)
            if len(triggerToEvents[triggerId]) == 0:
                triggerToEvents[triggerId].append(trigger.id)
        tMap = {}
        eventMap = {}
        for event in doc.events:
            eventMap[event.id] = event
        for protein in doc.proteins:
            entEl = ET.Element("entity")
            protId = docId + ".e" + str(elCounter)
            entEl.set("id", protId)
            entEl.set("origId", str(doc.id) + "." + str(protein.id))
            entEl.set("text", protein.text)
            entEl.set("charOffset", str(protein.charBegin) + "-" + str(protein.charEnd-1))
            if len(protein.alternativeOffsets) > 0:
                altOffs = []
                for ao in protein.alternativeOffsets:
                    altOffs.append( str(ao[0]) + "-" + str(ao[1]-1) ) 
                entEl.set("altOffset", ",".join(altOffs))
            entEl.set("type", protein.type)
            assert protein.fileType in ["a1", "a2"], protein.fileType
            if protein.fileType == "a1": #protein.isName():
                entEl.set("isName", "True")
            else:
                entEl.set("isName", "False")
            elCounter += 1
            docEl.append(entEl)
            assert not tMap.has_key(protId)
            tMap[protein.id] = protId        
        for protein in doc.triggers:
            for eventId in triggerToEvents[protein.id]: # Write duplicate triggers
                entEl = ET.Element("entity")
                protId = docId + ".e" + str(elCounter)
                entEl.set("id", protId)
                entEl.set("origId", str(doc.id) + "." + str(protein.id))
                entEl.set("text", protein.text)
                entEl.set("charOffset", str(protein.charBegin) + "-" + str(protein.charEnd-1))
                if len(protein.alternativeOffsets) > 0:
                    altOffs = []
                    for ao in protein.alternativeOffsets:
                        altOffs.append( str(ao[0]) + "-" + str(ao[1]-1) ) 
                    entEl.set("altOffset", ",".join(altOffs))
                entEl.set("type", protein.type)
                assert protein.fileType in ["a1", "a2"], protein.fileType
                if protein.fileType == "a1": #protein.isName():
                    entEl.set("isName", "True")
                else:
                    entEl.set("isName", "False")
                # Add negation and speculation
                if eventId in eventMap and eventMap[eventId].negation != None:
                    entEl.set("negation", "True")
                if eventId in eventMap and eventMap[eventId].speculation != None:
                    entEl.set("speculation", "True")
                elCounter += 1
                docEl.append(entEl)
                assert not tMap.has_key(protId)
                tMap[eventId] = protId
        # Pre-define XML interaction ids
        elCounter = 0
        # Write events
        for event in doc.events:
            if event.trigger == None: # triggerless event (simple pairwise interaction)
                assert len(event.arguments) >= 2, (event.id, event.type, event.arguments)
                a1 = event.arguments[0]
                a2 = event.arguments[1]
                intEl = ET.Element("interaction")
                intEl.set("directed", "True")
                intEl.set("id", docId + ".i" + str(elCounter))
                elCounter += 1
                intEl.set("origId", str(doc.id) + "." + str(event.id))
                intEl.set("e1", tMap[a1[1].id])
                intEl.set("e2", tMap[a2[1].id])
                #intEl.set("type", event.type)
                #intEl.set("argTypes", a1[0] + "/" + a2[0])
                intEl.set("type", event.type + "(" + a1[0] + "/" + a2[0] + ")")
                docEl.append(intEl)
            else:
                argCount = 0
                for arg in event.arguments:
                    intEl = ET.Element("interaction")
                    intEl.set("directed", "True")
                    intEl.set("id", docId + ".i" + str(elCounter))
                    elCounter += 1
                    intEl.set("origId", str(doc.id) + "." + str(event.id) + "." + str(argCount))
                    #intEl.set("e1", tMap[event.trigger.id])
                    intEl.set("e1", tMap[event.id])
                    if arg[1].trigger != None:
                        #intEl.set("e2", tMap[arg[1].trigger.id])
                        intEl.set("e2", tMap[arg[1].id])
                    else:
                        intEl.set("e2", tMap[arg[1].id])
                    intEl.set("type", arg[0])
                    docEl.append(intEl)
                    argCount += 1
                    # Add site
                    if arg[2] != None:
                        intEl = ET.Element("interaction")
                        intEl.set("directed", "True")
                        intEl.set("id", docId + ".i" + str(elCounter))
                        elCounter += 1
                        intEl.set("origId", str(doc.id) + "." + str(event.id) + "." + str(argCount) + ".site")
                        intEl.set("e1", tMap[arg[2].id]) # "Entity"-type entity is the source
                        assert arg[2].type == "Entity"
                        intEl.set("e2", tMap[arg[1].id]) # "Protein"-type entity is the target
                        assert arg[1].type in ["Protein", "Gene", "Chemical", "Organism", "Regulon-operon", "Two-component-system"], (arg[1].type, doc.id, doc.dataSet, event.id)
                        intEl.set("type", "Site")
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
            docEl.append(intEl)
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
                    intEl.set("type", "Target")
                    docEl.append(intEl)
            #docEl.append(intEl) # adding original intEl after extra argument loop broke everything
        if isSentence:
            sentAnalysesEl = ET.SubElement(sentEl, "sentenceanalyses")
            parsesEl = ET.SubElement(sentAnalysesEl, "parses")
            parseEl = ET.SubElement(parsesEl, "parse")
            tokenizationsEl = ET.SubElement(sentAnalysesEl, "tokenizations")
            tokenizationEl = ET.SubElement(tokenizationsEl, "tokenization")
            parseEl.set("parser", "gold")
            parseEl.set("tokenizer", "gold")
            tokenizationEl.set("tokenizer", "gold")
            tokenMap = {}
            for word in doc.words:
                tokEl = ET.SubElement(tokenizationEl, "token")
                tokEl.set("id", word.id)
                tokEl.set("text", word.text)
                tokEl.set("POS", "None")
                tokEl.set("charOffset", str(word.charBegin) + "-" + str(word.charEnd))
                tokenMap[word.id] = tokEl
            for dep in doc.dependencies:
                depEl = ET.SubElement(parseEl, "dependency")
                depEl.set("id", dep.id)
                depEl.set("type", dep.type)
                assert len(dep.arguments) == 2
                depEl.set("t1", dep.arguments[0][1].id)
                depEl.set("t2", dep.arguments[1][1].id)
                if dep.type.find(":") != -1:
                    word1Type, word2Type = dep.type.split("(")[0].split(":")[-1].split("-")
                    tokenMap[dep.arguments[0][1].id].set("POS", word1Type)
                    tokenMap[dep.arguments[1][1].id].set("POS", word2Type)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return ET.ElementTree(corpusRoot)

def toSTFormat(input, output=None, outputTag="a2", useOrigIds=False, debug=False, task=2):
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
        siteMap = {}
        sites = []
        sentenceOffsets = {}
        for sentence in document.findall("sentence"):
            stDoc.text += sentence.get("text")
            tail = sentence.get("tail")
            if tail != None:
                stDoc.text += tail
            sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            sentenceOffsets[sentence.get("id")] = sentenceOffset
            if stDoc.id == None:
                stDoc.id = sentence.get("origId").rsplit(".", 1)[0]
        entityElementMap = {} # for task 3
        for entity in document.getiterator("entity"):
            eType = entity.get("type")
            if eType == "neg":
                continue
            entityElementMap[entity.get("id")] = entity
            entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
            ann = Annotation()
            ann.type = eType
            if useOrigIds:
                entityOrigId = entity.get("origId")
                if entityOrigId != None and entityOrigId.find(".") != -1: # fix gluing of doc and ann id
                    entityOrigId = entityOrigId.rsplit(".",1)[-1]
                if entityOrigId != None:
                    if entityOrigId[0] == "E": # a special id denoting a numbered, but triggerless event
                        ann.eventId = entityOrigId
                        ann.id = None
                    else:
                        ann.id = entityOrigId
            ann.text = entity.get("text")
            ann.charBegin = entityOffset[0]
            ann.charEnd = entityOffset[1] + 1
            idStem = entity.get("id").split(".e", 1)[0]
            if sentenceOffsets.has_key(idStem):
                sentenceOffset = sentenceOffsets[idStem]
                ann.charBegin += sentenceOffset[0]
                ann.charEnd += sentenceOffset[0]
            if entity.get("speculation") == "True":
                ann.speculation = True
            if entity.get("negation") == "True":
                ann.negation = True
            if entity.get("isName") == "True":
                # Remember to use original id for names!
                ann.id = entity.get("origId").rsplit(".", 1)[-1]
                assert ann.id[0].isupper(), ann.id
                for c in ann.id[1:]:
                    assert c.isdigit(), ann.id
                stDoc.proteins.append(ann)
            else:
                found = False # prevent duplicate triggers
                for trigger in stDoc.triggers:
                    if trigger.charBegin == ann.charBegin and trigger.charEnd == ann.charEnd and \
                       trigger.text == ann.text and trigger.type == ann.type:
                        found = True
                        ann = trigger
                        break
                if not found:
                    stDoc.triggers.append(ann)
            assert entity.get("id") != None
            tMap[entity.get("id")] = ann
            if entity.get("type") == "Process": # these can have 0 interactions
                event = Annotation()
                event.trigger = ann
                event.type = event.trigger.type
                eMap[entity.get("id")] = event
                if entityElementMap[entity.get("id")].get("speculation") == "True":
                    event.speculation = True
                if entityElementMap[entity.get("id")].get("negation") == "True":
                    event.negation = True
                stDoc.events.append(event)
        # First map Coref proteins
        corefProtMap = {}
        for interaction in document.getiterator("interaction"):
            intType = interaction.get("type")
            if intType == "Target":
                e1 = interaction.get("e1")
                e2 = interaction.get("e2")
                if not tMap.has_key(e2):
                    print >> sys.stderr, "Warning, no trigger for Coref Protein Target"
                    continue
                e2 = tMap[e2]
                if not corefProtMap.has_key(e1):
                    corefProtMap[e1] = []
                if not e2 in corefProtMap[e1]: 
                    corefProtMap[e1].append(e2)
        # Then process all interactions
        for interaction in document.getiterator("interaction"):
            intType = interaction.get("type")
            if intType == "neg" or intType == "Target":
                continue # Targets have already been put into a dictionary
            #elif intType in ["Site", "Gene_expression", "Transcription", "Protein_catabolism", "Localization", "Binding", "Phosphorylation", "Positive_regulation", "Negative_regulation", "Regulation"]:
            #elif intType in ["Site", "Gene_expression", "Transcription", "Protein_catabolism", "Localization", "Binding", "Phosphorylation", "Positive_regulation", "Negative_regulation", "Regulation",
            #                 "InputAssociation", "InputProcess", "InputInhibitor", "OutputProcess"]:
            if "/" in intType and "(" in intType: # BI-task
                eventType, argTypes = intType.split("(")
                arg1Type, arg2Type = argTypes[:-1].split("/")
                event = Annotation()
                event.trigger = None # triggerless event (same as relation)
                event.type = eventType
                event.arguments.append([arg1Type, interaction.get("e1"), None])
                event.arguments.append([arg2Type, interaction.get("e2"), None])
                if event.arguments[0][0] == "SiteArg": # convert back to actual sites
                    event.arguments[0][0] = "Site"
                if event.arguments[1][0] == "SiteArg": # convert back to actual sites
                    event.arguments[1][0] = "Site"
                #event.speculation = entityElementMap[e1].get("speculation")
                #event.negation = entityElementMap[e1].get("negation")
                stDoc.events.append(event)
            elif intType not in ["Protein-Component", "Subunit-Complex", "Renaming", "Coref"]:
                #if intType == "Site" and tMap[interaction.get("e1")].type == "Entity":
                if intType == "Site":
                    # These sites are real sites (i.e. task 2 sites).
                    # Other sites are just arguments called "site"
                    #sites.append(interaction)
                    siteMap[interaction.get("e2")] = tMap[interaction.get("e1")]
                else:
                    e1 = interaction.get("e1")
                    if eMap.has_key(e1): # event has already been created
                        event = eMap[e1] # eMap lists events by their trigger ids
                    else:
                        eventType = tMap[interaction.get("e1")].type
                        if eventType != "Entity": # "Entity"-type entities are never event roots
                            event = Annotation()
                            event.trigger = tMap[interaction.get("e1")]
                            event.type = event.trigger.type
                            if hasattr(event.trigger, "eventId"):
                                event.id = event.trigger.eventId 
                            eMap[e1] = event
                            if entityElementMap[e1].get("speculation") == "True":
                                event.speculation = True
                            if  entityElementMap[e1].get("negation") == "True":
                                event.negation = True 
                            stDoc.events.append(event)
                        else:
                            event = None
                    if event != None:
                        arg = [interaction.get("type"), interaction.get("e2"), None]
                        if arg[0] == "SiteArg": # convert back to actual sites
                            arg[0] = "Site"
                        event.arguments.append(arg)
            else: # interaction is a relation
                rel = Annotation()
                rel.type = interaction.get("type")
                e1 = interaction.get("e1")
                e2 = interaction.get("e2")
                #assert rel.type == "Protein-Component" or rel.type == "Subunit-Complex" or rel.type == "Renaming", (rel.type, stDoc.id, interaction.get("id"))
                if rel.type == "Protein-Component" or rel.type == "Subunit-Complex": 
                    rel.arguments.append(["Arg1", tMap[e1], None])
                    rel.arguments.append(["Arg2", tMap[e2], None])
                elif rel.type == "Renaming":
                    rel.arguments.append(["Former", tMap[e1], None])
                    rel.arguments.append(["New", tMap[e2], None])
                elif rel.type == "Coref":
                    rel.arguments.append(["Anaphora", tMap[e1], None])
                    rel.arguments.append(["Antecedent", tMap[e2], None])
                    # Add protein arguments'
                    if corefProtMap.has_key(e2):
                        for prot in corefProtMap[e2]:
                            rel.arguments.append(["Target", prot, None])
                else:
                    assert False, (rel.type, stDoc.id, interaction.get("id"))
                stDoc.relations.append(rel)
        # Map argument targets
        for event in stDoc.events:
            for arg in event.arguments[:]:
                if arg[1] == None:
                    continue
                id = arg[1]
                if eMap.has_key(id):
                    arg[1] = eMap[id]
                elif tMap.has_key(id):
                    arg[1] = tMap[id]
                    # Remove Entity-type triggers if they are Regulation-arguments
                    if "egulation" in event.type and tMap[id].type != "Protein":
                        event.arguments.remove(arg)
                # add sites
                if siteMap.has_key(id):
                    assert id not in eMap
                    assert id in tMap
                    arg[2] = siteMap[id]
                    assert siteMap[id].type == "Entity", (stDoc.id, event.id, id, siteMap[id].id, siteMap[id].type)
#        # Remove eventless triggers
#        triggersToKeep = []
#        for trigger in stDoc.triggers:
#            if trigger.type == "Entity":
#                triggersToKeep.append(trigger)
#            else:
#                for event in stDoc.events:
#                    if event.trigger == trigger:
#                        triggersToKeep.append(trigger)
#                        break
#        stDoc.triggers = triggersToKeep
        # Sort arguments
        #for eKey in sorted(eMap.keys()):
        #    event = eMap[eKey]
        #    event.arguments.sort(cmp=compareArguments)
        # Create STFormat ids
        #updateIds(stDoc.proteins)
        #updateIds(stDoc.triggers, getMaxId(stDoc.proteins) + 1)
        #updateIds(stDoc.events)
        #updateIds(stDoc.relations)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        writeSet(documents, output, resultFileTag=outputTag, debug=debug, task=task)
    return documents

#def toSTFormatSentences(input, output=None, outputTag="a2"):
#    print >> sys.stderr, "Loading corpus", input
#    corpusTree = ETUtils.ETFromObj(input)
#    print >> sys.stderr, "Corpus file loaded"
#    corpusRoot = corpusTree.getroot()
#    
#    documents = []
#    for document in corpusRoot.findall("document"):
#        sentenceCount = 0
#        for sentence in document.findall("sentence"):
#            stDoc = Document()
#            stDoc.proteins = []
#            stDoc.triggers = []
#            stDoc.events = []
#            stDoc.relations = []
#            stDoc.id = document.get("origId") + ".s" + str(sentenceCount)
#            stDoc.text = sentence.get("text") #""
#            tail = sentence.get("tail")
#            if tail != None:
#                stDoc.text += tail
#            documents.append(stDoc)
#            eMap = {}
#            tMap = {}
#            sites = []
#            sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
##            sentenceOffsets = {}
##            for sentence in document.findall("sentence"):
##                stDoc.text += sentence.get("text")
##                tail = sentence.get("tail")
##                if tail != None:
##                    stDoc.text += tail
##                sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
##                sentenceOffsets[sentence.get("id")] = sentenceOffset
#            for entity in sentence.getiterator("entity"):
#                eType = entity.get("type")
#                if eType == "neg":
#                    continue
#                entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
#                ann = Annotation()
#                ann.type = eType
#                ann.text = entity.get("text")
#                ann.charBegin = entityOffset[0]
#                ann.charEnd = entityOffset[1] + 1
#                idStem = entity.get("id").rsplit(".", 1)[0]
#                if sentenceOffsets.has_key(idStem):
#                    #sentenceOffset = sentenceOffsets[idStem]
#                    ann.charBegin += sentenceOffset[0]
#                    ann.charEnd += sentenceOffset[0]
#                if entity.get("speculation") == "True":
#                    ann.speculation = True
#                if entity.get("negation") == "True":
#                    ann.negation = True
#                if entity.get("isName") == "True":
#                    stDoc.proteins.append(ann)
#                else:
#                    stDoc.triggers.append(ann)
#                tMap[entity.get("id")] = ann
#            # First map Coref proteins
#            corefProtMap = {}
#            for interaction in sentence.getiterator("interaction"):
#                intType = interaction.get("type")
#                if intType == "Target":
#                    e1 = interaction.get("e1")
#                    e2 = interaction.get("e2")
#                    if not tMap.has_key(e2):
#                        print >> sys.stderr, "Warning, no trigger for Coref Protein Target"
#                        continue
#                    e2 = tMap[e2]
#                    if not corefProtMap.has_key(e1):
#                        corefProtMap[e1] = []
#                    if not e2 in corefProtMap[e1]: 
#                        corefProtMap[e1].append(e2)
#            # Then process all interactions
#            for interaction in sentence.getiterator("interaction"):
#                intType = interaction.get("type")
#                if intType == "neg" or intType == "Target":
#                    continue # Targets have already been put into a dictionary
#                elif intType in ["Site", "Gene_expression", "Transcription", "Protein_catabolism", "Localization", "Binding", "Phosphorylation", "Positive_regulation", "Negative_regulation", "Regulation"]:
#                    if intType == "Site":
#                        sites.append(interaction)
#                    else:
#                        e1 = interaction.get("e1")
#                        if eMap.has_key(e1):
#                            event = eMap[e1]
#                        else:
#                            event = Annotation()
#                            event.trigger = tMap[interaction.get("e1")]
#                            eMap[e1] = event
#                            stDoc.events.append(event)
#                        arg = [interaction.get("type"), interaction.get("e2"), None]
#                        event.arguments.append(arg)
#                else: # interaction is a relation
#                    rel = Annotation()
#                    rel.type = interaction.get("type")
#                    e1 = interaction.get("e1")
#                    e2 = interaction.get("e2")
#                    #assert rel.type == "Protein-Component" or rel.type == "Subunit-Complex" or rel.type == "Renaming", (rel.type, stDoc.id, interaction.get("id"))
#                    if rel.type == "Protein-Component" or rel.type == "Subunit-Complex": 
#                        rel.arguments.append(["Arg1", tMap[e1], None])
#                        rel.arguments.append(["Arg2", tMap[e2], None])
#                    elif rel.type == "Renaming":
#                        rel.arguments.append(["Former", tMap[e1], None])
#                        rel.arguments.append(["New", tMap[e2], None])
#                    elif rel.type == "Coref":
#                        rel.arguments.append(["Anaphora", tMap[e1], None])
#                        rel.arguments.append(["Antecedent", tMap[e2], None])
#                        # Add protein arguments'
#                        if corefProtMap.has_key(e2):
#                            for prot in corefProtMap[e2]:
#                                rel.arguments.append(["Target", prot, None])
#                    else:
#                        assert False, (rel.type, stDoc.id, interaction.get("id"))
#                    stDoc.relations.append(rel)
#            # Map argument targets
#            for eKey in sorted(eMap.keys()):
#                event = eMap[eKey]
#                for arg in event.arguments:
#                    if tMap.has_key(arg[2]):
#                        arg[2] = tMap[arg2]
#                    else:
#                        arg[2] = eMap[arg2]
#            # Create STFormat ids
#            updateIds(stDoc.proteins)
#            updateIds(stDoc.triggers, getMaxId(stDoc.proteins) + 1)
#            updateIds(stDoc.events)
#            updateIds(stDoc.relations)
#            sentenceCount += 1
#    
#    if output != None:
#        print >> sys.stderr, "Writing output to", output
#        writeSet(documents, output, resultFileTag=outputTag)
#    return documents

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

    optparser = OptionParser(usage="%prog [options]\nRecalculate head token offsets.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--outputTag", default="a2", dest="outputTag", help="a2 file extension.")
    optparser.add_option("-s", "--sentences", default=False, action="store_true", dest="sentences", help="Write each sentence to its own document")
    optparser.add_option("-r", "--origIds", default=False, action="store_true", dest="origIds", help="Use stored original ids (can cause problems with duplicates).")
    optparser.add_option("-a", "--task", default=2, type="int", dest="task", help="1 or 2")
    (options, args) = optparser.parse_args()
    
    if options.input[-4:] == ".xml":
        print >> sys.stderr, "Loading XML"
        xml = ETUtils.ETFromObj(options.input)
        if options.sentences:
            print >> sys.stderr, "Converting to ST Format (sentences)"
            toSTFormatSentences(xml, options.output, options.outputTag, options.origIds)
        else:
            print >> sys.stderr, "Converting to ST Format"
            toSTFormat(xml, options.output, options.outputTag, options.origIds, debug=True, task=options.task)

                
#if __name__=="__main__":
#    # Import Psyco if available
#    try:
#        import psyco
#        psyco.full()
#        print >> sys.stderr, "Found Psyco, using"
#    except ImportError:
#        print >> sys.stderr, "Psyco not installed"
#    
#    #proteins, triggers, events = load(1335418, "/home/jari/biotext/tools/TurkuEventExtractionSystem-1.0/data/evaluation-data/evaluation-tools-devel-gold")
#    #write(1335418, "/home/jari/data/temp", proteins, triggers, events )
#    
#    #p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
#    p = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_development_data"
#    print "Loading documents"
#    documents = loadSet(p)
#    print "Writing XML"
#    xml = toInteractionXML(documents, "GENIA", "/home/jari/data/temp/new-devel.xml")
#    print "Converting back"
#    toSTFormat(xml, "/home/jari/data/temp/new-devel-stformat")