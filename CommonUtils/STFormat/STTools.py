import sys, os

class Document():
    def __init__(self):
        self.id = None
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
        self.equiv = [] # group of elements that are equivalent
        self.trigger = trigger # event
        self.arguments = [] # event
        if arguments != None:
            self.arguments = arguments
        self.sites = []
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

def readStarAnnotation(string, proteins):
    assert string[0] == "*", string
    string = string.strip()
    star, rest = string.split("\t")
    equivs = []
    if rest.find("Equiv") == 0:
        type, t1, t2 = rest.split(" ")
        equivs.append( (t1, t2) )
    if len(equivs) > 0:
        protMap = {}
        for protein in proteins:
            protMap[protein.id] = protein
        for equiv in equivs:
            p1 = protMap[equiv[0]]
            p2 = protMap[equiv[0]]
            equivGroup = None
            if p1.equiv != None and p1.equiv == p2.equiv: # equivalence exists already
                continue
            if p1.equiv != None:
                equivGroup = p1.equiv
            if p2.equiv != None:
                if equivGroup != None: # if two proteins are already equal
                    assert p2.equiv != p1.equiv
                    equivGroup = p1.equiv + p2.equiv
                else:
                    equivGroup = p2.equiv
            if equivGroup == None:
                equivGroup = []
            if not p1 in equivGroup:
                equivGroup.append(p1)
            if not p2 in equivGroup:
                equivGroup.append(p2)
            # set the equiv group
            p1.equiv = equivGroup
            p2.equiv = equivGroup

def readEvent(string):
    string = string.strip()
    ann = Annotation()
    ann.id, rest = string.split("\t")
    args = rest.split()
    trigger = args[0]
    args = args[1:]
    ann.type, ann.trigger = trigger.split(":")
    argMap = {}
    #print string
    for arg in args:
        argTuple = arg.split(":") + [None]
        if argTuple[0].find("Site") == -1:
            origArgName = argTuple[0]
            if argTuple[0].find("Theme") != -1: # multiple themes are numbered
                argTuple = ["Theme", argTuple[1], None]
            assert origArgName != "" # extra whitespace caused errors with splitting, splitting fixed
            argMap[origArgName] = argTuple
            ann.arguments.append( argTuple )
    #print argMap
    if len(argMap.keys()) != len(args): # We have sites
        for arg in args:
            argTuple = arg.split(":") + []
            if argTuple[0].find("Site") != -1:
                if argTuple[0] == "CSite":
                    argMap["Cause"][2] = argTuple[1]
                else:
                    argMap[ "Theme" + argTuple[0][4:] ][2] = argTuple[1] 
    return ann

def loadA1(filename):
    f = open(filename)
    proteins = []
    starSection = False
    for line in f:
        if starSection: # assume all proteins are defined before equivalences
            assert line[0] == "*"
        if line[0] == "T":
            proteins.append(readTAnnotation(line))
        elif line[0] == "*":
            starSection = True
            readStarAnnotation(line, proteins)
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
        #print event.id
        event.trigger = triggerMap[event.trigger]
        for i in range(len(event.arguments)):
            arg = event.arguments[i]
            if arg[1][0] == "T":
                if arg[2] != None:
                    event.arguments[i] = (arg[0], triggerMap[arg[1]], triggerMap[arg[2]])
                else:
                    event.arguments[i] = (arg[0], triggerMap[arg[1]], None)
            elif arg[1][0] == "E":
                assert arg[2] == None # no sites on events
                event.arguments[i] = (arg[0], eventMap[arg[1]], None)
    f.close()
    return triggers, events

def loadText(filename):
    f = open(filename)
    text = f.read()
    f.close()
    return text

def load(id, dir):
    id = str(id)
    proteins = loadA1(os.path.join(dir, id + ".a1"))
    triggers, events = loadA2(os.path.join(dir, id + ".a2"), proteins)
    return proteins, triggers, events

def loadSet(dir):
    ids = set()
    documents = []
    for filename in os.listdir(dir):
        if filename.find(".") != -1:
            ids.add(int(filename.split(".")[0]))
    for id in sorted(list(ids)):
        #print "Loading", id
        doc = Document()
        doc.id = id
        doc.proteins, doc.triggers, doc.events = load(str(id), dir)
        doc.text = loadText( os.path.join(dir, str(id) + ".txt") )
        documents.append(doc)
    return documents

def writeSet(documents, dir):
    for doc in documents:
        write(doc.id, dir, doc.proteins, doc.triggers, doc.events)
        # Write text file
        out = open(os.path.join(dir, str(doc.id) + ".txt"), "wt")
        out.write(doc.text)
        out.close()

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
    mCounter = 1
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
                if typeCounts[argType] > 1:
                    out.write(" " + argType + str(typeCounts[argType]) + ":" + arg[1].id)
                else:
                    out.write(" " + argType + ":" + arg[1].id)
                typeCounts[argType] += 1
            else:
                out.write(" " + argType + ":" + arg[1].id)
        
        # Reset type counts for writing sites
        for key in typeCounts.keys():
            typeCounts[key] = 1
        # Write sites
        for arg in event.arguments:
            argType = arg[0]
            if typeCounts.has_key(argType):
                typeCounts[argType] += 1
            if arg[2] == None:
                continue
            
            sitePrefix = ""
            if argType.find("Cause") != -1:
                sitePrefix = "C"
            if typeCounts.has_key(argType) and typeCounts[argType] > 1:
                out.write(" " + sitePrefix + "Site" + str(typeCounts[argType]) + ":" + arg[2].id)
            else:
                out.write(" " + sitePrefix + "Site" + ":" + arg[2].id)                
        out.write("\n")

        # Write task 3
        if event.speculation != None:
            out.write("M" + str(mCounter) + "\t" + "Speculation " + str(event.id) + "\n")
            mCounter += 1
        if event.negation != None:
            out.write("M" + str(mCounter) + "\t" + "Negation " + str(event.id) + "\n")
            mCounter += 1

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
    
    #proteins, triggers, events = load(1335418, "/home/jari/biotext/tools/TurkuEventExtractionSystem-1.0/data/evaluation-data/evaluation-tools-devel-gold")
    #write(1335418, "/home/jari/data/temp", proteins, triggers, events )
    
    p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
    documents = loadSet(p)
    writeSet(documents, "/home/jari/data/temp/testSTTools")
    





