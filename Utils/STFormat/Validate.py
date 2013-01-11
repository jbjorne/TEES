from collections import defaultdict

def validateREL(documents):
    for document in documents:
        if len(document.events) > 0:
            print >> sys.stderr, "Warning, events for REL task"
        for relation in relations:
            assert len(relation.arguments) == 2
            pass

def compareEvents(e1, e2):
    if e1.type == e2.type and e1.trigger == e2.trigger and len(e1.arguments) == len(e2.arguments):
        for arg1, arg2 in zip(e1.arguments, e2.arguments):
            if arg1[0] != arg2[0] or arg1[1] != arg2[1] or arg1[2] != arg2[2]:
                return False
        return True
    else:
        return False

def removeDuplicates(events):
    firstLoop = True
    numRemoved = 0
    totalRemoved = 0
    # Since removed events cause nesting events' arguments to be remapped, 
    # some of these nesting events may in turn become duplicates. Loop until
    # all such duplicates are removed.
    while(numRemoved > 0 or firstLoop):
        firstLoop = False
        # Group duplicate events
        duplGroups = {}
        isDuplicate = {}
        for i in range(len(events)-1):
            e1 = events[i]
            duplGroups[e1] = [] # "same as e1"
            # Check all other events against e1
            for j in range(i+1, len(events)):
                e2 = events[j]
                if compareEvents(e1, e2):
                    if e2 not in isDuplicate: # else already added to a duplGroup
                        isDuplicate[e2] = True
                        duplGroups[e1].append(e2)
        # Mark events for keeping or removal
        replaceWith = {}
        toRemove = set()
        for mainEvent, duplGroup in duplGroups.iteritems():
            if len(duplGroup) == 0:
                continue
            # Mark for removal or preservation
            for event in duplGroup:
                assert event not in replaceWith
                replaceWith[event] = mainEvent
                toRemove.add(event)    
        # Remove events and remap arguments
        kept = []
        for event in events:
            if event not in toRemove:
                for arg in event.arguments:
                    if arg[1] in replaceWith:
                        assert arg[2] == None
                        arg[1] = replaceWith[arg[1]]
                kept.append(event)
        numRemoved = len(events) - len(kept)
        totalRemoved += numRemoved
        events = kept
    return events

def getBISuperType(eType):
    if eType in ["GeneProduct", "Protein", "ProteinFamily", "PolymeraseComplex"]:
        return "ProteinEntity"
    elif eType in ["Gene", "GeneFamily", "GeneComplex", "Regulon", "Site", "Promoter"]:
        return "GeneEntity"
    else:
        return None

def isIDCore(eType):
    return eType in ["Protein", "Regulon-operon", "Two-component-system", "Chemical", "Organism"]

def isIDTask(proteins):
    for protein in proteins:
        if protein.type in ["Regulon-operon", "Two-component-system", "Chemical"]:
            return True
    return False

# Enforce type-specific limits
def validate(events, simulation=False, verbose=False, docId=None): #, taskIsID=None):
    #assert taskIsID != None
    
    numRemoved = 0
    removeCounts = defaultdict(int)
    totalRemoved = 0
    if simulation:
        verbose = True
    docId = str(docId)
    # Since removed events cause nesting events' arguments to be remapped, 
    # some of these nesting events may in turn become duplicates. Loop until
    # all such duplicates are removed.
    firstLoop = True
    while(numRemoved > 0 or firstLoop):
        firstLoop = False
        toRemove = set()
        for event in events:
            # Check arguments
            for arg in event.arguments[:]:
                #if arg[1].type == "Entity":
                #    print "arg[1] == Entity"
                #    if not verbose:
                #        assert False, arg
                if arg[2] != None and arg[2].type != "Entity":
                    print "arg[2] != Entity:", arg[2].type
                    #if not verbose:
                    if verbose: print "VAL:", docId + "." + str(event.id), "Warning, non-entity type arg[2]"
                    assert False, arg
            # GE-regulation rules
            if "egulation" in event.type:
                typeCounts = {"Cause":0, "Theme":0}
                for arg in event.arguments[:]:
                    if arg[0] not in typeCounts or not (isIDCore(arg[1].type) or arg[1].trigger != None):
                        # if arg[1] has no trigger, this means that arg[1] is a trigger for
                        # which no event was predicted
                        event.arguments.remove(arg)
                        if verbose: print "VAL:", docId + "." + str(event.id), "Removed", event.type, "event argument of type", arg[0], arg
                    else:
                        typeCounts[arg[0]] += 1
                if typeCounts["Theme"] == 0:# and not taskIsID:
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), "(P/N/R)egulation with no themes"
                if len(event.arguments) == 0:
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), "(P/N/R)egulation with no arguments"
            elif event.type != "Catalysis": # The three regulations and catalysis are the only events that can have a cause
                for arg in event.arguments[:]:
                    if arg[0] == "Cause":
                        event.arguments.remove(arg)
                        if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with", arg[0], "arg of type", arg[1].type
            # Remove illegal arguments (GE=Only a protein can be a Theme for a non-regulation event)
            if event.type in ["Gene_expression", "Transcription"]:
                for arg in event.arguments[:]:
                    if arg[0] == "Theme" and arg[1].type not in ["Protein", "Regulon-operon"]:
                        event.arguments.remove(arg)
                        if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with", arg[0], "arg of type", arg[1].type
            if event.type in ["Protein_catabolism", "Phosphorylation"]:
                for arg in event.arguments[:]:
                    if arg[0] == "Theme" and arg[1].type not in ["Protein"]:
                        event.arguments.remove(arg)
                        if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with", arg[0], "arg of type", arg[1].type
            if event.type in ["Localization", "Binding"]:
                for arg in event.arguments[:]:
                    if arg[0] == "Theme" and arg[1].type not in ["Protein", "Regulon-operon", "Two-component-system", "Chemical", "Organism"]:
                        event.arguments.remove(arg)          
                        if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with", arg[0], "arg of type", arg[1].type
            # Check non-regulation events
            if event.type in ["Gene_expression", "Transcription", "Protein_catabolism", "Phosphorylation", "Localization", "Binding"]:
                themeCount = 0
                for arg in event.arguments:
                    if arg[0] == "Theme":
                        themeCount += 1
                if themeCount == 0:
                    if event.type == "Localization" and len(event.arguments) > 0: # Also used in BB
                        for arg in event.arguments:
                            if arg[0] in ["ToLoc", "AtLoc"]: # GE-task Localization
                                if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with no themes"
                                toRemove.add(event)
                                break
                    else:
                        toRemove.add(event)
                        if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with no themes"
                # Filter sites from GE events that can't have them (moved from STTools.writeEvents
                if event.type not in ["Binding", "Phosphorylation"]: # also ["Positive_regulation", "Negative_regulation", "Regulation"]
                    for arg in event.arguments:
                        if arg[2] != None:
                            if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with", arg[0], "arg of type", arg[1].type, "with a site."
                            removeCounts["site-removed-from-" + event.type] += 1
                            arg[2] = None
                            if len(arg) > 4:
                                arg[4] = None
            # check non-binding events
            if event.type != "Binding":
                themeCount = 0
                for arg in event.arguments:
                    if arg[0] == "Theme":
                        themeCount += 1
                if themeCount > 1:
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), "Non-binding event", event.type, "with", themeCount, "themes"
            if event.type == "Process":
                for arg in event.arguments[:]:
                    if arg[0] != "Participant":
                        event.arguments.remove(arg)
                        if verbose: print "VAL:", docId + "." + str(event.id), "Non-participant argument", arg[0], "for", event.type
                    elif not isIDCore(arg[1].type):
                        event.arguments.remove(arg)
                        if verbose: print "VAL:", docId + "." + str(event.id), arg[0], "argument with target", arg[1].type
            if event.type == "PartOf": # BB
                assert len(event.arguments) == 2
                # BB
                if event.arguments[0][1].type != "Host":
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with arg 1 of type", event.arguments[0][1].type
                if event.arguments[1][1].type != "HostPart":
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with arg 2 of type", event.arguments[1][1].type
            if event.type == "Localization": # BB and others
                for arg in event.arguments:
                    if arg[0] == "Bacterium" and arg[1].type != "Bacterium":
                        if verbose: print "VAL:", docId + "." + str(event.id), event.type, "with", arg[0], "arg of type", arg[1].type
                        toRemove.add(event)
            
            # BI-rules
            if len(event.arguments) == 2:
                arg1Type = event.arguments[0][1].type
                arg1SuperType = getBISuperType(arg1Type)
                arg2Type = event.arguments[1][1].type
                arg2SuperType = getBISuperType(arg2Type)
            if event.type == "RegulonDependence":
                if arg1Type != "Regulon": toRemove.add(event)
                if arg2SuperType not in ["GeneEntity", "ProteinEntity"]: toRemove.add(event)
            elif event.type == "BindTo":
                if arg1SuperType != "ProteinEntity": toRemove.add(event)
                if arg2Type not in ["Site", "Promoter", "Gene", "GeneComplex"]: toRemove.add(event)
            elif event.type == "TranscriptionFrom":
                if arg1Type not in ["Transcription", "Expression"]: toRemove.add(event)
                if arg2Type not in ["Site", "Promoter"]: toRemove.add(event)
            elif event.type == "RegulonMember":
                if arg1Type != "Regulon": toRemove.add(event)
                if arg2SuperType not in ["GeneEntity", "ProteinEntity"]: toRemove.add(event)
            elif event.type == "SiteOf":
                if arg1Type != "Site": toRemove.add(event)
                if not (arg2Type in ["Site", "Promoter"] or arg2SuperType == "GeneEntity"): toRemove.add(event)
            elif event.type == "TranscriptionBy":
                if arg1Type != "Transcription": toRemove.add(event)
                if arg2SuperType != "ProteinEntity": toRemove.add(event)
            elif event.type == "PromoterOf":
                if arg1Type != "Promoter": toRemove.add(event)
                if arg2SuperType not in ["ProteinEntity", "GeneEntity"]: toRemove.add(event)
            elif event.type == "PromoterDependence":
                if arg1Type != "Promoter": toRemove.add(event)
                if arg2SuperType not in ["ProteinEntity", "GeneEntity"]: toRemove.add(event)
            elif event.type == "ActionTarget":
                if arg1Type not in ["Action", "Expression", "Transcription"]: toRemove.add(event)
            elif event.type == "Interaction":
                if arg1SuperType not in ["ProteinEntity", "GeneEntity"]: toRemove.add(event)
                if arg2SuperType not in ["ProteinEntity", "GeneEntity"]: toRemove.add(event)
            # BI-task implicit rules (not defined in documentation, discovered by evaluator complaining)
            if len(event.arguments) == 2:
                # Evaluator says: "SEVERE: role Target does not allow entity of type Site".
                # This is not actually true, because if you check this for all Target-arguments, and
                # remove such events, performance decreases for the gold-data. But what can you do,
                # the evaluator keeps complaining, and won't process the data. The "solution" is to 
                # remove from Target/Site-checking those classes which reduce performance on gold data.
                if event.type not in ["BindTo", "SiteOf"]:
                    if arg1Type == "Site" and event.arguments[0][0] == "Target": 
                        if verbose: print "VAL:", docId + "." + str(event.id), "Removing illegal Target-argument from event", event.type
                        toRemove.add(event)
                    if arg2Type == "Site" and event.arguments[1][0] == "Target": 
                        if verbose: print "VAL:", docId + "." + str(event.id), "Removing illegal Target-argument from event", event.type
                        toRemove.add(event)
            # EPI-specific rules
            if event.type in ["Dephosphorylation",
                              "Hydroxylation",
                              "Dehydroxylation",
                              "Ubiquitination",
                              "Deubiquitination",
                              "DNA_methylation",
                              "DNA_demethylation",
                              "Glycosylation",
                              "Deglycosylation",
                              "Acetylation",
                              "Deacetylation",
                              "Methylation",
                              "Demethylation",
                              "Catalysis"]:
                eventType = event.type
                # Filter arguments
                for arg in event.arguments[:]:
                    if arg[2] != None and eventType == "Catalysis": # No task 2 for Catalysis
                        arg[2] = None
                    if arg[0] in ["Theme", "Cause"] and (arg[1].trigger == None and arg[1].type not in ["Protein", "Entity"]): # Suspicious, trigger as argument
                        event.arguments.remove(arg)
                    elif arg[0] == "Cause" and (arg[1].type != "Protein" or eventType != "Catalysis"):
                        event.arguments.remove(arg)
                    elif arg[0] == "Theme":
                        if eventType == "Catalysis":
                            if arg[1].type in ["Entity", "Protein"]:
                                event.arguments.remove(arg)
                        elif arg[1].type != "Protein":
                            event.arguments.remove(arg)
                    elif arg[0] == "Sidechain" and eventType not in ["Glycosylation", "Deglycosylation"]:
                        event.arguments.remove(arg)
                    elif arg[0] == "Contextgene" and (eventType not in ["Acetylation", "Deacetylation", "Methylation", "Demethylation"] or arg[1].type != "Protein"):
                        event.arguments.remove(arg)
                # Count remaining arguments
                typeCounts = {"Cause":0, "Theme":0}
                for arg in event.arguments:
                    if arg[0] in typeCounts:
                        typeCounts[arg[0]] += 1
                # Make choices
                if typeCounts["Theme"] == 0:
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), "EPI-event with no themes"
                if len(event.arguments) == 0:
                    toRemove.add(event)
                    if verbose: print "VAL:", docId + "." + str(event.id), "EPI-event with no arguments"
        
        # Remove events and remap arguments
        if not simulation:
            kept = []
            for event in events:
                if event not in toRemove:
                    for arg in event.arguments[:]:
                        if arg[1] in toRemove:
                            event.arguments.remove(arg)
                    kept.append(event)
                else:
                    removeCounts[event.type] += 1
            numRemoved = len(events) - len(kept)
            totalRemoved += numRemoved
            events = kept
        else:
            numRemoved = 0
    return events, removeCounts

def removeUnusedTriggers(document):
    # Remove triggers which are not used as triggers or arguments
    triggersToKeep = []
    for trigger in document.triggers:
        kept = False
        for event in document.events:
            if event.trigger == trigger:
                triggersToKeep.append(trigger)
                kept = True
                break
            else:
                for arg in event.arguments:
                    if arg[1] == trigger or arg[2] == trigger:
                        triggersToKeep.append(trigger)
                        kept = True
                        break
            if kept:
                break
    document.triggers = triggersToKeep

def allValidate(document, counts, task, verbose=False):
    numEvents = len(document.events)
    document.events, removeCounts = validate(document.events, verbose=verbose, docId=document.id) #, taskIsID=isIDTask(document.proteins))
    for key in removeCounts:
        counts["invalid-" + key] += removeCounts[key]
    counts["validation-removed"] += numEvents - len(document.events)
    numEvents = len(document.events)
    document.events = removeDuplicates(document.events)
    counts["duplicates-removed"] += numEvents - len(document.events)
    removeArguments(document, task, counts)
    removeEntities(document, task, counts)
    # triggers
    numTriggers = len(document.triggers)
    removeUnusedTriggers(document)
    counts["unused-triggers-removed"] += numTriggers - len(document.triggers)

def removeArguments(document, task, counts):
    if task != 1:
        return
    for event in document.events:
        for arg in event.arguments[:]:
            if arg[0] in ["Site", "AtLoc", "ToLoc", "Sidechain", "Contextgene"]:
                event.arguments.remove(arg)
                counts["t2-arguments-removed"] += 1
    
def removeEntities(document, task, counts):
    if task != 1:
        return
    # "Entity"-entities are not used in task 1, so they
    # can be removed then.
    triggersToKeep = []
    for trigger in document.triggers:
        if trigger.type == "Entity":
            counts["t2-entities-removed"] += 1
        else:
            triggersToKeep.append(trigger)
    document.triggers = triggersToKeep

if __name__=="__main__":
    import sys
    import STTools
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(description="Validate BioNLP'11 event constraints")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--noScores", default=False, action="store_true", dest="noScores", help="")
    (options, args) = optparser.parse_args()
    
    if options.output == None:
        options.output = options.input + "-validated.tar.gz"
    print >> sys.stderr, "Reading documents"
    documents = STTools.loadSet(options.input, readScores=(not options.noScores))
    print >> sys.stderr, "Writing documents"
    STTools.writeSet(documents, options.output, validate=True, writeScores=(not options.noScores), task=2, debug=options.debug)