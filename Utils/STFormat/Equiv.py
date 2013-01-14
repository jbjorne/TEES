from STTools import *
import Validate
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Libraries.combine as combine
import copy

def process(documents, debug=False):
    """
    Resolves equivalences in place
    """
    numOldEvents = 0
    numNewEvents = 0
    for doc in documents:
        # Arg.siteOf links are temporarily removed, because during duplication the argument pointed to by siteOf
        # may end up in another event. To preserve the core/site pairs, when arguments are copied, their "full type"
        # (e.g. Theme2) is restored. After duplication is done, core/site pairs can be relinked just the way they 
        # are linked when reading from ST-format files, because A) old arguments have an intact arg.siteIdentifier
        # B) new arguments have full types (e.g. Theme2) and C) the argument type combination is the same for each
        # duplicate. 
        doc.unlinkSites()
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
        doc.connectSites() # rebuild site links
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
            if arg.target.id[0] == "E": # arg[1] is a nested event...
                if arg.target.id in eventDict: # ...if it hasn't been already removed...
                    del eventDict[arg.target.id] # ...remove it
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
        if len(arg.target.equiv) == 0:
            argList.append([arg.target])
        else:
            hasEquiv = True
            argList.append([arg.target] + arg.target.equiv)
            assert arg.target not in arg.target.equiv
        if arg.target.id[0] == "E": # nested event
            assert len(arg.target.equiv) == 0
            if hasNestedEquivs(arg.target):
                rv = getArgs(arg.target, argList)
                hasEquiv = rv or hasEquiv
            else:
                pass # stop recursion
    return hasEquiv

def hasNestedEquivs(event):
    rv = False
    for arg in event.arguments:
        if len(arg.target.equiv) != 0:
            rv = True
        elif arg.target.id[0] == "E": # nested event
            rv = rv or hasNestedEquivs(arg.target) 
    return rv

def makeEvent(model, argCombination, count, newEvent = None, finished=False, duplDict=None, debug=False, level=0):
    """
    Given an argument list in depth-first order (argCombination), make
    a copy of "model" event tree.
    """
    createdEvents = []
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
        createdEvents.append(newEvent)
    for arg in model.arguments:
        #if debug: print level * " ", model.id, [x[1].id for x in model.arguments], "/", arg[1].id, argCombination, "/", newEvent, newEvent.arguments
        if arg.target.id[0] != "E": # not a nested event
            # Non-event arguments never need to be duplicated
            if not finished:
                newEvent.addArgument(model.getArgumentFullType(arg), argCombination[0])
                #newEvent.arguments.append([arg[0], argCombination[0], arg[2]])
            argCombination.pop(0) # pop first (depth-first iteration)
            if debug: 
                print level * " ", "SIMP", model.id, [x.target.id for x in model.arguments], "/", arg.target.id, argCombination, "/", newEvent, newEvent.arguments
        else: # is a nested event
            #assert arg.siteOf == None, (model.id, arg)
            if not finished:
                if hasNestedEquivs(arg.target):
                    # For event arguments that have children with equiv, create a new copy
                    duplId = arg.target.id + ".d" + str(count)
                    #duplId = arg[1].id.split(".d")[0] + ".d" + str(count)
                    if duplId not in duplDict:
                        newArg = Argument(model.getArgumentFullType(arg), copy.copy(argCombination[0])) #[arg[0], copy.copy(argCombination[0]), None] # Make a new event
                        createdEvents.append(newArg.target)
                        argCombination.pop(0) # pop first (depth-first iteration)
                        newArg.target.arguments = [] # reset the argument list of the copy
                        newArg.target.id = duplId
                        newEvent.arguments.append(newArg) # add to parent copy
                        duplDict[duplId] = newArg.target # add the new event to duplDict #duplDict[duplId] = newArg
                        if debug: 
                            print level * " ", "NEST(new)", model.id, [x.target.id for x in model.arguments], "/", arg.target.id, argCombination, "/", newEvent, newEvent.arguments
                        createdEvents += makeEvent(arg.target, argCombination, count, newArg.target, finished, duplDict, level=level+1, debug=debug) # Continue processing with next level of model and copy
                    else:
                        newArg = Argument(model.getArgumentFullType(arg), duplDict[duplId]) #[arg[0], duplDict[duplId], None]
                        argCombination.pop(0) # pop first (depth-first iteration)
                        #newEvent.arguments.append(duplDict[duplId]) # add to parent copy
                        newEvent.arguments.append(newArg) # add to parent copy
                        if debug: 
                            print level * " ", "NEST(old)", model.id, [x.target.id for x in model.arguments], "/", arg.target.id, argCombination, "/", newEvent, newEvent.arguments
                        #makeEvent(arg[1], argCombination, count, duplDict[duplId][1], True, duplDict, level=level+1, debug=debug) # Continue processing with next level of model and copy
                        createdEvents += makeEvent(arg.target, argCombination, count, duplDict[duplId], True, duplDict, level=level+1, debug=debug) # Continue processing with next level of model and copy
                else:
                    newArg = Argument(model.getArgumentFullType(arg), argCombination[0]) #[arg[0], argCombination[0], None]
                    argCombination.pop(0) # pop first (depth-first iteration)
                    newEvent.arguments.append(newArg) # add to parent copy
                    if debug: 
                        print level * " ", "STOP", model.id, [x.target.id for x in model.arguments], "/", arg.target.id, argCombination, "/", newEvent, newEvent.arguments
                    # stop recursion here, it has been likewise stopped in getArgs
                    #makeEvent(arg[1], argCombination, count, newArg[1], True, duplDict, level=level+1) # Continue processing with next level of model and copy
    return createdEvents

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
        print "----------------------------------------------"
        print "Event:", event.id, event.type, event.arguments
        print " Orig. Duplicates:", argList
    combinations = combine.combine(*argList) # make all combinations
    if debug:
        print " Dup. Combinations:", combinations
    newEvents = []
    count = 0 # used only for marking duplicates' ids
    for combination in combinations:
        createdEvents = makeEvent(event, combination, count, duplDict=duplDict, debug=debug)
        newEvent = createdEvents[0]
        if debug:
            for createdEvent in createdEvents:
                if createdEvent == newEvent:
                    print " New Event (root):", createdEvent.id, createdEvent.type, createdEvent.arguments
                else:
                    print " New Event:", createdEvent.id, createdEvent.type, createdEvent.arguments
                #Validate.validate([createdEvent], simulation=True)
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
            if arg.target.id[0] == "E":
                rebuildEventList([arg.target], eventList)
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

    optparser = OptionParser(description="Resolve annotated equivalences")
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