import sys, os
from optparse import OptionParser
import tarfile

def getType(line):
    eventType =  line.split("\t")[1].split()[0]
    if line[0] == "E":
        return eventType.split(":")[0]
    else:
        return eventType

def countEvents(filePath):
    triggers = {} # trigger instances
    events = {} # event instances
    distribution = {} # number of events -> number of abstracts
    
    # Process all medline09nXXXX-part-XXXX-events-geniaformat.tar.gz files
    print "Processing", filePath
    f = tarfile.open(filePath)
    for name in f.getnames():
        # Process only the a2.t1 files from each gz-file
        if name.find(".a2.t123") != -1:
            id = name.split(".",1)[0]
        else:
            continue

        a2File = f.extractfile(id + ".a2.t123")
        a2Lines = a2File.readlines()
        a2File.close()
        
        eventCount = 0 # number of events in whole abstract
        for line in a2Lines:
            eventType = getType(line)
            if line[0] == "T": # trigger
                if not triggers.has_key(eventType): triggers[eventType] = 0
                triggers[eventType] += 1
            elif line[0] == "E":
                eventCount += 1
                if not events.has_key(eventType): events[eventType] = 0
                events[eventType] += 1
            else:
                pass
                #print "Unknown", line
        
        # per abstract event count
        if not distribution.has_key(eventCount): distribution[eventCount] = 0
        distribution[eventCount] += 1
    
    print "Trigger counts"
    for k in sorted(triggers.keys()):
        print k, triggers[k]
    
    print "Event counts"
    for k in sorted(events.keys()):
        print k, events[k]
    
    print "Event distribution (number of events vs. number of citations)"
    for k in sorted(distribution.keys()):
        print str(k) + ": " + str(distribution[k])
    
    return triggers, events, distribution

def main(inDirs, failFileName=None):
    if failFileName != None:
        failFile = open(failFileName, "at")
    
    allTriggers = {}
    allEvents = {} 
    allDistribution = {}
    for inDir in inDirs:
        for triple in os.walk(inDir):
            print "Processing", triple[0] 
            inputFiles = []
            for filename in triple[2]:
                if filename[-7:] == ".tar.gz":
                    inputFiles.append(filename)
            if len(inputFiles) == 0:
                continue
            
            for inputFile in inputFiles:
                triggers, events, distribution = countEvents(os.path.join(triple[0],inputFile))
                for p in [(triggers, allTriggers), (events, allEvents), (distribution, allDistribution)]:
                    for key in p[0].keys():
                        if not p[1].has_key(key): p[1][key] = 0
                        p[1][key] += p[0][key]
    
    print "Triggers"
    for k in sorted(allTriggers.keys()):
        print " " + k + ": " + str(allTriggers[k])
    print "Events"
    for k in sorted(allEvents.keys()):
        print " " + k + ": " + str(allEvents[k])
                
    if failFileName != None:            
        failFile.close()

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-f", "--statsFile", default=None, dest="statsFile", help="Failed input files will be listed here")
    (options, args) = optparser.parse_args()
    assert options.input != None
    if options.input.find(",") != -1:
        options.input = options.input.split(",")
    else:
        options.input = [options.input]
    for i in options.input:
        assert os.path.exists(i)
    
    main(options.input, options.statsFile)
        