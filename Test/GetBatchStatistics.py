import sys, os
from collections import defaultdict
import time

def getSeconds(timeString):
    #print timeString
    hours, minutes, seconds = timeString.strip().split(":")
    seconds = float(seconds)
    seconds += 60 * int(minutes)
    seconds += 3600 * int(hours)
    return seconds

def secondsToString(seconds):
    hours = int(seconds / 3600)
    minutes = int(seconds % 3600) / 60
    seconds = int(seconds % 3600) % 60
    return str(hours) + ":" + str(minutes) + ":" + str(seconds) 

def printValue(key, value):
    if "time" in key:
        print value, "(" + secondsToString(value) + ")"
    else:
        print value

def getLastRun(lines, match):
    for i in range(len(lines)-1, -1, -1):
        if match in lines[i]:
            return lines[i:]

def getCounterTime(line, match):
    if ("100.00 %" in line or "Process timed out (" in line) and match in line:
        timePart = line.split("\t", 1)[-1].split(":", 1)[-1].split(")")[0].split("(")[-1]
        return getSeconds(timePart)
    else:
        return 0.0

def getLastSection(lines, beginMatch, endMatch, skipTriggers=[]):
    searchPos = len(lines)-1
    while True:
        # Search for start position
        currBegin = None
        for i in range(searchPos, -1, -1):
            if beginMatch in lines[i]:
                currBegin = i
                break
        if currBegin == None:
            return None
        searchPos = currBegin - 1 # update to before current block
        #print "BEGIN", lines[currBegin]
        # Search for end position
        currEnd = None
        for i in range(currBegin+1, len(lines)):
            #print lines[i],
            # Check for block-breaking lines
            skip = False
            for skipTrigger in skipTriggers:
                if skipTrigger in lines[i]:
                    skip = True
                    break
            if skip:
                break
            
            if beginMatch in lines[i]: # block doesn't end before another begins
                #print "BEGINMATCH"
                break
            if endMatch in lines[i]:
                #print "MATCH", currBegin
                currEnd = i + 1
                break
            #print "NOT"
        #print (currBegin, currEnd)
        if currBegin != None and currEnd != None:
            assert currBegin < currEnd
            return (currBegin, currEnd)

def getEventStats(lines, stats):
    for line in lines:
        if "total-events:" in line:
            for pair in line.strip().split("\t")[1].split(","):
                key, value = pair.split(":")
                stats["EVENTS-"+key] += int(value)
        # Total time
        if "Total event detection time" in line:
            stats["TOTAL-time"] += getSeconds(line.strip().split("\t")[1].split(":", 1)[1])
            stats["TOTAL-time-events"] += getSeconds(line.strip().split("\t")[1].split(":", 1)[1])
    #getTimeFromTimeStamps(lines, "events", stats)

def assertUnique(string, line, lines, seenLines):
    if string in line:
        if string in seenLines:
            print "Warning, seen line", string, "in", line.strip()
        seenLines.add(string)
        return True
    else:
        return False

def getParsingStats(lines, stats):
    seenLines = set()
    for line in lines:
        #print "XX:", line.strip()
        # Sentence splitting
        stats["PREPROCESS-SENTENCE-SPLITTING-time"] += getCounterTime(line, "Splitting Documents")
        if "Sentence splitting created" in line:
            stats["PREPROCESS-SENTENCE-SPLITTING-sentences"] += int(line.split()[5])
        # BANNER
        if assertUnique("BANNER time:", line, lines, seenLines):
            stats["PREPROCESS-BANNER-time"] += getSeconds(line.split("BANNER time:")[-1])
        if "BANNER found" in line:
            splits = line.split()
            stats["PREPROCESS-BANNER-entities"] += int(splits[4])
            stats["PREPROCESS-BANNER-sentences"] += int(splits[7])
        # McClosky parsing
        stats["PREPROCESS-CHARNIAK-time"] += getCounterTime(line, "Parsing:")
        if "Parsed" in line:
            splits = line.split()
            stats["PREPROCESS-CHARNIAK-sentences"] += int(splits[3])
            stats["PREPROCESS-CHARNIAK-failed"] += int(splits[5][1:])
        # Stanford conversion
        stats["PREPROCESS-STANFORD-time"] += getCounterTime(line, "Stanford Conversion:")
        if "Stanford conversion was done" in line:
            splits = line.split()
            stats["PREPROCESS-STANFORD-sentences"] += int(splits[7])
            stats["PREPROCESS-STANFORD-nodep"] += int(splits[9])
            stats["PREPROCESS-STANFORD-failed"] += int(splits[13])
        # Protein name splitting
        stats["PREPROCESS-PROTEIN-NAME-SPLITTING-time"] += getCounterTime(line, "Splitting names")
        # Head detection
        if "EXIT STEP FIND-HEADS time:" in line:
            stats["PREPROCESS-FIND-HEADS-time"] += getSeconds(line.split("\t")[-1].split(":", 1)[-1])
        if assertUnique("documents,", line, lines, seenLines):
            splits = line.split()
            stats["PREPROCESS-HEADS-documents"] += int(splits[2])
            stats["PREPROCESS-HEADS-sentences"] += int(splits[4])
        # Total time
        if assertUnique("Total preprocessing time", line, lines, seenLines):
            stats["TOTAL-time-preprocess"] += getSeconds(line.strip().split("\t")[1].split(":", 1)[1])
            stats["TOTAL-time"] += getSeconds(line.strip().split("\t")[1].split(":", 1)[1])
    #getTimeFromTimeStamps(lines, "preprocess", stats)
    return stats

def getTimeFromTimeStamps(lines, tag, stats):
    beginTime = [int(x) for x in lines[0].split("\t")[0][1:-2].split(":")]
    assert len(beginTime) == 3
    endTime = [int(x) for x in lines[-1].split("\t")[0][1:-2].split(":")]
    assert len(endTime) == 3
    if beginTime[0] - endTime[0] > endTime[0] - beginTime[0]:
        beginTime[0] = 24-beginTime[0]
    stats["TOTAL-time-timestamps-"+tag] += abs(endTime[0] - beginTime[0]) * 3600
    stats["TOTAL-time-timestamps-"+tag] += abs(endTime[1] - beginTime[1]) * 60
    stats["TOTAL-time-timestamps-"+tag] += abs(endTime[2] - beginTime[2])

def processFile(filename, stats, filetags=[".log"], verbose=True):
    match = False
    for filetag in filetags:
        if filename.endswith(filetag):
            match = True
    if match:
        print "Processing", filename
        f = open(filename, "rt")
        lines = f.readlines()
        f.close()
        # Get parsing statistics
        parseSection = getLastSection(lines, "------------ Preprocessing ------------", 
                                      "Total preprocessing time:")
        if parseSection == None:
            if verbose:
                print "Warning, no parse section for", filename
        else:
            if verbose:
                print "******************* PARSE SECTION FOUND *******************"
                print parseSection
                print "=================== PARSE SECTION BEGIN ==================="
                print "".join(lines[parseSection[0]:parseSection[1]])
                print "=================== PARSE SECTION END ==================="
            getParsingStats(lines[parseSection[0]:parseSection[1]], stats)
            # Check stats
            tempStats = getParsingStats(lines[parseSection[0]:parseSection[1]], defaultdict(int))
            totalTime = 0.000000000000001
            sumTime = 0
            for key in tempStats:
                if "TOTAL" in key:
                    if "preprocess" in key:
                        totalTime = tempStats[key]
                elif "time" in key:
                    sumTime += tempStats[key]
            if sumTime / totalTime > 0.9 or sumTime / totalTime < 1.1:
                print "Warning, time difference", (sumTime, totalTime)
        # Get event statistics
        eventSection = getLastSection(lines, "------------ Event Detection ------------", 
                                      "Total event detection time:",
                                      ["No model defined, skipping event detection"])
        if eventSection == None:
            if verbose:
                print "Warning, no event section for", filename
        else:
            getEventStats(lines[eventSection[0]:eventSection[1]], stats)
                        
def queue(input, filetags=[".log"], verbose=True):
    stats = defaultdict(int)
    #stats["protein-dist"] = defaultdict(int)
    #stats["event-dist"] = defaultdict(int)
    #stats["sentence-dist"] = defaultdict(int)
    if os.path.exists(input) and os.path.isfile(input): # single file
        processFile(input, stats, filetags, verbose=verbose)
    else: # walk directory tree
        for triple in os.walk(input):
            print "Processing", triple[0]
            for filename in sorted(triple[2]):
                processFile(os.path.join(triple[0], filename), stats, filetags, verbose=verbose)
    return stats

def process(input, filetags=[".log"], verbose=True):
    stats = queue(input, filetags, verbose=verbose)
    for key in sorted(stats):
        print key + ":", 
        printValue(key, stats[key])

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input data")
    optparser.add_option("-t", "--tags", default=".log", dest="tags", help="log file tag")
    optparser.add_option("-v", "--verbose", default=False, action="store_true", dest="verbose", help="")
    (options, args) = optparser.parse_args()
    
    options.tags = options.tags.split(",")
    print "Tags", options.tags
    process(options.input, options.tags, options.verbose)