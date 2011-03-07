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
    numRemoved = 1
    totalRemoved = 0
    # Since removed events cause nesting events' arguments to be remapped, 
    # some of these nesting events may in turn become duplicates. Loop until
    # all such duplicates are removed.
    while(numRemoved > 0):
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

# Enfore type-specific limits
def validate(events):
    numRemoved = 1
    totalRemoved = 0
    # Since removed events cause nesting events' arguments to be remapped, 
    # some of these nesting events may in turn become duplicates. Loop until
    # all such duplicates are removed.
    while(numRemoved > 0):
        toRemove = set()
        for event in events:
            if "egulation" in event.type:
                typeCounts = {"Cause":0, "Theme":0}
                for arg in event.arguments[:]:
                    if arg[0] not in typeCounts:
                        event.arguments.remove(arg)
                    else:
                        typeCounts[arg[0]] += 1
                if typeCounts["Theme"] == 0:
                    toRemove.add(event)
                if len(event.arguments) == 0:
                    toRemove.add(event)
            if event.type == "PartOf":
                assert len(event.arguments) == 2
                if event.arguments[0][1].type != "Host":
                    toRemove.add(event)
                if event.arguments[1][1].type != "HostPart":
                    toRemove.add(event)
            if event.type == "Localization":
                for arg in event.arguments:
                    if arg[0] == "Bacterium" and arg[1].type != "Bacterium":
                        toRemove.add(event)
        # Remove events and remap arguments
        kept = []
        for event in events:
            if event not in toRemove:
                for arg in event.arguments[:]:
                    if arg[1] in toRemove:
                        event.arguments.remove(arg)
                kept.append(event)
        numRemoved = len(events) - len(kept)
        totalRemoved += numRemoved
        events = kept
    return events

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

def allValidate(document, counts, task):
    numEvents = len(document.events)
    document.events = validate(document.events)
    counts["validation-removed"] += numEvents - len(document.events)
    numEvents = len(document.events)
    document.events = removeDuplicates(document.events)
    counts["duplicates-removed"] += numEvents - len(document.events)
    # triggers
    numTriggers = len(document.triggers)
    removeUnusedTriggers(document)
    counts["triggers-removed"] += numTriggers - len(document.triggers)
    removeEntities(document, task, counts)

def removeEntities(document, task, counts):
    triggersToKeep = []
    for trigger in document.triggers:
        if trigger.type == "Entity" and task == 1:
            counts["entities-removed"] += 1
        else:
            triggersToKeep.append(trigger)
    document.triggers = triggersToKeep
            