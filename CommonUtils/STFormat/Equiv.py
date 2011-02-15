from STTools import *
import combine
import copy

def process(documents):
    numOldEvents = 0
    numNewEvents = 0
    for doc in documents:
        print doc.id
        numOldEvents += len(doc.events)
        rootEvents = getRoots(doc)
        newEvents = []
        for rootEvent in rootEvents:
            newEvents.extend(duplicateEquiv(rootEvent))
        doc.events = rebuildEventList(newEvents)
        numNewEvents += len(doc.events)
    print >> sys.stderr, "Duplication created", numNewEvents - numOldEvents, "new events"

def getRoots(document):
    eventDict = {}
    for event in document.events:
        eventDict[event.id] = event
    for event in document.events:
        for arg in event.arguments:
            if arg[1].id[0] == "E": # arg[1] is a nested event
                if arg[1].id in eventDict:
                    del eventDict[arg[1].id]
    rootEvents = []
    for key in sorted(eventDict.keys()):
        rootEvents.append(eventDict[key])
    return rootEvents

def getArgs(event, argList):
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
    if newEvent == None:
        print "Mak", argCombination
        newEvent = Annotation()
        newEvent.trigger = model.trigger
        newEvent.id = model.id + "_d" + str(count)
        newEvent.speculation = model.speculation
        newEvent.negation = model.negation
    for arg in model.arguments:
        print model.id, [x[1].id for x in model.arguments], arg[1].id, argCombination, newEvent, newEvent.arguments
        if arg[1].id[0] != "E": # not a nested event
            newEvent.arguments.append([arg[0], argCombination[0], arg[2]])
            argCombination = argCombination[1:] # pop first
        else:
            assert arg[2] == None, (model.id, arg)
            newArg = [arg[0], copy.copy(argCombination[0]), None]
            argCombination = argCombination[1:] # pop first
            newArg[1].arguments = []
            newArg[1].id += "_d" + str(count)
            newEvent.arguments.append(newArg)
            makeEvent(arg[1], argCombination, count, newArg[1])
    return newEvent

def duplicateEquiv(event):
    argList = []
    hasEquiv = getArgs(event, argList)
    if not hasEquiv:
        return [event]
    print event.id
    print "a", argList
    combinations = combine.combine(*argList)
    print "b", combinations
    newEvents = []
    count = 0
    for combination in combinations:
        newEvents.append(makeEvent(event, combination, count))
        count += 1
    return newEvents

def rebuildEventList(events, eventList = None):
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