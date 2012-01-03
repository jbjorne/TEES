import sys, os
from collections import defaultdict
import time

def getSeconds(timeString):
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
    if "100.00 %" in line and match in line:
        return getSeconds(line.split("(")[-1].split(")")[0])
    else:
        return 0.0

def getLastSection(lines, beginMatch, endMatch):
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
        # Search for end position
        currEnd = None
        for i in range(currBegin+1, len(lines)):
            if beginMatch in lines[i]: # block doesn't end before another begins
                break
            if endMatch in lines[i]:
                currEnd = i + 1
                break
        if currBegin != None and currEnd != None:
            return (currBegin, currEnd)

def getParsingStats(lines, stats):
    for line in lines:
        # Sentence splitting
        stats["SPLITTING-time"] += getCounterTime(line, "Splitting Documents")
        if "Sentence splitting created" in line:
            stats["SPLITTING-sentences"] += int(line.split()[4])
        # BANNER
        if "BANNER time:" in line:
            stats["BANNER-time"] += getSeconds(line.split("BANNER time:")[-1])
        if "BANNER found" in line:
            splits = line.split()
            stats["BANNER-entities"] += int(splits[3])
            stats["BANNER-sentences"] += int(splits[6])
        # McClosky parsing
        stats["PARSING-time"] += getCounterTime(line, "Parsing:")
        if "Parsed" in line:
            splits = line.split()
            stats["PARSING-sentences"] += int(splits[2])
            stats["PARSING-failed"] += int(splits[4][1:])
        # Stanford conversion
        stats["STANFORD-time"] += getCounterTime(line, "Stanford Conversion:")
        if "Stanford conversion was done" in line:
            splits = line.split()
            stats["STANFORD-sentences"] += int(splits[6])
            stats["STANFORD-nodep"] += int(splits[8])
            stats["STANFORD-failed"] += int(splits[12])
        # Protein name splitting
        stats["PROTEIN-NAME-SPLITTING-time"] += getCounterTime(line, "Splitting names")
        # Head detection
        stats["HEADS-time"] += getCounterTime(line, "Making sentence graphs")
        if "documents," in line:
            splits = line.split()
            stats["HEADS-documents"] += int(splits[1])
            stats["HEADS-sentences"] += int(splits[3])
        # Total time
        if "Total processing time" in line:
            stats["TOTAL-time"] += getSeconds(line.strip().split("\t")[1].split(":", 1)[1])
    return stats

def processFile(filename, stats, filetags=[".log"], verbose=True):
    match = False
    for filetag in filetags:
        if filename.endswith(filetag):
            match = True
    if match:
        f = open(filename, "rt")
        lines = f.readlines()
        f.close()
        parseSection = getLastSection(lines, "------------ Preprocessing ------------", "Total processing time:")
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
            for filename in triple[2]:
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
    process(options.input, options.tags, options.verbose)