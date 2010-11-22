import sys, os

class Document():
    def __init__(self):
        self.id = None
        self.text = None
        self.proteins = []
        self.triggers = []
        self.events = []
        self.relations = []
        self.dataSet = None

class Annotation():
    def __init__(self, id = None, type = None, text=None, trigger=None, arguments=None):
        self.id = id # protein/trigger/event
        self.type = type # protein/trigger/event
        self.text = text # protein/trigger
        self.charBegin = -1 # protein/trigger
        self.charEnd = -1 # protein/trigger
        self.alternativeOffsets = []
        self.equiv = [] # group of elements that are equivalent
        self.trigger = trigger # event
        self.arguments = [] # event/relation
        if arguments != None:
            self.arguments = arguments
        self.sites = []
        self.speculation = None # event 
        self.negation = None # event
    
    def isNegated(self):
        return self.negation != None
    
    def isSpeculated(self):
        return self.speculation != None
    
    def isName(self):
        return self.type == "Protein" or self.type == "Gene"
    
def readTAnnotation(string):
    #print string
    assert string[0] == "T", string
    string = string.strip()
    ann = Annotation()
    splits = string.split("\t")
    ann.id = splits[0]
    middle = splits[1]
    ann.text = splits[2]
    #ann.id, middle, ann.text = string.split("\t")
    ann.type, ann.charBegin, ann.charEnd = middle.split()
    ann.charBegin = int(ann.charBegin)
    ann.charEnd = int(ann.charEnd)
    if len(splits) > 3:
        skip = False
        for split in splits[3:]:
            if not skip:
                cSplits = split.split()
                assert len(cSplits) == 2, (cSplits, string)
                c1 = int(cSplits[0])
                c2 = int(cSplits[1])
                ann.alternativeOffsets.append( (c1, c2) )
            skip = not skip
    return ann

def readStarAnnotation(string, proteins):
    assert string[0] == "*", string
    string = string.strip()
    star, rest = string.split("\t")
    equivs = []
    if rest.find("Equiv") == 0:
        splits = rest.split(" ")
        type = splits[0]
        assert type == "Equiv"
        entities = splits[1:] 
        equivs.append( entities )
    if len(equivs) > 0:
        protMap = {}
        for protein in proteins:
            protMap[protein.id] = protein
        for equiv in equivs:
            for member in equiv:
                for other in equiv:
                    if member == other:
                        continue
                    if not protMap[other] in protMap[member].equiv:
                        protMap[member].equiv.append(protMap[other])

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

def readRAnnotation(string):
    string = string.strip()
    ann = Annotation()
    tabSplits = string.split("\t")
    ann.id = tabSplits[0]
    args = tabSplits[1].split()
    ann.type = args[0]
    args = args[1:]
    argMap = {}
    #print string
    for arg in args:
        argTuple = arg.split(":") + [None]
        #assert argTuple[0].find("Arg") != -1, (string, argTuple)
        ann.arguments.append( (argTuple[0], argTuple[1], None) )
    if len(tabSplits) == 3:
        assert ann.type == "Coref"
        assert tabSplits[2][0] == "[" and tabSplits[2][-1] == "]", (string, tabSplits)
        protIds = tabSplits[2][1:-1].split(",")
        for protId in protIds:
            ann.arguments.append( ("Connected", protId.strip(), None) )
    return ann

#def loadRel(filename, proteins):
#    triggerMap = {}
#    for protein in proteins:
#        triggerMap[protein.id] = protein
#        
#    f = open(filename)
#    triggers = []
#    relations = []
#    lines = f.readlines()
#    for line in lines:
#        if line[0] == "T":
#            triggers.append(readTAnnotation(line))
#            triggerMap[triggers[-1].id] = triggers[-1]
#    for line in lines:
#        if line[0] == "*":
#            readStarAnnotation(line, proteins+triggers)
#    for line in lines:
#        if line[0] == "R":
#            relations.append(readRAnnotation(line))
#    f.close()
#    
#    # Build links
#    for relation in relations:
#        for i in range(len(relation.arguments)):
#            arg = relation.arguments[i]
#            if arg[1][0] == "T":
#                if arg[2] != None:
#                    relation.arguments[i] = (arg[0], triggerMap[arg[1]], triggerMap[arg[2]])
#                else:
#                    relation.arguments[i] = (arg[0], triggerMap[arg[1]], None)
#                
#    return triggers, relations

def loadA1(filename):
    f = open(filename)
    proteins = []
    #starSection = False
    lines = f.readlines()
    for line in lines:
        #if starSection: # assume all proteins are defined before equivalences
        #    assert line[0] == "*"
        if line[0] == "T":
            proteins.append(readTAnnotation(line))
    for line in lines:
        if line[0] == "*":
            #starSection = True
            readStarAnnotation(line, proteins)
    f.close()
    return proteins

#def loadA2(filename, proteins):
#    f = open(filename)
#    triggers = []
#    triggerMap = {}
#    for protein in proteins:
#        triggerMap[protein.id] = protein
#    events = []
#    eventMap = {}
#    for line in f:
#        if line[0] == "T":
#            triggers.append( readTAnnotation(line) )
#            triggerMap[triggers[-1].id] = triggers[-1]
#        elif line[0] == "E":
#            events.append( readEvent(line) )
#            eventMap[events[-1].id] = events[-1]
#        elif line[0] == "M":
#            mId, rest = line.split("\t")
#            mType, eventId = rest.split()
#            if mType == "Speculation":
#                eventMap[eventId].speculation = mId
#            elif mType == "Negation":
#                eventMap[eventId].negation = mId
#    # Build links
#    for event in events:
#        #print event.id
#        event.trigger = triggerMap[event.trigger]
#        for i in range(len(event.arguments)):
#            arg = event.arguments[i]
#            if arg[1][0] == "T":
#                if arg[2] != None:
#                    event.arguments[i] = (arg[0], triggerMap[arg[1]], triggerMap[arg[2]])
#                else:
#                    event.arguments[i] = (arg[0], triggerMap[arg[1]], None)
#            elif arg[1][0] == "E":
#                assert arg[2] == None # no sites on events
#                event.arguments[i] = (arg[0], eventMap[arg[1]], None)
#    f.close()
#    return triggers, events

def loadRelOrA2(filename, proteins):
    f = open(filename)
    triggers = []
    triggerMap = {}
    for protein in proteins:
        triggerMap[protein.id] = protein
    events = []
    eventMap = {}
    relations = []
    lines = f.readlines()
    f.close()
    for line in lines:
        if line[0] == "T":
            triggers.append( readTAnnotation(line) )
            triggerMap[triggers[-1].id] = triggers[-1]
    for line in lines:
        if line[0] == "E":
            events.append( readEvent(line) )
            eventMap[events[-1].id] = events[-1]
    for line in lines:
        if line[0] == "R":
            relations.append(readRAnnotation(line))
    for line in lines:
        if line[0] == "M":
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
    # Build links
    for relation in relations:
        for i in range(len(relation.arguments)):
            arg = relation.arguments[i]
            if arg[1][0] == "T":
                if arg[2] != None:
                    relation.arguments[i] = (arg[0], triggerMap[arg[1]], triggerMap[arg[2]])
                else:
#                    if not triggerMap.has_key(arg[1]): # NOTE! hack for CO bugs
#                        relation.arguments = relation.arguments[0:i]
#                        if len(relation.arguments) == 1: # NOTE! hack
#                            relations = []
#                        break
                    relation.arguments[i] = (arg[0], triggerMap[arg[1]], None)

    return triggers, events, relations

def loadText(filename):
    f = open(filename)
    text = f.read()
    f.close()
    return text

def load(id, dir):
    #print id
    id = str(id)
    proteins = loadA1(os.path.join(dir, id + ".a1"))
    a2Path = os.path.join(dir, id + ".a2")
    relPath = os.path.join(dir, id + ".rel")
    triggers = []
    events = []
    relations = []
    if os.path.exists(a2Path):
        triggers, events, relations = loadRelOrA2(a2Path, proteins)
    elif os.path.exists(relPath):
        triggers, events, relations = loadRelOrA2(relPath, proteins)
    return proteins, triggers, events, relations

def loadSet(dir, setName=None):
    ids = set()
    documents = []
    for filename in os.listdir(dir):
        if filename.find("tar.gz") != -1:
            continue
        if filename.find(".") != -1:
            splits = filename.split(".")
            ids.add(splits[0])
    for id in sorted(list(ids)):
        #print "Loading", id
        doc = Document()
        doc.id = id
        doc.proteins, doc.triggers, doc.events, doc.relations = load(str(id), dir)
        doc.text = loadText( os.path.join(dir, str(id) + ".txt") )
        doc.dataSet = setName
        documents.append(doc)
    return documents

def writeSet(documents, dir, resultFileTag="a2"):
    for doc in documents:
        write(doc.id, dir, doc.proteins, doc.triggers, doc.events, doc.relations, resultFileTag)
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
            elif ann.trigger != None:
                ann.id = "E" + str(idCount)
            else:
                ann.id = "R" + str(idCount)
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
        if trigger == None:
            out.write(event.type)
        else:
            out.write(trigger.type + ":" + trigger.id)
        typeCounts = {}
        # Count arguments
        targetProteins = set()
        for arg in event.arguments:
            argType = arg[0]
            if argType == "Target":
                targetProteins.add(arg[1].id)
            else:
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
            if argType == "Target":
                continue
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
            if argType == "Target":
                continue
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
        
        # Write Coref targets
        if len(targetProteins) > 0:
            out.write("\t[" + ", ".join(sorted(list(targetProteins))) + "]" ) 
        
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

def write(id, dir, proteins, triggers, events, relations, resultFileTag="a2"):
    id = str(id)
    if not os.path.exists(dir):
        os.makedirs(dir)
    if proteins != None:
        out = open(os.path.join(dir, id + ".a1"), "wt")
        writeTAnnotation(proteins, out)
        out.close()
    resultFile = open(os.path.join(dir, id + "." + resultFileTag), "wt")
    writeTAnnotation(triggers, resultFile, getMaxId(proteins) + 1)
    if events != None:
        writeEvents(events, resultFile)
    if relations != None:
        writeEvents(relations, resultFile)
    resultFile.close()
        
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
    





