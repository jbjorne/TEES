import sys, os
import codecs
import Validate

#def compareOffsets(a, b):
#    if a.charBegin != b.charBegin:
#        if a.charBegin < b.charBegin:
#            return -1
#        else:
#            return 1
#    else:
#        if a.charEnd < b.charEnd:
#            return -1
#        elif a.charEnd == b.charEnd:
#            return 0
#        else:
#            return 1
#    return 0 

class Document:
    def __init__(self):
        self.id = None
        self.text = None
        self.proteins = []
        self.triggers = []
        self.events = []
        self.relations = []
        self.dataSet = None

class Annotation:
    def __init__(self, id = None, type = None, text=None, trigger=None, arguments=None):
        self.id = id # protein/word/dependency/trigger/event
        self.type = type # protein/word/dependency/trigger/event
        self.text = text # protein/word/trigger
        self.charBegin = -1 # protein/word/trigger
        self.charEnd = -1 # protein/word/trigger
        self.alternativeOffsets = []
        self.equiv = [] # group of elements that are equivalent
        self.trigger = trigger # event
        self.arguments = [] # event/dependency/relation
        if arguments != None:
            self.arguments = arguments
        self.sites = []
        self.speculation = None # event 
        self.negation = None # event
        self.fileType = None # "a1" or "a2"
        # Optional confidence scores
        self.triggerScores = None
        self.unmergingScores = None
        self.speculationScores = None
        self.negationScores = None
    
    def isNegated(self):
        return self.negation != None
    
    def isSpeculative(self):
        return self.speculation != None
    
    def isName(self):
        return self.type == "Protein" or self.type == "Gene"

    # for debugging
    def __repr__(self):
        if self.id == None:
            return "<Ann NO-ID>"
        else:
            return "<Ann " + self.id + ">"

def getStatistics(documents, printStats=True, statSeparator="\n"):
    from collections import defaultdict
    import types
    if type(documents) in types.StringTypes:
        documents = loadSet(documents)
    
    stats = defaultdict(int)
    for document in documents:
        stats["total-docs"] += 1
        stats["total-events"] += len(document.events)
        stats["total-relations"] += len(document.relations)
        stats["total-proteins"] += len(document.proteins)
        stats["doc-events-"+str(len(document.events))] += 1
        stats["doc-relations-"+str(len(document.relations))] += 1
        stats["doc-proteins-"+str(len(document.proteins))] += 1
        for event in document.events:
            stats["events-"+event.type] += 1
            if event.speculation != None:
                stats["events-"+event.type+"-spec"] += 1
            if event.negation != None:
                stats["events-"+event.type+"-neg"] += 1
            argStats = defaultdict(int)
            nesting = False
            for arg in event.arguments:
                argType = arg[0]
                if arg[2] != None:
                    argType += "(" + arg[2].type + ")"
                if not arg[1].isName():
                    nesting = True
                argStats[argType] += 1
            if nesting:
                stats["events-"+event.type+"-parent"] += 1
            stats["args-"+event.type+"-"+"-".join([str(key)+"_"+str(argStats[key]) for key in sorted(argStats.keys())]) ] += 1
    if printStats:
        print >> sys.stderr, "Event Statistics:"
        print >> sys.stderr, statSeparator.join([str(key)+":"+str(stats[key]) for key in sorted(stats.keys())])
    return stats

def readTAnnotation(string, readScores=False):
    #print string
    assert string[0] == "T" or string[0] == "W", string
    string = string.strip()
    ann = Annotation()
    splits = string.split("\t")
    ann.id = splits[0]
    middle = splits[1]
    ann.text = splits[2]
    if readScores:
        ann.triggerScores = splits[3]
    #ann.id, middle, ann.text = string.split("\t")
    ann.type, ann.charBegin, ann.charEnd = middle.split()
    ann.charBegin = int(ann.charBegin)
    ann.charEnd = int(ann.charEnd)
    # TODO disabled temporarily
#    if len(splits) > 3:
#        skip = False
#        for split in splits[3:]:
#            if not skip:
#                cSplits = split.split()
#                assert len(cSplits) == 2, (cSplits, string)
#                c1 = int(cSplits[0])
#                c2 = int(cSplits[1])
#                ann.alternativeOffsets.append( (c1, c2) )
#            skip = not skip
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

def readEvent(string, sitesAreArguments=False, readScores=False):
    string = string.strip()
    ann = Annotation()
    ann.id, rest = string.split("\t")
    args = rest.split()
    trigger = args[0]
    args = args[1:]
    splits = trigger.split(":")
    ann.type = splits[0]
    ann.trigger = None
    if len(splits) > 1:
        if "=" not in splits[1]:
            ann.trigger = splits[1]
        elif readScores:
            ann.unmergingScores = splits[1]
        if len(splits) > 2 and readScores:
            assert "=" in splits[2]
            ann.unmergingScores = splits[2]
#    if len(splits) == 2: # (splits, trigger, string)
#        ann.type, ann.trigger = splits[0], splits[1]
#    else:
#        ann.type = splits[0]
#        ann.trigger = None
    argMap = {}
    #print string
    for arg in args:
        argTuple = arg.split(":")
        argScores = []
        if len(argTuple) > 2:
            if readScores:
                argScores = argTuple[2:]
            argTuple = argTuple[:2]
        argTuple += [None] + argScores + [None] # room for the site
        # In the Shared Task Annotation, the word Site can mean a site, or then again not, 
        # because the same term Site is used also for a Site that is not a Site, but just
        # a "Site"-type argument for a SiteOf event in the BI-task, which may, or may not 
        # (didn't check), have also actual Sites.
        if sitesAreArguments or argTuple[0].find("Site") == -1 or ann.type == "SiteOf": # not a site or SiteOf-type event
            origArgName = argTuple[0]
            if argTuple[0].find("Theme") != -1: # multiple themes are numbered
                argTuple[0] = "Theme" #["Theme", argTuple[1], None]
            assert origArgName != "" # extra whitespace caused errors with splitting, splitting fixed
            argMap[origArgName] = argTuple
            ann.arguments.append( argTuple )
            if "Site" in argTuple[0]:
                assert argTuple[0] == "Site"
                argTuple[0] = "SiteArg"
    #print argMap
    if len(argMap.keys()) != len(args): # We have sites
        for arg in args:
            argTuple = arg.split(":")
            if "Site" in argTuple[0]:
                if argTuple[0] == "CSite":
                    target = "Cause"
                else:
                    target = "Theme" + argTuple[0][4:]
                if target not in argMap: # a single theme is not numbered
                    assert "Theme" in target
                    assert "Theme" in argMap
                    target = "Theme"
                argMap[target][2] = argTuple[1]
                if readScores and len(argTuple) > 2:
                    argMap[target][4] = argTuple[2] 
    return ann

def readRAnnotation(string, readScores=False):
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
        argTuple = arg.split(":")
        #assert argTuple[0].find("Arg") != -1, (string, argTuple)
        if readScores and len(argTuple) > 2:
            ann.arguments.append( [argTuple[0], argTuple[1], None, argTuple[2], None] )
        else:
            ann.arguments.append( [argTuple[0], argTuple[1], None] )
    if len(tabSplits) == 3:
        assert ann.type == "Coref"
        assert tabSplits[2][0] == "[" and tabSplits[2][-1] == "]", (string, tabSplits)
        protIds = tabSplits[2][1:-1].split(",")
        for protId in protIds:
            ann.arguments.append( ["Connected", protId.strip(), None] )
    return ann

def readDependencyAnnotation(string):
    string = string.strip()
    id, depType, word1, word2 = string.split()
    assert word1[0] == "W" and word2[0] == "W", string
    ann = Annotation()
    ann.id = id
    ann.type = depType
    ann.arguments = [("Word", word1), ("Word", word2)]
    return ann

def loadA1(filename):
    #f = open(filename)
    f = codecs.open(filename, "rt", "utf-8")
    proteins = []
    words = []
    dependencies = []
    lines = f.readlines()
    count = 0
    for line in lines:
        if line[0] == "T":
            proteins.append(readTAnnotation(line))
            count += 1
    for line in lines:
        if line[0] == "*":
            readStarAnnotation(line, proteins)
            count += 1
    for line in lines:
        if line[0] == "W":
            words.append(readTAnnotation(line))
            count += 1
    for line in lines:
        if line[0] == "R": # in a1-files, "R" refers to dependencies
            dependencies.append(readDependencyAnnotation(line))
            count += 1
    assert count == len(lines), lines # check that all lines were processed
    f.close()
    # Mark source file type
    for ann in proteins + words + dependencies:
        ann.fileType = "a1"
    # Build syntactic links
    if len(words) > 0:
        wordMap = {}
        for word in words:
            wordMap[word.id] = word
        for dep in dependencies:
            for i in range(len(dep.arguments)):
                arg = dep.arguments[i]
                dep.arguments[i] = (arg[0], wordMap[arg[1]])
    return proteins, words, dependencies

def loadRelOrA2(filename, proteins, sitesAreArguments=False, readScores=False):
    if readScores and os.path.exists(filename + ".scores"):
        #f = open(filename + ".scores", "rt")
        f = codecs.open(filename + ".scores", "rt", "utf-8")
    else:
        #f = open(filename, "rt")
        f = codecs.open(filename, "rt", "utf-8")
    triggers = []
    triggerMap = {}
    for protein in proteins:
        triggerMap[protein.id] = protein
    events = []
    eventMap = {}
    relations = []
    lines = f.readlines()
    f.close()
    count = 0
    for line in lines:
        if line[0] == "T":
            triggers.append( readTAnnotation(line, readScores=readScores) )
            triggerMap[triggers[-1].id] = triggers[-1]
            count += 1
    for line in lines:
        if line[0] == "E":
            events.append( readEvent(line, sitesAreArguments, readScores=readScores) )
            eventMap[events[-1].id] = events[-1]
            count += 1
    for line in lines:
        if line[0] == "R":
            relations.append(readRAnnotation(line, readScores=readScores))
            # NOTE: Temporarily treating relations as events to get equiv-resolution
            # working
            #events.append(readRAnnotation(line))
            count += 1
    for line in lines:
        if line[0] == "M":
            if not readScores:
                mId, rest = line.strip().split("\t")
                mScore = None
            else:
                mId, rest, mScore = line.strip().split("\t")
            mType, eventId = rest.split()
            assert mType in ["Speculation", "Negation"]
            if mType == "Speculation":
                eventMap[eventId].speculation = mId
                eventMap[eventId].speculationScores = mScore
            elif mType == "Negation":
                eventMap[eventId].negation = mId
                eventMap[eventId].negationScores = mScore
            count += 1
    for line in lines:
        if line[0] == "*":
            readStarAnnotation(line, proteins + triggers)
            count += 1
    assert count == len(lines), lines # check that all lines were processed
    
    # Mark source file type
    for ann in triggers + events + relations:
        ann.fileType = "a2"
    # Build links
    for event in events:
        #print event.id
        if event.trigger != None:
            event.trigger = triggerMap[event.trigger]
            # Move scores from event to trigger
            event.trigger.unmergingScores = event.unmergingScores
            event.trigger.negationScores = event.negationScores
            event.trigger.speculationScores = event.speculationScores
            event.unmergingScores = None
            event.negationScores = None
            event.speculationScores = None
            
        for i in range(len(event.arguments)):
            arg = event.arguments[i]
            if arg[1][0] == "T":
                if arg[2] != None:
                    #event.arguments[i] = (arg[0], triggerMap[arg[1]], triggerMap[arg[2]])
                    event.arguments[i][1] = triggerMap[arg[1]]
                    event.arguments[i][2] = triggerMap[arg[2]]
                else:
                    #event.arguments[i] = (arg[0], triggerMap[arg[1]], None)
                    event.arguments[i][1] = triggerMap[arg[1]]
            elif arg[1][0] == "E":
                assert arg[2] == None # no sites on events
                #event.arguments[i] = (arg[0], eventMap[arg[1]], None)
                event.arguments[i][1] = eventMap[arg[1]]
    # Build links
    for relation in relations:
        for i in range(len(relation.arguments)):
            arg = relation.arguments[i]
            if arg[1][0] == "T":
                if arg[2] != None:
                    #relation.arguments[i] = (arg[0], triggerMap[arg[1]], triggerMap[arg[2]])
                    relation.arguments[i][1] = triggerMap[arg[1]]
                    relation.arguments[i][2] = triggerMap[arg[2]]
                else:
#                    if not triggerMap.has_key(arg[1]): # NOTE! hack for CO bugs
#                        relation.arguments = relation.arguments[0:i]
#                        if len(relation.arguments) == 1: # NOTE! hack
#                            relations = []
#                        break
                    #relation.arguments[i] = (arg[0], triggerMap[arg[1]], None)
                    relation.arguments[i][1] = triggerMap[arg[1]]

    return triggers, events, relations

def loadText(filename):
    #f = open(filename)
    f = codecs.open(filename, "rt", "utf-8")
    text = f.read()
    f.close()
    return text

def load(id, dir, loadA2=True, sitesAreArguments=False, a2Tag="a2", readScores=False):
    #print id
    id = str(id)
    a1Path = os.path.join(dir, id + ".a1")
    if os.path.exists(a1Path):
        proteins, words, dependencies = loadA1(a1Path)
    else:
        proteins = []
        words = []
        dependencies = []
    if not loadA2:
        return proteins, [], [], [], [], []
    a2Path = os.path.join(dir, id + "." + a2Tag)
    relPath = os.path.join(dir, id + ".rel")
    triggers = []
    events = []
    relations = []
    if os.path.exists(a2Path):
        triggers, events, relations = loadRelOrA2(a2Path, proteins, sitesAreArguments, readScores=readScores)
    elif os.path.exists(relPath):
        triggers, events, relations = loadRelOrA2(relPath, proteins, sitesAreArguments, readScores=readScores)
    return proteins, words, dependencies, triggers, events, relations

def loadSet(path, setName=None, level="a2", sitesAreArguments=False, a2Tag="a2", readScores=False):
    assert level in ["txt", "a1", "a2"]
    if path.endswith(".tar.gz"):
        import tempfile
        import tarfile
        import shutil
        dir = tempfile.mkdtemp()
        f = tarfile.open(path, "r")
        f.extractall(dir)
        f.close()
    else:
        dir = path
    
    ids = set()
    documents = []
    for filename in os.listdir(dir):
        if filename.endswith(".txt"):
            ids.add(filename.split(".")[0])
    for id in sorted(list(ids)):
        #print "Loading", id
        doc = Document()
        doc.id = id
        if not level == "txt":
            try:
                doc.proteins, doc.words, doc.dependencies, doc.triggers, doc.events, doc.relations = load(str(id), dir, level=="a2", sitesAreArguments, a2Tag=a2Tag, readScores=readScores)
            except:
                print >> sys.stderr, "Exception reading document", id, "from", dir 
                raise
        doc.text = loadText( os.path.join(dir, str(id) + ".txt") )
        doc.dataSet = setName
        documents.append(doc)
    
    if dir != path:
        shutil.rmtree(dir)
    return documents

def writeSet(documents, output, resultFileTag="a2", debug=False, task=2, validate=True, writeScores=False):
    from collections import defaultdict
    import shutil
    counts = defaultdict(int)
    
    while output.endswith("/"):
        output = output[:-1]
    if output.endswith(".tar.gz"):
        outdir = output + "-temp"
    else:
        outdir = output
    if os.path.exists(outdir):
        shutil.rmtree(outdir)

    if not validate:
        print "Warning! No validation."
    for doc in documents:
        if validate:
            if debug: print >> sys.stderr, "Validating", doc.id
            Validate.allValidate(doc, counts, task, verbose=debug)
        #doc.proteins.sort(cmp=compareOffsets)
        #doc.triggers.sort(cmp=compareOffsets)
        if debug: print >> sys.stderr, "Writing", doc.id
        write(doc.id, outdir, doc.proteins, doc.triggers, doc.events, doc.relations, resultFileTag, counts, task=task, writeScores=writeScores)
        # Write text file
        #out = open(os.path.join(outdir, str(doc.id) + ".txt"), "wt")
        out = codecs.open(os.path.join(outdir, str(doc.id) + ".txt"), "wt", "utf-8")
        out.write(doc.text)
        out.close()
    if output.endswith(".tar.gz"):
        package(outdir, output, ["a1", "txt", resultFileTag, resultFileTag+".scores"])
        shutil.rmtree(outdir)
    print counts
        

def getMaxId(annotations):
    nums = [0]
    for annotation in annotations:
        if annotation.id != None:
            assert annotation.id[1:].isdigit(), annotation.id
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
            if len(ann.arguments) == 0 and ann.trigger == None:
                ann.id = "T" + str(idCount)
            elif ann.type in ["Subunit-Complex", "Protein-Component", "Coref", "Renaming", "SR-subunitof", "SR-equivto", "SR-partof", "SR-memberof"]:
                ann.id = "R" + str(idCount)
            #elif ann.trigger != None or ann.type in ["ActionTarget", "Interaction", "TranscriptionBy", ""]:
            else:
                ann.id = "E" + str(idCount)
            idCount += 1

def writeTAnnotation(proteins, out, writeScores, idStart=0):
    updateIds(proteins, idStart)
    for protein in proteins:
        assert protein.id[0] == "T", (protein.id, protein.text)
        out.write(protein.id + "\t")
        out.write(protein.type + " " + str(protein.charBegin) + " " + str(protein.charEnd) + "\t")
        if protein.text == None:
            out.write(str(protein.text))
        else:
            out.write(protein.text.replace("\n", "&#10;").replace("\r", "&#10;"))
        if writeScores and protein.triggerScores != None:
            out.write("\t" + protein.triggerScores.replace(":", "="))
        out.write("\n")

def getDuplicatesMapping(eventLines):
    # Duplicates are BAAADD. However, removing nested duplicates is also BAAADDD. Evaluation system doesn't like
    # either. So, if you don't remove duplicates, it refuses to evaluate because of duplicates. If you do remove
    # duplicates, it refuses to evaluate because of missing events. That's why they ARE THERE, how can they
    # be duplicates, IF THEY ARE PART OF DIFFERENT NESTING CHAINS??? The "solution" is to remap nesting events
    # to removed duplicates.
    duplicateMap = {}
    seenLineMap = {}
    for eventLineTuple in eventLines:
        if eventLineTuple[1] not in seenLineMap:
            seenLineMap[eventLineTuple[1]] = eventLineTuple[0]
        else:
            duplicateMap[eventLineTuple[0]] = seenLineMap[eventLineTuple[1]]
    return duplicateMap

#def removeDuplicates():
#    for e1 in events[:]:
#        for e2 in events[:]:
#            if e1 == e2:
#                continue
#            if e1.trigger == e2.trigger and len(e1.arguments) == len(e2.arguments):
#                for arg1 in zip(e1.arguments, e2.arguments)

def writeEvents(events, out, counts, task, writeScores=False):
    updateIds(events)
    mCounter = 1
    eventLines = []
    nestedEvents = set()
    for event in events:
        eventLine = ""
        #out.write(event.id + "\t")
        # Event id part ############################
        trigger = event.trigger
        if trigger == None:
            eventLine += event.type
        else:
            eventLine += trigger.type + ":" + trigger.id
            if writeScores and event.trigger.unmergingScores != None:
                eventLine += ":" + event.trigger.unmergingScores.replace(":", "=")
        # Argument part #############################
        typeCounts = {}
        # Count arguments
        targetProteins = set()
        for arg in event.arguments:
            argType = arg[0]
            if argType == "Target" and event.type == "Coref":
                targetProteins.add(arg[1].id)
            else:
                if not typeCounts.has_key(argType):
                    typeCounts[argType] = 0
                typeCounts[argType] += 1
        # Determine which arguments need numbering
        #for key in typeCounts.keys():
        #    if typeCounts[key] <= 1:
        #        del typeCounts[key]
        # Write arguments
        currTypeCounts = {}
        for key in typeCounts.keys():
            currTypeCounts[key] = 0
        for arg in event.arguments:
            argType = arg[0]
            if argType == "Target" and event.type == "Coref":
                continue
            assert arg[1].id != None, (event.id, event.arguments, arg)
            currTypeCounts[argType] += 1
            if typeCounts[argType] > 1:
                eventLine += " " + argType + str(currTypeCounts[argType]) + ":" + arg[1].id
            else:
                eventLine += " " + argType + ":" + arg[1].id
            if writeScores and len(arg) > 3 and arg[3] != None:
                eventLine += ":" + arg[3].replace(":", "=")
            
            # keep track of nesting
            if arg[1].id[0] == "E":
                nestedEvents.add(arg[1].id)
        
        # Reset type counts for writing sites
        currTypeCounts = {}
        for key in typeCounts.keys():
            currTypeCounts[key] = 0
        # Write sites
        for arg in event.arguments:
            if task == 1:
                continue
            
            if arg[2] == None:
                continue
            
            #if arg[2].id in ["T18", "T19"]:
            #    print arg
            #    out.write("XXX")
            #    print event.type
            
            # limit sites to accepted event types
            # Todo! This should be done in validate
            #if event.type not in ["Binding", "Phosphorylation", "Positive_regulation", "Negative_regulation", "Regulation"]:
            #    continue
            
            argType = arg[0]
            if argType == "Target" and event.type == "Coref":
                continue
            currTypeCounts[argType] += 1
            
            sitePrefix = ""
            if argType.find("Cause") != -1:
                sitePrefix = "C"
            if typeCounts[argType] > 1:
                eventLine += " " + sitePrefix + "Site" + str(currTypeCounts[argType]) + ":" + arg[2].id
            else:
                eventLine += " " + sitePrefix + "Site" + ":" + arg[2].id
            if writeScores and len(arg) > 4 and arg[4] != None:
                eventLine += ":" + arg[4].replace(":", "=")
        
        # Write Coref targets
        if len(targetProteins) > 0:
            eventLine += "\t[" + ", ".join(sorted(list(targetProteins))) + "]"
        
        eventLine += "\n"
        

        # Write task 3
        if event.speculation != None:
            eventLine += "M" + str(mCounter) + "\t" + "Speculation " + str(event.id)
            if writeScores and event.trigger != None and event.trigger.speculationScores != None:
                eventLine += "\t" + event.trigger.speculationScores.replace(":", "=")
            eventLine += "\n"
            mCounter += 1
        if event.negation != None:
            eventLine += "M" + str(mCounter) + "\t" + "Negation " + str(event.id)
            if writeScores and event.trigger != None and event.trigger.negationScores != None:
                eventLine += "\t" + event.trigger.negationScores.replace(":", "=")
            eventLine += "\n"
            mCounter += 1
        
        eventLines.append( [event.id, eventLine] )
    
    # Write ignoring duplicates
    #duplicateMap = getDuplicatesMapping(eventLines)
    #seenLines = set()
    for eventLineTuple in eventLines:
        out.write(eventLineTuple[0] + "\t" + eventLineTuple[1])
        
#        if eventLineTuple[1] not in seenLines:
#            eventLine = eventLineTuple[1] + " "
#            for key in sorted(duplicateMap.keys()):
#                eventLine = eventLine.replace(key, duplicateMap[key])
#            out.write(eventLineTuple[0] + "\t" + eventLine)
#            seenLines.add(eventLineTuple[1])
    # Write task 3
    #for event in events:
    #    if event.negation != None:

def write(id, dir, proteins, triggers, events, relations, resultFileTag="a2", counts=None, debug=False, task=2, writeScores=False):
    id = str(id)
    if debug:
        print id
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    #updateIds(proteins)
    #updateIds(triggers, getMaxId(stDoc.proteins) + 1)
    #updateIds(events)
    #updateIds(relations)
    
    if proteins != None:
        out = codecs.open(os.path.join(dir, id + ".a1"), "wt", "utf-8")
        writeTAnnotation(proteins, out, False)
        out.close()
    resultFile = codecs.open(os.path.join(dir, id + "." + resultFileTag), "wt", "utf-8")
    writeTAnnotation(triggers, resultFile, False, getMaxId(proteins) + 1)
    if writeScores:
        resultScoresFile = codecs.open(os.path.join(dir, id + "." + resultFileTag + ".scores"), "wt", "utf-8")
        writeTAnnotation(triggers, resultScoresFile, True, getMaxId(proteins) + 1)
    if len(events) > 0:
        if debug: print >> sys.stderr, "Writing events"
        writeEvents(events, resultFile, counts, task, writeScores=False)
        if writeScores:
            writeEvents(events, resultScoresFile, counts, task, writeScores=True)
    if len(relations) > 0:
        if debug: print >> sys.stderr, "Writing relations"
        writeEvents(relations, resultFile, counts, task)
        if writeScores:
            writeEvents(relations, resultScoresFile, counts, task, writeScores=True)
    resultFile.close()
    if writeScores:
        resultScoresFile.close()

def package(sourceDir, outputFile, includeTags=["a2", "a2.scores"]):
    import tarfile
    allFiles = os.listdir(sourceDir)
    tarFiles = []
    for file in allFiles:
        for tag in includeTags:
            if file.endswith(tag):
                tarFiles.append(file)
                break
    packageFile = tarfile.open(outputFile, "w:gz")
    tempCwd = os.getcwd()
    os.chdir(sourceDir)
    for file in tarFiles:
        packageFile.add(file)#, exclude = lambda x: x == submissionFileName)
    #if "final" in outputFile:
    #    packageFile.add("/home/jari/data/BioNLP11SharedTask/resources/questionnaire.txt", "questionnaire.txt")
    os.chdir(tempCwd)
    packageFile.close()

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
        
    optparser = OptionParser(usage="%prog [options]\nST format input and output.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--outputTag", default="a2", dest="outputTag", help="a2 file extension.")
    optparser.add_option("-s", "--sentences", default=False, action="store_true", dest="sentences", help="Write each sentence to its own document")
    optparser.add_option("-r", "--origIds", default=False, action="store_true", dest="origIds", help="Use stored original ids (can cause problems with duplicates).")
    optparser.add_option("-a", "--task", default=2, type="int", dest="task", help="1 or 2")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="Verbose output.")
    (options, args) = optparser.parse_args()
    
    assert options.input != options.output
    documents = loadSet(options.input, "GE", level="a2", sitesAreArguments=False, a2Tag="a2", readScores=False)
    writeSet(documents, options.output, resultFileTag=options.outputTag, debug=options.debug, task=options.task, validate=True, writeScores=False)
        
#if __name__=="__main__":
#    # Import Psyco if available
#    try:
#        import psyco
#        psyco.full()
#        print >> sys.stderr, "Found Psyco, using"
#    except ImportError:
#        print >> sys.stderr, "Psyco not installed"
#    
#    #proteins, triggers, events = load(1335418, "/home/jari/biotext/tools/TurkuEventExtractionSystem-1.0/data/evaluation-data/evaluation-tools-devel-gold")
#    #write(1335418, "/home/jari/data/temp", proteins, triggers, events )
#    
#    p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
#    documents = loadSet(p)
#    writeSet(documents, "/home/jari/data/temp/testSTTools")
