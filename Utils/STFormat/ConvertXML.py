import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
from STTools import *
import xml.etree.cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range

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
    entEl.set("charOffset", str(ann.charBegin) + "-" + str(ann.charEnd))
    if len(ann.alternativeOffsets) > 0:
        altOffs = []
        for ao in protein.alternativeOffsets:
            altOffs.append( str(ao[0]) + "-" + str(ao[1]-1) ) 
        entEl.set("altOffset", ",".join(altOffs))
    # determine if given data
    assert ann.fileType in ["a1", "a2", "rel"], ann.fileType
    if ann.fileType == "a1": #protein.isName():
        entEl.set("isName", "True")
    else:
        entEl.set("isName", "False")
    return entEl

def makeDocumentElement(doc, idCount, corpusName):
    docEl = ET.Element("document")
    docId = corpusName + ".d" + str(idCount)
    docEl.set("id", docId)
    #docEl.set("pmid", str(doc.id))
    docEl.set("origId", str(doc.id))
    docEl.set("text", doc.text)
    if doc.dataSet != None:
        docEl.set("set", doc.dataSet)
    # If this is a sentence, make one
    isSentence = len(doc.words) > 0
    if isSentence:
        sentEl = ET.SubElement(docEl, "sentence")
        sentEl.set("id", docId + ".s0")
        sentEl.set("text", doc.text)
        sentEl.set("charOffset", "0-" + str(len(doc.text)))
        docId = sentEl.get("id") # hack to get all subelements here
        docEl = sentEl # hack to get all subelements here
    return docEl

def addParseElements(doc, docEl):
    if docEl.tag != "sentence":
        return
    sentAnalysesEl = ET.SubElement(sentEl, "analyses")
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

def makeInteractionElement(intType, docId, idCount, origId, e1Id, e2Id, isRelation=False):
    intEl = ET.Element("interaction")
    intEl.set("directed", "True")
    intEl.set("id", docId + ".i" + str(idCount))
    intEl.set("origId", origId)
    intEl.set("e1", e1Id)
    intEl.set("e2", e2Id)
    intEl.set("type", intType)
    if isRelation:
        intEl.set("relation", "True")
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
        for event in doc.events:
            if event.trigger == None: # triggerless event (simple pairwise interaction) == relation
                assert len(event.arguments) >= 2, (event.id, event.type, event.arguments)
                a1 = event.arguments[0]
                a2 = event.arguments[1]
                origId = str(doc.id) + "." + str(event.id)
                relEl = makeInteractionElement(event.type, docId, elCounter, origId, tMap[a1[1].id], tMap[a2[1].id], True)
                if (a1[0] != "Arg1"):
                    relEl.set("e1Role", a1[0])
                if (a2[0] != "Arg2"):
                    relEl.set("e2Role", a2[0])
                elCounter += 1
                docEl.append(intEl)
                if len(event.arguments) > 2:
                    assert event.type == "Coref", (event.id, docId, event.type)
                    for connProt in event.arguments[2:]: # link proteins to antecedent
                        docEl.append(makeInteractionElement("CorefTarget", docId, elCounter, origId, tMap[a2[1].id], tMap[connProt[1].id]), True)
            else:
                argCount = 0
                for arg in event.arguments:
                    origId = str(doc.id) + "." + str(event.id) + "." + str(argCount)
                    argEl = makeInteractionElement(arg[0], docId, elCounter, origId, tMap[event.id], tMap[arg[1].id])
                    elCounter += 1
                    argCount += 1
                    docEl.append(argEl)
                    # Add site
                    if arg[2] != None:
                        #assert arg[2].type == "Entity"
                        #assert arg[1].type in ["Protein", "Gene", "Chemical", "Organism", "Regulon-operon", "Two-component-system"], (arg[1].type, doc.id, doc.dataSet, event.id)
                        origId = str(doc.id) + "." + str(event.id) + "." + str(argCount) + ".site"
                        # The site-argument connects the event to the site entity, just like in the shared task
                        siteEl = makeInteractionElement("Site", docId, elCounter, origId, tMap[event.id], tMap[arg[2].id])
                        elCounter += 1
                        docEl.append(siteEl)
                        # The SiteParent argument connects the entity to it's protein. As sites must be paired with
                        # core arguments, the SiteParent can be used to find the protein argument corresponding to
                        # the entity. Site and core arguments can be paired by the shared protein which is both the
                        # immediate target of the core argument, and the Site's target via the SiteParent argument.
                        siteEl = makeInteractionElement("SiteParent", docId, elCounter, origId, tMap[arg[2].id], tMap[arg[1].id])
                        elCounter += 1
                        docEl.append(siteEl)
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
        if len(triggerToEvents[triggerId]) == 0:
            triggerToEvents[triggerId].append(trigger.id)
    return triggerToEvents
            
def toInteractionXML(documents, corpusName="CORPUS", output=None):
    corpusRoot = ET.Element("corpus")
    corpusRoot.set("source", corpusName)
    docCounter = 0
    for doc in documents:
        docEl = makeDocumentElement(doc, docCounter, corpusName)
        corpusRoot.append(docEl)
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
        if trigger.charBegin == ann.charBegin and trigger.charEnd == ann.charEnd and \
           trigger.text == ann.text and trigger.type == ann.type:
            found = True
            return trigger
    return None

def addTextToSTDoc(doc, docElement):
    #sentenceOffsets = {}
    for sentence in document.findall("sentence"):
        head = sentence.get("head")
        if head != None:
            stDoc.text += head
        stDoc.text += sentence.get("text")
        tail = sentence.get("tail")
        if tail != None:
            stDoc.text += tail
        #sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
        #sentenceOffsets[sentence.get("id")] = sentenceOffset
        if stDoc.id == None:
            stDoc.id = sentence.get("origId").rsplit(".", 1)[0]

def addEntitiesToSTDoc(doc, docElement, tMap, eMap, entityElementMap, useOrigIds=False):
    containerElements = [docElement] + [x for x in docElement.getiterator("sentence")]
    for containerElement in containerElements:
        for entity in containerElement.findall("entity"):
            eType = entity.get("type")
            if eType == "neg": # skip negative predictions if they are present
                continue
            assert entity.get("id") != None
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
            assert entityOffset[1] - entityOffset[0] in [len(ann.text), len(ann.text) - 1], (ann.text, entityOffset)
            ann.charBegin = entityOffset[0]
            ann.charEnd = entityOffset[0] + len(ann.text) # entityOffset[1] + 1
            if containerElement.tag == "sentence": # entity offset is relative to the container element, and for sentences, they can be relative to the document
                sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
                ann.charBegin += sentenceOffset[0]
                ann.charEnd += sentenceOffset[0]
#            idStem = entity.get("id").split(".e", 1)[0]
#            if sentenceOffsets.has_key(idStem):
#                sentenceOffset = sentenceOffsets[idStem]
#                ann.charBegin += sentenceOffset[0]
#                ann.charEnd += sentenceOffset[0]
            if entity.get("speculation") == "True":
                ann.speculation = True
            if entity.get("negation") == "True":
                ann.negation = True
            if entity.get("isName") == "True":
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
            else:
                duplicateAnn = findDuplicateForSTTrigger(ann, doc.triggers)
                if duplicateAnn == None:
                    doc.triggers.append(ann)
                    tMap[entity.get("id")] = ann
                    # Add confidence scores
                    ann.triggerScores = entity.get("predictions")
                    ann.unmergingScores = entity.get("umStrength")
                    ann.speculationScores = entity.get("modPred")
                    ann.negationScores = entity.get("modPred")
                    # Process events with 0 interactions would not be formed when constructing events based on interactions
                    if entity.get("type") == "Process": # Process-type events can have 0 interactions
                        event = makeSTEvent(ann, entityElementMap[entity.get("id")])
                        eMap[entity.get("id")] = event
                        doc.events.append(event)
                else: # a duplicate trigger already exists
                    tMap[entity.get("id")] = duplicateAnn

def makeSTEvent(triggerAnn, triggerElement):
    event = Annotation()
    event.trigger = triggerAnn
    event.type = triggerAnn.type
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
            if not tMap.has_key(e2):
                print >> sys.stderr, "Warning, no trigger for Coref Protein Target"
                continue
            e2 = tMap[e2]
            if not corefProtMap.has_key(e1):
                corefProtMap[e1] = []
            if not e2 in corefProtMap[e1]: 
                corefProtMap[e1].append(e2)
    return corefProtMap

def addInteractionsToSTDoc(doc, docElement, tMap, eMap, entityElementMap):
    # First map Coref proteins
    corefProtMap = getCorefTargetMap(docElement)
    # Then process all interactions
    siteMap = {}
    siteScores = {}
    for interaction in docElement.getiterator("interaction"):
        intType = interaction.get("type")
        if intType == "neg" or intType == "CorefTarget":
            continue # Targets have already been put into a dictionary
        if interaction.get("relation") == "True": # "/" in intType and "(" in intType: # BI-task
            rel = Annotation()
            rel.type = interaction.get("type")
            e1 = interaction.get("e1")
            e2 = interaction.get("e2")
            e1Role = interaction.get("e1Role", "Arg1")
            e2Role = interaction.get("e2Role", "Arg2")          
            relScores = interaction.get("predictions")
            rel.arguments.append([e1Role, tMap[e1], None, relScores])
            rel.arguments.append([e2Role, tMap[e2], None, relScores])
            if rel.type == "Coref":
                # Add protein arguments
                if corefProtMap.has_key(e2):
                    for prot in corefProtMap[e2]:
                        rel.arguments.append(["CorefTarget", prot, None])
            stDoc.events.append(event)
        else:
            if intType == "SiteParent":
                # These sites are real sites (i.e. task 2 sites). Other sites are just arguments called "site"
                siteMap[interaction.get("e2")] = tMap[interaction.get("e1")]
                siteScores[interaction.get("e2")] = interaction.get("predictions")
            else:
                e1 = interaction.get("e1")
                if e1 not in eMap: # event has not yet been created
                    eMap[e1] = makeSTEvent(tMap[e1], entityElementMap[e1])
                    doc.events.append(eMap[e1])
                # add arguments
                eMap[e1].arguments.append([interaction.get("type"), interaction.get("e2"), None, interaction.get("predictions")])
#    # Rename site-type interactions (which have been masked as "SiteArg" to prevent them being processed as Shared Task task-2 sites
#    for event in doc.events:
#        for arg in event.arguments:
#            if arg[0] == "SiteArg":
#                arg[0] = "Site"
#                if arg[3] != None: # Convert also prediction strengths
#                    arg[3] = arg[3].replace("SiteArg", "Site")
    # replace argument target ids with actual target objects
    mapSTArgumentTargets(doc, siteMap, siteScores, tMap, eMap)

def mapSTArgumentTargets(stDoc, siteMap, siteScores, tMap, eMap):
    # Map argument targets
    for event in stDoc.events:
        for arg in event.arguments[:]:
            assert arg[1] != None
            id = arg[1]
            if eMap.has_key(id):
                arg[1] = eMap[id]
            elif tMap.has_key(id):
                arg[1] = tMap[id]
            # add sites
            if siteMap.has_key(id):
                assert id not in eMap
                assert id in tMap
                arg[2] = siteMap[id]
                if id in siteScores and siteScores[id] != None:
                    while len(arg) < 5:
                        arg += [None]
                    assert arg[4] == None
                    arg[4] = siteScores[id]
    
    # An interaction with type "Site" is the task 2 argument. An interaction with type "SiteParent" links the target
    # of the "Site"-argument to the protein that is the target of the core argument, allowing the site to be connected
    # to its core argument. 
    for siteArg in event.arguments:   
        if siteArg.type == "Site":
            siteParents = getSiteParents(arg.target)
            for mainArg in event.arguments:
                if mainArg.type != "Site" and mainArg.target in siteParents:
                    siteArg.siteOf = mainArg
                elif event.type != "SiteOf":
                    pass # remove site (because it's core argument cannot be determined)

def toSTFormat(input, output=None, outputTag="a2", useOrigIds=False, debug=False, task=2, validate=True, writeScores=False):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    nonEntitySiteCount = 0
    documents = []
    for document in corpusRoot.findall("document"):
        stDoc = Document()
        stDoc.id = document.get("pmid")
        if stDoc.id == None:
            stDoc.id = document.get("origId")
        stDoc.text = ""
        documents.append(stDoc)
        eMap = {}
        tMap = {}
        entityElementMap = {} # for task 3
        addEntitiesToSTDoc(stDoc, document, tMap, eMap, entityElementMap, useOrigIds)
        addInteractionsToSTDoc(stDoc, document, tMap, eMap, entityElementMap)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        writeSet(documents, output, resultFileTag=outputTag, debug=debug, task=task, validate=validate, writeScores=writeScores)
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
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-c", "--conversion", default="TO-ST", dest="conversion", help="")
    optparser.add_option("-t", "--outputTag", default="a2", dest="outputTag", help="a2 file extension.")
    optparser.add_option("-s", "--sentences", default=False, action="store_true", dest="sentences", help="Write each sentence to its own document")
    optparser.add_option("-r", "--origIds", default=False, action="store_true", dest="origIds", help="Use stored original ids (can cause problems with duplicates).")
    optparser.add_option("--stSitesAreArguments", default=False, action="store_true", dest="stSitesAreArguments", help="")
    optparser.add_option("-n", "--xmlCorpusName", default="CORPUS", dest="xmlCorpusName", help="")
    optparser.add_option("-a", "--task", default=2, type="int", dest="task", help="1 or 2")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="Verbose output.")
    (options, args) = optparser.parse_args()
    
    if options.conversion == "TO-ST":
        print >> sys.stderr, "Loading XML"
        xml = ETUtils.ETFromObj(options.input)
        print >> sys.stderr, "Converting to ST Format"
        toSTFormat(xml, options.output, options.outputTag, options.origIds, debug=options.debug, task=options.task)
    elif options.conversion == "TO-XML":
        import STTools
        print >> sys.stderr, "Loading ST format"
        documents = STTools.loadSet(options.input, "GE", level="a2", sitesAreArguments=options.stSitesAreArguments, a2Tag="a2", readScores=False)
        print >> sys.stderr, "Converting to XML"
        toInteractionXML(documents, options.xmlCorpusName, options.output)
    elif options.conversion == "ROUNDTRIP":
        import STTools
        print >> sys.stderr, "Loading ST format"
        documents = STTools.loadSet(options.input, "GE", level="a2", sitesAreArguments=options.stSitesAreArguments, a2Tag="a2", readScores=False)
        print >> sys.stderr, "Converting to XML"
        xml = toInteractionXML(documents)
        print >> sys.stderr, "Converting to ST Format"
        toSTFormat(xml, options.output, options.outputTag, options.origIds, debug=options.debug, task=options.task)
    else:
        print >> sys.stderr, "Unknown conversion option", options.conversion
        
