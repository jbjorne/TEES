import sys, os, types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
from STTools import *
import xml.etree.cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
from collections import defaultdict

def makeEntityElement(ann, idCount, docEl):
    entEl = ET.Element("entity")
    entEl.set("type", ann.type)
    entEl.set("text", ann.text)
    # identifiers
    protId = docEl.get("id") + ".e" + str(idCount)
    entEl.set("id", protId)
    if ann.id != None:
        entEl.set("origId", docEl.get("origId") + "." + str(ann.id))
    # offsets
    entEl.set("charOffset", Range.tuplesToCharOffset(ann.charOffsets))
    if len(ann.alternativeOffsets) > 0:
        altOffs = []
        for alternativeOffset in ann.alternativeOffsets:
            altOffs.append( str(alternativeOffset[0]) + "-" + str(alternativeOffset[1]-1) ) 
        entEl.set("altOffset", ",".join(altOffs))
    if ann.normalization != None:
        entEl.set("normalization", ann.normalization)
    addExtraToElement(entEl, ann.extra)
    # determine if given data
    assert ann.fileType in ["a1", "a2", "rel"], ann.fileType
    if ann.fileType == "a1": #protein.isName():
        entEl.set("given", "True")
    #else:
    #    entEl.set("given", "False")
    return entEl

def addDocumentElement(doc, corpusEl, idCount, corpusName):
    docEl = ET.SubElement(corpusEl, "document")
    docId = corpusName + ".d" + str(idCount)
    docEl.set("id", docId)
    #docEl.set("pmid", str(doc.id))
    docEl.set("origId", str(doc.origId))
    docEl.set("text", doc.text)
    if doc.dataSet != None:
        docEl.set("set", doc.dataSet)
    # If this is a sentence, make one
    isSentence = len(doc.words) > 0
    if isSentence:
        sentEl = ET.SubElement(docEl, "sentence")
        sentEl.set("id", docId + ".s0")
        sentEl.set("origId", str(doc.id))
        sentEl.set("text", doc.text)
        sentEl.set("charOffset", "0-" + str(len(doc.text)))
        #docId = sentEl.get("id") # hack to get all subelements here
        docEl = sentEl # hack to get all subelements here
    return docEl

def addParseElements(doc, docEl):
    if docEl.tag != "sentence":
        return
    sentAnalysesEl = ET.SubElement(docEl, "analyses")
    #parsesEl = ET.SubElement(sentAnalysesEl, "parses")
    parseEl = ET.SubElement(sentAnalysesEl, "parse")
    #tokenizationsEl = ET.SubElement(sentAnalysesEl, "tokenizations")
    tokenizationEl = ET.SubElement(sentAnalysesEl, "tokenization")
    parseEl.set("parser", "gold")
    parseEl.set("tokenizer", "gold")
    tokenizationEl.set("tokenizer", "gold")
    tokenMap = {}
    for word in doc.words:
        tokEl = ET.SubElement(tokenizationEl, "token")
        tokEl.set("id", word.id)
        tokEl.set("text", word.text)
        tokEl.set("POS", "None")
        assert len(word.charOffsets) == 1, (word, word.charOffsets)
        tokEl.set("charOffset", Range.tuplesToCharOffset(word.charOffsets))
        tokenMap[word.id] = tokEl
    for dep in doc.dependencies:
        depEl = ET.SubElement(parseEl, "dependency")
        depEl.set("id", dep.id)
        depEl.set("type", dep.type)
        assert len(dep.arguments) == 2
        depEl.set("t1", dep.arguments[0].target.id)
        depEl.set("t2", dep.arguments[1].target.id)
        if dep.type.find(":") != -1:
            word1Type, word2Type = dep.type.split("(")[0].split(":")[-1].split("-")
            tokenMap[dep.arguments[0].target.id].set("POS", word1Type)
            tokenMap[dep.arguments[1].target.id].set("POS", word2Type)

def makeInteractionElement(intType, docId, idCount, origId, e1Id, e2Id, isEventArgument=False, annSource=None):
    intEl = ET.Element("interaction")
    intEl.set("directed", "True")
    intEl.set("id", docId + ".i" + str(idCount))
    intEl.set("origId", origId)
    intEl.set("e1", e1Id)
    intEl.set("e2", e2Id)
    intEl.set("type", intType)
    if isEventArgument:
        intEl.set("event", "True")
    if annSource != None and annSource == "a1": #protein.isName():
        intEl.set("given", "True")
    return intEl

def addEntityElements(doc, docEl, tMap, eventMap):
    elCounter = 0
    for protein in doc.proteins: # entities
        entEl = makeEntityElement(protein, elCounter, docEl) 
        elCounter += 1
        docEl.append(entEl)
        assert not tMap.has_key(entEl.get("id")), entEl.get("id")
        tMap[protein.id] = entEl.get("id")
    triggerToEvents = getTriggerToEventsMap(doc)
    for protein in doc.triggers: # triggers
        for eventId in triggerToEvents[protein.id]: # Write duplicate triggers
            entEl = makeEntityElement(protein, elCounter, docEl)
            if eventId in eventMap and eventMap[eventId].trigger != None:
                entEl.set("event", "True")
            # Add negation and speculation
            if eventId in eventMap and eventMap[eventId].negation != None:
                entEl.set("negation", "True")
            if eventId in eventMap and eventMap[eventId].speculation != None:
                entEl.set("speculation", "True")
            elCounter += 1
            docEl.append(entEl)
            assert not tMap.has_key(entEl.get("id")), entEl.get("id")
            tMap[eventId] = entEl.get("id")

def addInteractionElements(doc, docEl, tMap):
        elCounter = 0
        docId = docEl.get("id")
        # Write events and relations
        siteParentLinks = set()
        for event in doc.events:
            if event.trigger == None: # triggerless event (simple pairwise interaction) == relation
                origId = str(doc.id) + "." + str(event.id)
                if event.type != "Coref": 
                    assert len(event.arguments) >= 2, (event.id, event.type, event.arguments)
                    a1 = event.arguments[0]
                    a2 = event.arguments[1]
                    #assert a1.target.id in tMap, (a1.target.id, event, docId, docEl.get("origId"))
                    #assert a2.target.id in tMap, (a2.target.id, event, docId, docEl.get("origId"))
                    if a1.target.id not in tMap:
                        print >> sys.stderr, "Warning, skipping relation", event.id, "with no T-type target for argument", event.argumentToString(a1), "in document", docId + "/" + docEl.get("origId")
                    elif a2.target.id not in tMap:
                        print >> sys.stderr, "Warning, skipping relation", event.id, "with no T-type target for argument", event.argumentToString(a2), "in document", docId + "/" + docEl.get("origId")
                    else:
                        relEl = makeInteractionElement(event.type, docId, elCounter, origId, tMap[a1.target.id], tMap[a2.target.id], annSource=event.fileType)
                        if (a1.type + a1.siteIdentifier != "Arg1"):
                            relEl.set("e1Role", a1.type)
                        if (a2.type + a2.siteIdentifier != "Arg2"):
                            relEl.set("e2Role", a2.type)
                        if relEl.get("id").startswith("SDB16."):
                            relEl.set("type", relEl.get("type") + "(" + str(relEl.get("e1Role")) + "/" + str(relEl.get("e2Role")) + ")")
                        elCounter += 1
                        docEl.append(relEl)
                else: # BioNLP'11 Coref
                    assert event.type == "Coref", (event.id, docId, event.type)
                    argByType = defaultdict(list)
                    for arg in event.arguments:
                        argByType[arg.type].append(arg)
                    assert len(argByType) > 1, event
                    assert len(argByType["Anaphora"]) == 1, event
                    anaphoraArg = argByType["Anaphora"][0]
                    for antecedentArg in argByType["Antecedent"]:
                        corefEl = makeInteractionElement("Coref", docId, elCounter, origId, tMap[anaphoraArg.target.id], tMap[antecedentArg.target.id], annSource=event.fileType)
                        corefEl.set("e1Role", "Anaphora")
                        corefEl.set("e2Role", "Antecedent")
                        elCounter += 1
                        docEl.append(corefEl)
                        for connProtArg in argByType["CorefTarget"]: # link proteins to antecedent
                            docEl.append(makeInteractionElement("CorefTarget", docId, elCounter, origId, tMap[antecedentArg.target.id], tMap[connProtArg.target.id], annSource=event.fileType))
                            elCounter += 1
            else:
                argCount = 0
                elementIdByArg = {}
                for arg in event.arguments:
                    if arg.type != "Site":
                        origId = str(doc.id) + "." + str(event.id) + "." + str(argCount)
                        argEl = makeInteractionElement(arg.type, docId, elCounter, origId, tMap[event.id], tMap[arg.target.id], True, annSource=event.fileType)
                        elementIdByArg[arg] = argEl.get("id")
                        elCounter += 1
                        argCount += 1
                        docEl.append(argEl)
                for arg in event.arguments:
                    if arg.type == "Site":
                        #assert arg[2].type == "Entity"
                        #assert arg[1].type in ["Protein", "Gene", "Chemical", "Organism", "Regulon-operon", "Two-component-system"], (arg[1].type, doc.id, doc.dataSet, event.id)
                        origId = str(doc.id) + "." + str(event.id) + "." + str(argCount) + ".site"
                        # The site-argument connects the event to the site entity, just like in the shared task
                        siteEl = makeInteractionElement("Site", docId, elCounter, origId, tMap[event.id], tMap[arg.target.id], True, annSource=event.fileType)
                        if arg.siteOf != None:
                            siteEl.set("siteOf", elementIdByArg[arg.siteOf])
                        elCounter += 1
                        docEl.append(siteEl)
                        # The SiteParent argument connects the entity to it's protein. As sites must be paired with
                        # core arguments, the SiteParent can be used to find the protein argument corresponding to
                        # the entity. Site and core arguments can be paired by the shared protein which is both the
                        # immediate target of the core argument, and the Site's target via the SiteParent argument.
                        if arg.siteOf != None:
                            siteEntity = tMap[arg.target.id]
                            siteProtein = tMap[arg.siteOf.target.id]
                            siteIdentifier = (siteEntity, siteProtein)
                            if not siteIdentifier in siteParentLinks: # avoid duplicate SiteParent links
                                siteEl = makeInteractionElement("SiteParent", docId, elCounter, origId, siteEntity, siteProtein, annSource=event.fileType)
                                elCounter += 1
                                docEl.append(siteEl)
                                siteParentLinks.add(siteIdentifier)
                        #siteEl.set("parent", argEl.get("id"))
                        #intEl.set("e1", tMap[arg[2].id]) # "Entity"-type entity is the source
                        #intEl.set("e2", tMap[arg[1].id]) # "Protein"-type entity is the target

def getTriggerToEventsMap(doc):
    triggerToEvents = {}
    for trigger in doc.triggers:
        triggerId = trigger.id
        triggerToEvents[triggerId] = []
        for event in doc.events:
            if event.trigger == trigger:
                triggerToEvents[triggerId].append(event.id)
        if len(triggerToEvents[triggerId]) == 0: # T-elements with no event (such as Entities) are included in the list
            triggerToEvents[triggerId].append(trigger.id)
    return triggerToEvents
            
def toInteractionXML(documents, corpusName="CORPUS", output=None):
    corpusRoot = ET.Element("corpus")
    corpusRoot.set("source", corpusName)
    docCounter = 0
    for doc in documents:
        docEl = addDocumentElement(doc, corpusRoot, docCounter, corpusName)
        docCounter += 1
        # prepare mapping structures
        tMap = {}
        eventMap = {}
        for event in doc.events:
            eventMap[event.id] = event
        # write elements
        addEntityElements(doc, docEl, tMap, eventMap)
        addInteractionElements(doc, docEl, tMap)
        addParseElements(doc, docEl)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return ET.ElementTree(corpusRoot)

def findDuplicateForSTTrigger(ann, triggers):
    for trigger in triggers:
        if trigger.charOffsets == ann.charOffsets and trigger.text == ann.text and trigger.type == ann.type:
            return trigger
    return None

def addTextToSTDoc(doc, docElement):
    #sentenceOffsets = {}
    doc.text = ""
    sentenceElements = docElement.findall("sentence")
    if len(sentenceElements) == 0:
        doc.text = docElement.get("text")
    else:
        for sentence in sentenceElements:
            head = sentence.get("head")
            if head != None:
                doc.text += head
            doc.text += sentence.get("text")
            tail = sentence.get("tail")
            if tail != None:
                doc.text += tail
            #sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            #sentenceOffsets[sentence.get("id")] = sentenceOffset
            if doc.id == None:
                doc.id = sentence.get("origId").rsplit(".", 1)[0]

def addEntitiesToSTDoc(doc, docElement, tMap, eMap, entityElementMap, useOrigIds=False, skipModifiers=False):
    containerElements = [docElement] + [x for x in docElement.getiterator("sentence")]
    for containerElement in containerElements:
        for entity in containerElement.findall("entity"):
            eType = entity.get("type")
            if eType == "neg": # skip negative predictions if they are present
                continue
            assert entity.get("id") != None
            entityElementMap[entity.get("id")] = entity
            entityOffsets = Range.charOffsetToTuples(entity.get("charOffset"))
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
            if entity.get("normalization") != None:
                ann.normalization = entity.get("normalization")
            #assert entityOffset[1] - entityOffset[0] in [len(ann.text), len(ann.text) - 1], (ann.text, entityOffset)
            ann.charOffsets = entityOffsets
            #ann.charBegin = entityOffset[0]
            #ann.charEnd = entityOffset[0] + len(ann.text) # entityOffset[1] + 1
            if containerElement.tag == "sentence": # entity offset is relative to the container element, and for sentences, they can be relative to the document
                sentenceOffset = Range.charOffsetToSingleTuple(containerElement.get("charOffset"))
                for i in range(len(ann.charOffsets)):
                    ann.charOffsets[i] = (ann.charOffsets[i][0] + sentenceOffset[0], ann.charOffsets[i][1] + sentenceOffset[0]) 
                #ann.charBegin += sentenceOffset[0]
                #ann.charEnd += sentenceOffset[0]
#            idStem = entity.get("id").split(".e", 1)[0]
#            if sentenceOffsets.has_key(idStem):
#                sentenceOffset = sentenceOffsets[idStem]
#                ann.charBegin += sentenceOffset[0]
#                ann.charEnd += sentenceOffset[0]
            if not skipModifiers:
                if entity.get("speculation") == "True":
                    ann.speculation = True
                if entity.get("negation") == "True":
                    ann.negation = True
            ann.extra = getExtraFromElement(entity) # add all scores and extra data
            if entity.get("given") == "True":
                # Remember to use original id for names!
                if entity.get("origId") != None:
                    ann.id = entity.get("origId").rsplit(".", 1)[-1]
                    assert ann.id[0].isupper(), ann.id
                    for c in ann.id[1:]:
                        assert c.isdigit(), ann.id
                doc.proteins.append(ann)
                tMap[entity.get("id")] = ann
                # The part below is dangerous, and incompatibilities should be handled rather
                # by not converting to the shared task format when it cannot be done 
                #if entity.get("origId") != None:
                #    # Attempt to process origId, assuming it corresponds to the BioNLP Shared Task format
                #    nonNamedEntityOrigId = entity.get("origId").rsplit(".", 1)[-1]
                #    if len(nonNamedEntityOrigId) > 1 and nonNamedEntityOrigId[0].isupper() and nonNamedEntityOrigId[1:].isdigit():
                #        ann.id = nonNamedEntityOrigId
                #stDoc.proteins.append(ann)
            else: # a predicted protein or trigger
                duplicateAnn = findDuplicateForSTTrigger(ann, doc.triggers)
                if duplicateAnn == None:
                    doc.triggers.append(ann)
                    tMap[entity.get("id")] = ann
                    # Add confidence scores
                    #ann.extra = getExtraFromElement(entity, ["conf"])
                    #ann.triggerScores = entity.get("predictions")
                    #ann.unmergingScores = entity.get("umStrength")
                    #ann.speculationScores = entity.get("modPred")
                    #ann.negationScores = entity.get("modPred")
                    # Events with 0 interactions (such as some Process-type events) would not be formed when constructing events based on interactions
                    if entity.get("event") == "True":
                        event = makeSTEvent(ann, entityElementMap[entity.get("id")], skipModifiers=skipModifiers)
                        eMap[entity.get("id")] = event
                        doc.events.append(event)
                else: # a duplicate trigger already exists
                    tMap[entity.get("id")] = duplicateAnn

def makeSTEvent(triggerAnn, triggerElement, skipModifiers=False):
    """
    triggerAnn: A deduplicated st-format entity
    triggerElement: The original (possibly duplicate) interaction XML entity
    """
    event = Annotation()
    event.trigger = triggerAnn
    event.type = triggerAnn.type
    # Add event-specific extra data from the trigger element
    event.extra = getExtraFromElement(triggerElement, ["conf", "umConf", "modConf", "specConf", "negConf"])
    # Remove the event-specific extra data from the trigger annotation. Only the trigger confidence is left in the trigger
    triggerAnn.extra = {}
    if "conf" in event.extra:
        triggerAnn.extra["conf"] = event.extra["conf"]
        del event.extra["conf"]
    # Mark modifiers
    if not skipModifiers:
        if triggerElement.get("speculation") == "True":
            event.speculation = True
        if triggerElement.get("negation") == "True":
            event.negation = True
    if hasattr(event.trigger, "eventId"):
        event.id = event.trigger.eventId 
    return event

def getCorefTargetMap(docElement):
    corefProtMap = {}
    for interaction in docElement.getiterator("interaction"):
        intType = interaction.get("type")
        if intType == "CorefTarget":
            e1 = interaction.get("e1")
            e2 = interaction.get("e2")
#            if not tMap.has_key(e2):
#                print >> sys.stderr, "Warning, no trigger for Coref Protein Target"
#                continue
#            e2 = tMap[e2]
            if not corefProtMap.has_key(e1):
                corefProtMap[e1] = []
            if not e2 in corefProtMap[e1]: 
                corefProtMap[e1].append(e2)
    return corefProtMap

def getExtraFromElement(element, include=["conf", "umConf", "modConf", "specConf", "negConf"], extraTag="stx_"):
    extra = {}
    for key in element.attrib.keys():
        if key.startswith(extraTag) or key in include:
            extra[key.strip(extraTag)] = element.get(key)
    return extra

def addExtraToElement(element, extra, include=["conf", "umConf", "modConf", "specConf", "negConf"], extraTag="stx_"):
    if extra == None:
        return
    for key in extra.keys():
        if key in include:
            element.set(key, extra[key])
        else:
            element.set(extraTag + key, extra[key])

def addInteractionsToSTDoc(doc, docElement, tMap, eMap, entityElementMap, skipArgs=[], allAsRelations=False, skipModifiers=False):
    # First map Coref proteins
    corefProtMap = getCorefTargetMap(docElement)
    # Then process all interactions
    siteParents = defaultdict(set)
    siteOfTypes = defaultdict(set)
    for interaction in docElement.getiterator("interaction"):
        intType = interaction.get("type")
        if intType == "neg" or intType == "CorefTarget" or intType in skipArgs:
            continue # Targets have already been put into a dictionary
        if intType == "SiteParent" and not allAsRelations:
            siteParents[tMap[interaction.get("e1")]].add(tMap[interaction.get("e2")])
        elif interaction.get("event") != "True" or allAsRelations: # "/" in intType and "(" in intType: # BI-task
            rel = Annotation()
            rel.type = interaction.get("type")
            if interaction.get("id").startswith("SDB16."):
                rel.type = rel.type.split("(")[0]
            #relScores = getExtraFromElement(interaction) #interaction.get("conf")
            rel.extra = getExtraFromElement(interaction)
            rel.addArgument(interaction.get("e1Role", "Arg1"), interaction.get("e1")) #, None, relScores)
            rel.addArgument(interaction.get("e2Role", "Arg2"), interaction.get("e2")) #, None, relScores)
            if rel.type == "Coref":
                # Add protein arguments
                if interaction.get("e2") in corefProtMap:
                    for prot in corefProtMap[interaction.get("e2")]:
                        rel.addArgument("CorefTarget", prot)
            doc.events.append(rel)
        else:
            e1 = interaction.get("e1")
            if e1 not in eMap: # event has not yet been created
                eMap[e1] = makeSTEvent(tMap[e1], entityElementMap[e1], skipModifiers=skipModifiers)
                doc.events.append(eMap[e1])
            # add arguments
            arg = eMap[e1].addArgument(interaction.get("type"), interaction.get("e2"), None, getExtraFromElement(interaction))
            siteOfTypes[arg] = interaction.get("siteOfTypes")
            if siteOfTypes[arg] != None:
                siteOfTypes[arg] = set(siteOfTypes[arg].split(","))
#    # Rename site-type interactions (which have been masked as "SiteArg" to prevent them being processed as Shared Task task-2 sites
#    for event in doc.events:
#        for arg in event.arguments:
#            if arg[0] == "SiteArg":
#                arg[0] = "Site"
#                if arg[3] != None: # Convert also prediction strengths
#                    arg[3] = arg[3].replace("SiteArg", "Site")
    # replace argument target ids with actual target objects
    mapSTArgumentTargets(doc, siteParents, siteOfTypes, tMap, eMap)

def mapSTArgumentTargets(stDoc, siteParents, siteOfTypes, tMap, eMap):
    # Map argument targets
    for event in stDoc.events:
        #argTypeCounts = defaultdict(int)
        for arg in event.arguments:
            #argTypeCounts[arg.type] += 1
            assert type(arg.target) in types.StringTypes, arg.target
            targetId = arg.target # at this point, target is not yet an argument, but an interaction XML id
            if targetId in eMap:
                arg.target = eMap[targetId]
            elif targetId in tMap:
                arg.target = tMap[targetId]
            else:
                raise Exception("No object for argument target " + str(targetId))
    
        # An interaction with type "Site" is the task 2 argument. An interaction with type "SiteParent" links the target
        # of the "Site"-argument to the protein that is the target of the core argument, allowing the site to be connected
        # to its core argument.
        #argTypeCounts["Theme_and_Cause"] = argTypeCounts["Theme"] + argTypeCounts["Cause"]
        #if max(argTypeCounts.values()) > 1: # sites must be linked to core arguments
        # Note that Site-argument mapping applies only to events. E.g. the BI11 task has relations
        # which have an argument called "Site", but this is not a Site in the "GE task 2" sense.
        if not event.isRelation(): # map event sites
            argsToKeep = []
            argsWithSite = set() # prevent more than one site per argument
            for arg1 in event.arguments:
                if arg1.type == "Site":
                    # Pick valid potential primary arguments
                    validPrimaryArgTypes = siteOfTypes[arg1]
                    if validPrimaryArgTypes == None:
                        validPrimaryArgTypes = ("Theme", "Cause")
                    validPrimaryArgs = []
                    for arg2 in event.arguments:
                        if arg2.type in validPrimaryArgTypes:
                            validPrimaryArgs.append(arg2)
                    # Map site to a primary argument
                    if len(validPrimaryArgs) == 1: # only one valid primary argument, no siteParents are needed
                        arg2 = validPrimaryArgs[0]
                        if arg2 not in argsWithSite: # only if arg2 hasn't already got a site
                            argsWithSite.add(arg2)
                            arg1.siteOf = arg2
                            argsToKeep.append(arg1)
                    elif len(validPrimaryArgs) > 0: # multiple potential primary arguments
                        for arg2 in validPrimaryArgs:
                            # Keep site only if it's core argument can be determined unambiguously
                            if arg2 not in argsWithSite and arg1.target in siteParents and arg2.target in siteParents[arg1.target]:
                                argsWithSite.add(arg2)
                                arg1.siteOf = arg2
                                argsToKeep.append(arg1)
                                break # so that arg1 won't be duplicated when one site has (incorrectly) two parents
                else:
                    argsToKeep.append(arg1)
            event.arguments = argsToKeep            

def toSTFormat(input, output=None, outputTag="a2", useOrigIds=False, debug=False, skipArgs=[], validate=True, writeExtra=False, allAsRelations=False, files=None, exportIds=None, clear=True, skipModifiers=False):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    nonEntitySiteCount = 0
    documents = []
    for document in corpusRoot.findall("document"):
        stDoc = Document()
        stDoc.id = IXMLUtils.getExportId(document, exportIds)
        #stDoc.id = document.get("pmid")
        #if stDoc.id == None:
        #    stDoc.id = document.get("origId")
        addTextToSTDoc(stDoc, document)
        documents.append(stDoc)
        eMap = {}
        tMap = {}
        entityElementMap = {} # for task 3
        addEntitiesToSTDoc(stDoc, document, tMap, eMap, entityElementMap, useOrigIds, skipModifiers=skipModifiers)
        addInteractionsToSTDoc(stDoc, document, tMap, eMap, entityElementMap, skipArgs, allAsRelations, skipModifiers=skipModifiers)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        writeSet(documents, output, resultFileTag=outputTag, debug=debug, writeExtra=writeExtra, files=files, clear=clear)
    return documents

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

    optparser = OptionParser(description="Conversion between BioNLP ST format and Interaction XML")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in Interaction XML or BioNLP Shared Task format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in Interaction XML or BioNLP Shared Task format.")
    optparser.add_option("-c", "--conversion", default="TO-ST", dest="conversion", help="")
    optparser.add_option("-t", "--outputTag", default="a2", dest="outputTag", help="a2 file extension.")
    optparser.add_option("-u", "--inputTags", default="a2", dest="inputTags", help="a2 file extension.")
    optparser.add_option("-s", "--sentences", default=False, action="store_true", dest="sentences", help="Write each sentence to its own document")
    optparser.add_option("-r", "--origIds", default=False, action="store_true", dest="origIds", help="Use stored original ids (can cause problems with duplicates).")
    optparser.add_option("--stSitesAreArguments", default=False, action="store_true", dest="stSitesAreArguments", help="")
    optparser.add_option("-n", "--xmlCorpusName", default="CORPUS", dest="xmlCorpusName", help="")
    optparser.add_option("-a", "--task", default=2, type="int", dest="task", help="1 or 2")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="Verbose output.")
    optparser.add_option("-x", "--extra", default=False, action="store_true", dest="extra", help="Verbose output.")
    (options, args) = optparser.parse_args()
    
    options.inputTags = options.inputTags.split(",")
    
    if options.conversion in ("TO-ST", "TO-ST-RELATIONS"):
        print >> sys.stderr, "Loading XML"
        xml = ETUtils.ETFromObj(options.input)
        print >> sys.stderr, "Converting to ST Format"
        toSTFormat(xml, options.output, options.outputTag, options.origIds, debug=options.debug, allAsRelations=options.conversion=="TO-ST-RELATIONS", writeExtra=options.extra)
    elif options.conversion == "TO-XML":
        import STTools
        print >> sys.stderr, "Loading ST format"
        documents = STTools.loadSet(options.input, "GE", level="a2", sitesAreArguments=options.stSitesAreArguments, a2Tags=options.inputTags, readScores=False, debug=options.debug)
        print >> sys.stderr, "Converting to XML"
        toInteractionXML(documents, options.xmlCorpusName, options.output)
    elif options.conversion == "ROUNDTRIP":
        import STTools
        print >> sys.stderr, "Loading ST format"
        documents = STTools.loadSet(options.input, "GE", level="a2", sitesAreArguments=options.stSitesAreArguments, a2Tags=options.inputTags, readScores=False, debug=options.debug)
        print >> sys.stderr, "Converting to XML"
        xml = toInteractionXML(documents)
        print >> sys.stderr, "Converting to ST Format"
        toSTFormat(xml, options.output, options.outputTag, options.origIds, debug=options.debug, writeExtra=options.extra)
    else:
        print >> sys.stderr, "Unknown conversion option", options.conversion
        
