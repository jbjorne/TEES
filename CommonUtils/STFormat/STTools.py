import sys, os

class Document():
    def __init__(self):
        self.text = None
        self.proteins = None
        self.triggers = None
        self.events = None

class Annotation():
    def __init__(self, id = None, type = None, text=None, trigger=None, arguments=None):
        self.id = id # protein/trigger/event
        self.type = type # protein/trigger/event
        self.text = text # protein/trigger
        self.charBegin = -1 # protein/trigger
        self.charEnd = -1 # protein/trigger
        self.trigger = trigger # event
        self.arguments = [] # event
        if arguments != None:
            self.arguments = arguments
        self.speculation = None # event 
        self.negation = None # event
    
    def isNegated(self):
        return self.negation != None
    
    def isSpeculated(self):
        return self.speculation != None
    
def readTAnnotation(string):
    assert string[0] == "T", string
    string = string.strip()
    ann = Annotation()
    ann.id, middle, ann.text = string.split("\t")
    ann.type, ann.charBegin, ann.charEnd = middle.split()
    ann.charBegin = int(ann.charBegin)
    ann.charEnd = int(ann.charEnd)
    return ann

def readEvent(string):
    string = string.strip()
    ann = Annotation()
    ann.id, rest = string.split("\t")
    args = rest.split(" ")
    trigger = args[0]
    args = args[1:]
    ann.type, ann.trigger = trigger.split(":")
    for arg in args:
        argTuple = arg.split(":")
        if argTuple[0].find("Theme") != -1: # multiple themes are numbered
            argTuple = ("Theme", argTuple[1])
        ann.arguments.append( argTuple ) 
    return ann

def loadA1(filename):
    f = open(filename)
    proteins = []
    for line in f:
        proteins.append(readTAnnotation(line))
    f.close()
    return proteins

def loadA2(filename, proteins):
    f = open(filename)
    triggers = []
    triggerMap = {}
    for protein in proteins:
        triggerMap[protein.id] = protein
    events = []
    eventMap = {}
    for line in f:
        if line[0] == "T":
            triggers.append( readTAnnotation(line) )
            triggerMap[triggers[-1].id] = triggers[-1]
        elif line[0] == "E":
            events.append( readEvent(line) )
            eventMap[events[-1].id] = events[-1]
        elif line[0] == "M":
            mId, rest = line.split("\t")
            mType, eventId = rest.split()
            if mType == "Speculation":
                eventMap[eventId].speculation = mId
            elif mType == "Negation":
                eventMap[eventId].negation = mId
    # Build links
    for event in events:
        event.trigger = triggerMap[event.trigger]
        for i in range(len(event.arguments)):
            arg = event.arguments[i]
            if arg[1][0] == "T":
                event.arguments[i] = (arg[0], triggerMap[arg[1]])
            elif arg[1][0] == "E":
                event.arguments[i] = (arg[0], eventMap[arg[1]])
    f.close()
    return triggers, events

def load(id, dir):
    id = str(id)
    proteins = loadA1(os.path.join(dir, id + ".a1"))
    triggers, events = loadA2(os.path.join(dir, id + ".a2"), proteins)
    return proteins, triggers, events  

def getMaxId(annotations):
    nums = [0]
    for annotation in annotations:
        if annotation.id != None:
            nums.append(int(annotation.id[1:]))
    return max(nums)

def updateIds(annotations, minId=0):
    newIds = False
    for ann in annotations:
        if ann.id == None:
            newIds = True
            break
    if newIds:
        idCount = max(getMaxId(annotations) + 1, minId)
        for ann in annotations:
            if len(ann.arguments) == 0:
                ann.id = "T" + str(idCount)
            else:
                ann.id = "E" + str(idCount)
            idCount += 1

def writeTAnnotation(proteins, out, idStart=0):
    updateIds(proteins, idStart)
    for protein in proteins:
        assert protein.id[0] == "T", (protein.id, protein.text)
        out.write(protein.id + "\t")
        out.write(protein.type + " " + str(protein.charBegin) + " " + str(protein.charEnd) + "\t")
        if protein.text == None:
            out.write(str(protein.text) + "\n")
        else:
            out.write(protein.text + "\n")

def writeEvents(events, out):
    updateIds(events)
    for event in events:
        out.write(event.id + "\t")
        trigger = event.trigger
        out.write(trigger.type + ":" + trigger.id)
        typeCounts = {}
        # Count arguments
        for arg in event.arguments:
            argType = arg[0]
            if not typeCounts.has_key(argType):
                typeCounts[argType] = 0
            typeCounts[argType] += 1
        # Determine which arguments need numbering
        for key in typeCounts.keys():
            if typeCounts[key] > 1:
                typeCounts[key] = 1
            else:
                del typeCounts[key]
        # Write arguments
        for arg in event.arguments:
            argType = arg[0]
            if typeCounts.has_key(argType):
                out.write(" " + argType + str(typeCounts[argType]) + ":" + arg[1].id)
                typeCounts[argType] += 1
            else:
                out.write(" " + argType + ":" + arg[1].id)
        out.write("\n")
    # Write task 3
    #for event in events:
    #    if event.negation != None:

def write(id, dir, proteins, triggers, events):
    id = str(id)
    if not os.path.exists(dir):
        os.makedirs(dir)
    if proteins != None:
        out = open(os.path.join(dir, id + ".a1"), "wt")
        writeTAnnotation(proteins, out)
    if triggers != None:
        out = open(os.path.join(dir, id + ".a2"), "wt")
        writeTAnnotation(triggers, out, getMaxId(proteins) + 1)
        writeEvents(events, out)
        out.close()
        
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    proteins, triggers, events = load(1335418, "/home/jari/biotext/tools/TurkuEventExtractionSystem-1.0/data/evaluation-data/evaluation-tools-devel-gold")
    write(1335418, "/home/jari/data/temp", proteins, triggers, events )
    





