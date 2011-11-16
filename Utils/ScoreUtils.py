import sys, os, shutil
import Statistics.stats as stats
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath, "../../../../GeniaChallenge")))
import evaluation.EvaluateSharedTask
evaluateSharedTask = evaluation.EvaluateSharedTask.evaluate

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

def causeArgs(event, triggerMap, ranges):
    scores = []
    for arg in event[1]:
        if arg[0] == "Cause":
            argScore = normalize(arg[1][arg[0]], ranges[1])
            assert argScore >= 0.0 and argScore <= 1.0, argScore
            scores.append(argScore)
    if len(scores) == 0:
        scores = [1]
    return sum(scores, 0.0) / len(scores)

def nestedScores():
    pass

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

def process(sourceDir, outDir, function):
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
    
    class Stuff:
        def __init__(self, allTriggers, allEvents, ranges, outDir, function):
            self.allTriggers = allTriggers
            self.allEvents = allEvents
            self.ranges = ranges
            self.outDir = outDir
            self.function = function
    stuff = Stuff(allTriggers, allEvents, ranges, outDir, function)
    writeOut(allTriggers, allEvents, ranges, outDir, function, 0)
    baseline = evaluateSharedTask(outDir, evaluations=["approximate"], silent=True)["approximate"]["ALL-TOTAL"]["fscore"]
    best = search(baseline, 1.0, 0.0, 0.5, 0.01, [0], stuff)
    print "Baseline", baseline
    print "Highest", best
    print "Difference", best[1] - baseline
    return
    
    best = (None, {"approximate":{"ALL-TOTAL":{"fscore":-1}}})
    for i in range(100, -1, -1):
        threshold = float(i/100.0)
        writeOut(allTriggers, allEvents, ranges, outDir, function, threshold)
        result = evaluateSharedTask(outDir, evaluations=["approximate"], silent=True)
        r = result["approximate"]["ALL-TOTAL"]
        print threshold, r["precision"], r["recall"], r["fscore"]
        if r["fscore"] > best[1]["approximate"]["ALL-TOTAL"]["fscore"]:
            best = (threshold, result)
    print "Baseline", result["approximate"]["ALL-TOTAL"]["fscore"]
    print "Highest", best[1]["approximate"]["ALL-TOTAL"]["fscore"]

def search(baseline, top, bottom, middle, threshold, maxIt, stuff):
    maxIt[0] += 1
    p1 = (top - middle) * 0.5 + middle
    p2 = (middle - bottom) * 0.5 + bottom
    writeOut(stuff.allTriggers, stuff.allEvents, stuff.ranges, stuff.outDir, stuff.function, p1)
    p1Value = evaluateSharedTask(outDir, evaluations=["approximate"], silent=True)["approximate"]["ALL-TOTAL"]["fscore"]
    writeOut(stuff.allTriggers, stuff.allEvents, stuff.ranges, stuff.outDir, stuff.function, p2)
    p2Value = evaluateSharedTask(outDir, evaluations=["approximate"], silent=True)["approximate"]["ALL-TOTAL"]["fscore"]
    print "Testing", (p1, p1Value), (p2, p2Value)
    if abs( (p1Value - baseline) - (p2Value - baseline) ) <= threshold:
        print "Threshold reached"
        if p1Value - baseline > p2Value - baseline:
            return p1, p1Value
        else:
            return p2, p2Value
    if p1Value - baseline > p2Value - baseline:
        if maxIt[0] > 100:
            print "Max Iterations"
            return p1, p1Value
        return search(baseline, top, middle, p1, threshold, maxIt, stuff)
    else:
        if maxIt[0] > 100:
            print "Max Iterations"
            return p2, p2Value
        return search(baseline, middle, bottom, p2, threshold, maxIt, stuff)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-f", "--function", default="averageArgs", dest="function", help="")
    #optparser.add_option("-i", "--input", default=None, dest="input", help="input directory with predicted shared task files", metavar="FILE")
    #optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    #optparser.add_option("-v", "--variance", default=0, type="int", dest="variance", help="variance folds")
    (options, args) = optparser.parse_args()
    #assert(options.input != None)
    #assert(options.task in [1,12,13,123])
    print "Testing function", options.function
    function = eval(options.function)
    
    sourceDir = "/home/jari/data/temp/BioNLP09Classify/geniaformat"
    outDir = "/home/jari/data/temp/BioNLP09Classify/geniaformat-modified"
    if os.path.exists(outDir):
        shutil.rmtree(outDir)
    os.mkdir(outDir)
    
    process(sourceDir, outDir, function)
    