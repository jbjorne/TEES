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

#def getEventValues(event, values, currentValue = 0):
#    """
#    Return the arguments of a nested event tree in a depth-first order.
#    Each argument is in a list, and has multiple items if that argument
#    is a protein with Equivs.
#    """
#    if event not in values or values[event] < currentValue:
#        values[event] = currentValue            
#    for arg in event.arguments:
#        if arg[1].id[0] == "E": # nested event
#            getEventValues(arg[1], values, currentValue + 1)