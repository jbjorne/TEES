import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source")
from Utils.ProgressCounter import ProgressCounter
import Range
from optparse import OptionParser

def getGeniaFileNames(path):
    allNames = os.listdir(path)
    fileNames = []
    for name in allNames:
        if os.path.isfile(os.path.join(path,name)):
            isGeniaDocument = True
            try:
                int(name.split(".")[0])
            except ValueError:
                isGeniaDocument = False
            if isGeniaDocument:
                fileNames.append(name)
    return sorted(fileNames)

def compareDirectories(options):
    inputFiles = getGeniaFileNames(options.input)
    outputFiles = getGeniaFileNames(options.output)
    
    documentMap = {}
    for inputFile in inputFiles:
        documentNumber = int(inputFile.split(".",1)[0])
        if not documentMap.has_key(documentNumber):
            documentMap[documentNumber] = []
        documentMap[documentNumber].append(inputFile)
    compareDocuments(documentMap, outputFiles, options)

def addStat(stats, extension, category):
    if not stats.has_key(extension):
        stats[extension] = [0,0,0,0]
    if category == "source":
        stats[extension][0] += 1
    elif category == "target":
        stats[extension][1] += 1
    elif category == "identical":
        stats[extension][2] += 1
    elif category == "different":
        stats[extension][3] += 1
    else:
        assert(False)

def compareDocuments(documentMap, targetFiles, options):
    documentIds = sorted(documentMap.keys())
    counter = ProgressCounter(len(documentIds))
    stats = {}
    eventStats = {"Start Events":0, 
                  "End Events":0,
                  "False Positive Trigger":0,
                  "Cause FN":0,
                  "Cause FP":0,
                  "Theme FN":0,
                  "Theme FP":0}
    for docId in documentIds:
        counter.update(1, "Processing: ")# document " + str(docId) + ": " )
        for fileName in sorted(documentMap[docId]):
            extension = fileName.split(".",1)[-1]
            addStat(stats, extension, "source")
            if os.path.exists(os.path.join(options.output, fileName)):
                addStat(stats, extension, "target")
                if extension == "txt" or extension == "a1":
                    if compareByLine(fileName, options):
                        addStat(stats, extension, "identical")
                    else:
                        addStat(stats, extension, "different")
                        if options.verbose: print >> sys.stderr, " ...in comparing", fileName
                elif extension == "a2.t1":
                    if compareA2T1Files(fileName, options, eventStats):
                        addStat(stats, extension, "identical")
                    else:
                        addStat(stats, extension, "different")
                        if options.verbose: print >> sys.stderr, " ...in comparing", fileName
    print >> sys.stderr, "Files (source, target, identical, different):"
    for key in sorted(stats.keys()):
        print >> sys.stderr, " " + key + ":" + (10-len(key)) * " " + "\t",
        for value in stats[key]:
            print >> sys.stderr, "\t" + str(value),
        print >> sys.stderr
    print >> sys.stderr, "Event stats:"
    for key in sorted(eventStats.keys()):
        print >> sys.stderr, " " + key + ": " + str(eventStats[key])
    print >> sys.stderr, "Event extraction:"
    eventsSource = eventStats["Start Events"]
    events0 = 0
    if eventStats.has_key("Error Level 0"):
        events0 = eventStats["Error Level 0"]
    print >> sys.stderr, " Exact:", events0, "/", eventsSource, "(%.2f" % (100.0 * events0 / eventsSource) + " %)"

def getFiles(filename, options):
    sourceFile = open(os.path.join(options.input, filename),"rt")
    targetFile = open(os.path.join(options.output, filename),"rt")
    return sourceFile, targetFile

def compareByLine(filename, options):
    sourceFile, targetFile = getFiles(filename, options)
    sourceLines = sourceFile.readlines()
    targetLines = targetFile.readlines()
    identical = True
    if len(sourceLines) != len(targetLines):
        if options.verbose: print >> sys.stderr, "  Source has", len(sourceLines), "lines, target", len(targetLines)
        identical = False
    if identical:
        for i in range(len(sourceLines)):
            if sourceLines[i] != targetLines[i]:
                if options.verbose:
                    print >> sys.stderr, "  Lines differ:"
                    print >> sys.stderr, "   " + sourceLines[i].strip()
                    print >> sys.stderr, "   " + targetLines[i].strip()
                identical = False
    sourceFile.close()
    targetFile.close()
    return identical

def compareA2T1Files(filename, options, eventStats):
    sourceFile, targetFile = getFiles(filename, options)
    sourceLines = sourceFile.readlines()
    targetLines = targetFile.readlines()
    identical = True
    
    triggerMap = mapTriggers(sourceLines, targetLines, options)
    for v in triggerMap.values():
        if v == None:
            identical = False
    i2 = compareEvents(sourceLines, targetLines, triggerMap, eventStats, options)
    identical = i2 and identical
    
    sourceFile.close()
    targetFile.close()
    return identical

def readEvent(eventLine):
    event = {}
    splits = eventLine.split()
    event["id"] = splits[0]
    event["trigger"] = splits[1].split(":")
    event["Theme"] = []
    event["Cause"] = []
    for participant in splits[2:]:
        participantSplits = participant.split(":")
        if participantSplits[0][0:5] == "Theme":
            participantSplits[0] = "Theme"
        elif participantSplits[0][0:5] == "Cause":
            participantSplits[0] = "Cause"
        assert(participantSplits[0] == "Theme" or participantSplits[0] == "Cause")
        event[participantSplits[0]].append(participantSplits[1])
    return event        

def compareEvents(sourceLines, targetLines, triggerMap, eventStats, options):
    identical = True
    sourceEvents = []
    for sourceLine in sourceLines:
        if sourceLine[0] != "E":
            continue
        sourceEvents.append(readEvent(sourceLine))
    eventStats["Start Events"] += len(sourceEvents)
    
    targetEvents = []
    for targetLine in targetLines:
        if targetLine[0] != "E":
            continue
        targetEvents.append(readEvent(targetLine))
    eventStats["End Events"] += len(targetEvents)
    
    eventMap = {}
    eventErrorLevels = {}
    eventsFound = 1
    while eventsFound > 0:
        localEventStats = None
        localEventStats = {"False Positive Trigger":0,
                  "Cause FN":0,
                  "Cause FP":0,
                  "Theme FN":0,
                  "Theme FP":0}
        eventsFound = 0
        for targetEvent in targetEvents:
            if triggerMap[targetEvent["trigger"][1]] == None:
                localEventStats["False Positive Trigger"] += 1
                eventErrorLevels[targetEvent["id"]] = "False Positive Trigger"
            else:
                found = False
                bestMatch = None
                bestMatchErrorCount = 99999999999999
                for sourceEvent in sourceEvents:
                    errorCount = 0
                    if triggerMap[targetEvent["trigger"][1]] != sourceEvent["trigger"][1]:
                        continue
                    found = True
                    
                    count = 0
                    for cause in targetEvent["Cause"]:
                        if cause[0] == "E":
                            if ((not eventMap.has_key(cause)) or not eventMap[cause] in sourceEvent["Cause"]):
                                errorCount += 1
                                localEventStats["Theme FP"] += 1
                            else:
                                count += 1
                        elif not triggerMap[cause] in sourceEvent["Cause"]:
                            errorCount += 1
                            localEventStats["Cause FP"] += 1
                        else:
                            count += 1
                    errorCount += len(sourceEvent["Cause"]) - count
                    localEventStats["Cause FN"] += len(sourceEvent["Cause"]) - count
                    
                    count = 0
                    for theme in targetEvent["Theme"]:
                        if theme[0] == "E":
                            if ((not eventMap.has_key(theme)) or not eventMap[theme] in sourceEvent["Theme"]):
                                errorCount += 1
                                localEventStats["Theme FP"] += 1
                            else:
                                count += 1
                        elif not triggerMap[theme] in sourceEvent["Theme"]:
                            errorCount += 1
                            localEventStats["Theme FP"] += 1
                        else:
                            count += 1
                    errorCount += len(sourceEvent["Theme"]) - count
                    localEventStats["Theme FN"] += len(sourceEvent["Theme"]) - count
                    
                    if bestMatchErrorCount > errorCount:
                        bestMatch = sourceEvent
                        bestMatchErrorCount = errorCount
                assert(found)
                if (not eventMap.has_key(targetEvent["id"])) or eventMap[targetEvent["id"]] != bestMatch["id"]:
                    eventsFound += 1
                eventMap[targetEvent["id"]] = bestMatch["id"]
                if not localEventStats.has_key("Error Level " + str(bestMatchErrorCount)):
                    localEventStats["Error Level " + str(bestMatchErrorCount)] = 0
                localEventStats["Error Level " + str(bestMatchErrorCount)] += 1
                eventErrorLevels[targetEvent["id"]] = bestMatchErrorCount
    
    for k in sorted(eventErrorLevels.keys()):
        v = eventErrorLevels[k]
        if v != 0:
            identical = False
            if options.verbose:
                print >> sys.stderr, "  Event", k, "error level", str(v)
    
    for k in localEventStats.keys():
        if not eventStats.has_key(k):
            eventStats[k] = 0
        eventStats[k] += localEventStats[k]
    return identical

def mapTriggers(sourceLines, targetLines, options):
    sourceSplits = []
    triggerMap = {}
    firstTriggerLine = True
    for sourceLine in sourceLines:
        if sourceLine[0] != "T":
            continue
        sourceSplit = sourceLine.split()
        if firstTriggerLine:
            for i in range(1,int(sourceSplit[0][1:])):
                triggerMap["T"+str(i)] = "T"+str(i)
            firstTriggerLine = False
        sourceSplits.append(sourceSplit)
    
    matchTypes = {}
    for targetLine in targetLines:
        if targetLine[0] != "T":
            continue
        splits = targetLine.split()
        triggerMap[splits[0]] = None
        targetOffset = (int(splits[2]), int(splits[3]))
        for i in range(len(sourceSplits)):
            if splits[1] == sourceSplits[i][1]:
                sourceOffset = (int(sourceSplits[i][2]), int(sourceSplits[i][3]))
                if Range.overlap(sourceOffset, targetOffset):
                    matchType = "overlap"
                    if sourceOffset == targetOffset:
                        matchType = "exact"

                    if triggerMap[splits[0]] == None or (matchTypes[splits[0]] == "overlap" and matchType == "exact"):
                        triggerMap[splits[0]] = sourceSplits[i][0]
                        matchTypes[splits[0]] = matchType
                        
        if triggerMap[splits[0]] == None:
            if options.verbose:
                print >> sys.stderr, "  Trigger not found:", splits[0]
    return triggerMap
        
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nConvert interaction XML to GENIA shared task format.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="interaction xml input file", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-v", "--verbose", dest="verbose", default=False, help="Verbose output.", action="store_true")
    (options, args) = optparser.parse_args()
    
    assert(options.input != None and os.path.exists(options.input) and os.path.isdir(options.input))
    assert(options.output != None and os.path.exists(options.output) and os.path.isdir(options.output))
    
    compareDirectories(options)
