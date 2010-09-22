import sys, os, shutil
import Statistics.stats as stats

def getTrigger(line):
    id, s = line.split("\t")
    classDict = {}
    for pair in s.split(","):
        cls, confidence = pair.split(":")
        classDict[cls] = float(confidence)
    return [id, classDict, None, None, None]

def addData(file, triggers, events):
    for t in zip(file.readlines(), triggers + events):
        line = t[0]
        line = line.strip()
        splits = line.split("\t")
        id = splits[0]
        assert t[1][0] == id
        if id[0] == "T":
            tType, offset = splits[1].split(" ", 1)
            t[1][2] = tType
            t[1][3] = offset
            t[1][4] = splits[2] # word
        else:
            assert id[0] == "E"
            args = splits[1].split(" ")
            t[1][2] = args[0].split(":")
            t[1][3] = []
            for arg in args[1:]:
                t[1][3].append(arg.split(":"))

def getEvent(line):
    id, s = line.split("\t")
    classDicts = []
    for arg in s.split(" "):
        argType, pairs = arg.split("=")
        while argType[-1].isdigit():
            argType = argType[:-1]
        classDicts.append( (argType, {}) )
        for pair in pairs.split(","):
            cls, confidence = pair.split(":")
            classDicts[-1][1][cls] = float(confidence)
    return [id, classDicts, None, None]

def normalize(value, range):
    return (value - range[0]) / (range[1] - range[0])

#def test(triggers, events, f):
#    for t in triggers:
#        f.write(t[0] + "\t")
#        highest = -9999999
#        selected = None
#        for key in t[1]:
#            if t[key] > highest:
#                highest = t[key]
#                selected = key
#        f.write 

def getRanges(triggers, events):
    tValues = set()
    for l in triggers.values():
        for t in l:
            tValues.add(t[1][t[2]])
    eValues = set()
    for l in events.values():
        for e in l:
            for arg in e[1]:
                eValues.add(arg[1][arg[0]])
    return (min(tValues), max(tValues)), (min(eValues), max(eValues))

def getScores(event, triggerMap, ranges):
    scores = []
    trigger = triggerMap[ event[2][1] ]
    tScore = normalize(trigger[1][trigger[2]], ranges[0])
    assert tScore >= 0.0 and tScore <= 1.0, tScore
    scores.append(tScore)
    for arg in event[1]:
        argScore = normalize(arg[1][arg[0]], ranges[1])
        assert argScore >= 0.0 and argScore <= 1.0, argScore
        scores.append(argScore)
    return scores

def averageScore(event, triggerMap, ranges):
    scores = getScores(event, triggerMap, ranges)
    return sum(scores, 0.0) / len(scores)

def medianScore(event, triggerMap, ranges):
    scores = getScores(event, triggerMap, ranges)
    return stats.lmedianscore(scores)

def averageArgs(event, triggerMap, ranges):
    scores = getScores(event, triggerMap, ranges)[1:]
    return sum(scores, 0.0) / len(scores)

def medianArgs(event, triggerMap, ranges):
    scores = getScores(event, triggerMap, ranges)
    return stats.lmedianscore(scores[1:])

def dummy(event, triggerMap, ranges):
    return 1

def writeOut(allTriggers, allEvents, ranges, outDir, selectFunction, threshold):
    for fileId in sorted(allTriggers.keys()):
        triggers = allTriggers[fileId]
        events = allEvents[fileId]
        
        triggerMap = {}
        for trigger in triggers:
            triggerMap[trigger[0]] = trigger
        
        f = open( os.path.join(outDir, fileId + ".a2.t1"), "wt" )
        for trigger in triggers:
            f.write(trigger[0] + "\t" )
            f.write(trigger[2] + " ")
            f.write(trigger[3] + "\t")
            f.write(trigger[4] + "\n")
        for event in events:
            score = selectFunction(event, triggerMap, ranges)
            assert score >= 0.0 and score <= 1.0, score
            if score >= threshold:
                f.write(event[0] + "\t")
                f.write(":".join(event[2]))
                for arg in event[3]:
                    f.write(" " + ":".join(arg))
                f.write("\n")
        f.close()

def process(sourceDir, outDir):
    allTriggers = {}
    allEvents = {}
            
    filenames = os.listdir(sourceDir)
    for filename in filenames:
        if filename.find(".scores") != -1:
            id = filename.split(".")[0]
            triggers = []
            events = []
            
            f = open(os.path.join(sourceDir,filename), "rt")
            for line in f.readlines():
                line = line.strip()
                if line[0] == "T":
                    triggers.append(getTrigger(line))
                elif line[0] == "E":
                    events.append(getEvent(line))
            f.close()
            
            f = open(os.path.join(sourceDir,filename.rsplit(".", 1)[0]), "rt")
            addData(f, triggers, events)
            f.close()
            
            allTriggers[id] = triggers
            allEvents[id] = events
    ranges = getRanges(allTriggers, allEvents)
    print ranges
    writeOut(allTriggers, allEvents, ranges, outDir, averageArgs, 0.3)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    sourceDir = "/home/jari/data/temp/BioNLP09Classify/geniaformat"
    outDir = "/home/jari/data/temp/BioNLP09Classify/geniaformat-modified"
    if os.path.exists(outDir):
        shutil.rmtree(outDir)
    os.mkdir(outDir)
    
    process(sourceDir, outDir)
    