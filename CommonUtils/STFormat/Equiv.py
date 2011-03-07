from STTools import *
import combine
import copy

def process(documents, debug=False):
    """
    Resolves equivalences in place
    """
    numOldEvents = 0
    numNewEvents = 0
    for doc in documents:
        #if doc.id != "PMC-2806624-00-TIAB":
        #    continue
        if debug:
            print "Document:", doc.id
        numOldEvents += len(doc.events)
        # Get all top-level events
        rootEvents = getRoots(doc)
        # Build new top level events
        newEvents = []
        # The same event that needs to be duplicated can be nested in several trees
        # The duplDict makes sure that duplicates are generated only once, and shared
        # between trees.
        duplDict = {}
        for rootEvent in rootEvents:
            newEvents.extend(duplicateEquiv(rootEvent, duplDict, debug))
        # Regenerate the flat event list in the document
        doc.events = rebuildEventList(newEvents)
        doc.events.sort(key = lambda x: (x.id[0], int(x.id[1:].split(".")[0]), x.id[1:].split(".")[-1]) )
        numNewEvents += len(doc.events)
    print >> sys.stderr, "Duplication created", numNewEvents - numOldEvents, "new events (new total", numNewEvents, "events)"

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
            assert arg[1] not in arg[1].equiv
        if arg[1].id[0] == "E": # nested event
            assert len(arg[1].equiv) == 0
            if hasNestedEquivs(arg[1]):
                rv = getArgs(arg[1], argList)
                hasEquiv = rv or hasEquiv
            else:
                pass # stop recursion
    return hasEquiv

def hasNestedEquivs(event):
    rv = False
    for arg in event.arguments:
        if len(arg[1].equiv) != 0:
            rv = True
        elif arg[1].id[0] == "E": # nested event
            rv = rv or hasNestedEquivs(arg[1]) 
    return rv

def makeEvent(model, argCombination, count, newEvent = None, finished=False, duplDict=None, debug=False, level=0):
    """
    Given an argument list in depth-first order (argCombination), make
    a copy of "model" event tree.
    """
    if newEvent == None: # First call, make a new root
        if debug:
            print "Arg.Comb.:", argCombination
        #print "Mak", argCombination
        newEvent = Annotation()
        newEvent.trigger = model.trigger
        newEvent.type = model.type
        newEvent.id = model.id + ".d" + str(count)
        newEvent.speculation = model.speculation
        newEvent.negation = model.negation
    for arg in model.arguments:
        #if debug: print level * " ", model.id, [x[1].id for x in model.arguments], "/", arg[1].id, argCombination, "/", newEvent, newEvent.arguments
        if arg[1].id[0] != "E": # not a nested event
            # Non-event arguments never need to be duplicated
            if not finished:
                newEvent.arguments.append([arg[0], argCombination[0], arg[2]])
            argCombination.pop(0) # pop first (depth-first iteration)
            if debug: print level * " ", "SIMP", model.id, [x[1].id for x in model.arguments], "/", arg[1].id, argCombination, "/", newEvent, newEvent.arguments
        else: # is a nested event
            assert arg[2] == None, (model.id, arg)
            if not finished:
                if hasNestedEquivs(arg[1]):
                    # For event arguments that have children with equiv, create a new copy
                    duplId = arg[1].id + ".d" + str(count)
                    if duplId not in duplDict:
                        newArg = [arg[0], copy.copy(argCombination[0]), None]
                        argCombination.pop(0) # pop first (depth-first iteration)
                        newArg[1].arguments = [] # reset the argument list of the copy
                        newArg[1].id = duplId
                        newEvent.arguments.append(newArg) # add to parent copy
                        duplDict[duplId] = newArg
                        if debug: print level * " ", "NEST(new)", model.id, [x[1].id for x in model.arguments], "/", arg[1].id, argCombination, "/", newEvent, newEvent.arguments
                        makeEvent(arg[1], argCombination, count, newArg[1], finished, duplDict, level=level+1, debug=debug) # Continue processing with next level of model and copy
                    else:
                        argCombination.pop(0) # pop first (depth-first iteration)
                        newEvent.arguments.append(duplDict[duplId]) # add to parent copy
                        if debug: print level * " ", "NEST(old)", model.id, [x[1].id for x in model.arguments], "/", arg[1].id, argCombination, "/", newEvent, newEvent.arguments
                        makeEvent(arg[1], argCombination, count, duplDict[duplId][1], True, duplDict, level=level+1, debug=debug) # Continue processing with next level of model and copy
                else:
                    newArg = [arg[0], argCombination[0], None]
                    argCombination.pop(0) # pop first (depth-first iteration)
                    newEvent.arguments.append(newArg) # add to parent copy
                    if debug: print level * " ", "STOP", model.id, [x[1].id for x in model.arguments], "/", arg[1].id, argCombination, "/", newEvent, newEvent.arguments
                    # stop recursion here, it has been likewise stopped in getArgs
                    #makeEvent(arg[1], argCombination, count, newArg[1], True, duplDict, level=level+1) # Continue processing with next level of model and copy
    return newEvent

def duplicateEquiv(event, duplDict, debug):
    """
    If the event (event tree) has arguments which have Equiv-statements, create a new event
    for each combination. Otherwise, return just the existing event.
    """
    argList = [] # depth-first argument list
    hasEquiv = getArgs(event, argList)
    if not hasEquiv:
        return [event]
    if debug:
        print "Event:", event.id, event.type, event.arguments
        print " Orig. Duplicates:", argList
    combinations = combine.combine(*argList) # make all combinations
    if debug:
        print " Dup. Combinations:", combinations
    newEvents = []
    count = 0 # used only for marking duplicates' ids
    for combination in combinations:
        newEvent = makeEvent(event, combination, count, duplDict=duplDict, debug=debug)
        if debug:
            print " New Event:", newEvent.id, newEvent.type, newEvent.arguments
        newEvents.append(newEvent)
        count += 1
    return newEvents

def rebuildEventList(events, eventList = None):
    """
    Add all events (top and nested) from event trees to a list.
    """
    if eventList == None:
        eventList = []
    for event in events:
        if event not in eventList:
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
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Loading documents from", options.input
    documents = loadSet(options.input)
    print >> sys.stderr, "Resolving equivalences"
    process(documents, debug=options.debug)
    print >> sys.stderr, "Writing documents to", options.output
    writeSet(documents, options.output)