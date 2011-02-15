from STTools import *
import combine
import copy

def process(documents):
    """
    Resolves equivalences in place
    """
    numOldEvents = 0
    numNewEvents = 0
    for doc in documents:
        print doc.id
        numOldEvents += len(doc.events)
        # Get all top-level events
        rootEvents = getRoots(doc)
        # Build new top level events
        newEvents = []
        for rootEvent in rootEvents:
            newEvents.extend(duplicateEquiv(rootEvent))
        # Regenerate the flat event list in the document
        doc.events = rebuildEventList(newEvents)
        numNewEvents += len(doc.events)
    print >> sys.stderr, "Duplication created", numNewEvents - numOldEvents, "new events"

def getRoots(document):
    """
    Returns topmost events in event hierarchy
    """
    eventDict = {}
    for event in document.events:
        eventDict[event.id] = event
    for event in document.events:
        for arg in event.arguments:
            if arg[1].id[0] == "E": # arg[1] is a nested event...
                if arg[1].id in eventDict: # ...if it hasn't been already removed...
                    del eventDict[arg[1].id] # ...remove it
    rootEvents = []
    for key in sorted(eventDict.keys()):
        rootEvents.append(eventDict[key])
    return rootEvents

def getArgs(event, argList):
    """
    Return the arguments of a nested event tree in a depth-first order.
    Each argument is in a list, and has multiple items if that argument
    is a protein with Equivs.
    """
    hasEquiv = False
    for arg in event.arguments:
        if len(arg[1].equiv) == 0:
            argList.append([arg[1]])
        else:
            hasEquiv = True
            argList.append([arg[1]] + arg[1].equiv)
        if arg[1].id[0] == "E": # nested event
            rv = getArgs(arg[1], argList)
            hasEquiv = rv or hasEquiv
    return hasEquiv

def makeEvent(model, argCombination, count, newEvent = None):
    """
    Given an argument list in depth-first order (argCombination), make
    a copy of "model" event tree.
    """
    if newEvent == None: # First call, make a new root
        #print "Mak", argCombination
        newEvent = Annotation()
        newEvent.trigger = model.trigger
        newEvent.id = model.id + "_d" + str(count)
        newEvent.speculation = model.speculation
        newEvent.negation = model.negation
    for arg in model.arguments:
        #print model.id, [x[1].id for x in model.arguments], arg[1].id, argCombination, newEvent, newEvent.arguments
        if arg[1].id[0] != "E": # not a nested event
            # Non-event arguments never need to be duplicated
            newEvent.arguments.append([arg[0], argCombination[0], arg[2]])
            argCombination = argCombination[1:] # pop first (depth-first iteration)
        else: # is a nested event
            # For event arguments, create a new copy
            assert arg[2] == None, (model.id, arg)
            newArg = [arg[0], copy.copy(argCombination[0]), None]
            argCombination = argCombination[1:] # pop first (depth-first iteration)
            newArg[1].arguments = [] # reset the argument list of the copy
            newArg[1].id += "_d" + str(count)
            newEvent.arguments.append(newArg) # add to parent copy
            makeEvent(arg[1], argCombination, count, newArg[1]) # Continue processing with next level of model and copy
    return newEvent

def duplicateEquiv(event):
    """
    If the event (event tree) has arguments which have Equiv-statements, create a new event
    for each combination. Otherwise, return just the existing event.
    """
    argList = [] # depth-first argument list
    hasEquiv = getArgs(event, argList)
    if not hasEquiv:
        return [event]
    print event.id
    #print "a", argList
    combinations = combine.combine(*argList) # make all combinations
    #print "b", combinations
    newEvents = []
    count = 0 # used only for marking duplicates' ids
    for combination in combinations:
        newEvents.append(makeEvent(event, combination, count))
        count += 1
    return newEvents

def rebuildEventList(events, eventList = None):
    """
    Add all events (top and nested) from event trees to a list.
    """
    if eventList == None:
        eventList = []
    for event in events:
        eventList.append(event)
        for arg in event.arguments:
            if arg[1].id[0] == "E":
                rebuildEventList([arg[1]], eventList)
    return eventList

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
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Loading documents from", options.input
    documents = loadSet(options.input)
    print >> sys.stderr, "Resolving equivalences"
    process(documents)
    print >> sys.stderr, "Writing documents to", options.output
    writeSet(documents, options.output)