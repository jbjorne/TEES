import sys, os
import STTools
import tempfile
import shutil
from collections import defaultdict
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../Evaluators")))
import BioNLP11GeniaTools
from pylab import *

def getScoreDict(scoreString):
    """
    Extract individual scores from a comma-separated list
    """
    scoreDict = {}
    for pairString in scoreString.split(","):
        className, score = pairString.split("=")
        score = float(score)
        assert className not in scoreDict
        scoreDict[className] = score
    return scoreDict

def updateRange(rangeDict, sourceDict):
    for key in sourceDict:
        if rangeDict[key][0] == None or rangeDict[key][0] > sourceDict[key]:
            rangeDict[key][0] = sourceDict[key]
        if rangeDict[key][1] == None or rangeDict[key][1] < sourceDict[key]:
            rangeDict[key][1] = sourceDict[key]

def getRangeDicts(documents):
    rangeDicts = {}
    rangeDicts["unmerging"] = defaultdict(lambda:[None, None])
    rangeDicts["triggers"] = defaultdict(lambda:[None, None])
    for doc in documents:
        for event in doc.events:
            updateRange(rangeDicts["triggers"], event.trigger.triggerScoreDict)
            updateRange(rangeDicts["unmerging"], event.trigger.unmergingScoreDict)
    print "Ranges", rangeDicts
    return rangeDicts

def getScore(scoreDict, typeString=None):
    """
    Get the highest score (optionally for a known type)
    """
    currentScore = None
    for key in scoreDict:
        if typeString != None: # match type
            for keySplit in key.split("---"): # check for merged classes
                if key == typeString and currentScore == None or currentScore < scoreDict[key]:
                    currentScore = scoreDict[key]
                    highestKey = key
        else: # take highest
            if currentScore == None or currentScore < scoreDict[key]:
                currentScore = scoreDict[key]
                highestKey = key
    assert highestKey != "neg"
    assert currentScore != None
    return currentScore, highestKey

def normalizeScore(value, key, rangeDict):
    return (value - rangeDict[key][0]) / (abs(rangeDict[key][0]) + abs(rangeDict[key][1])) 

def processScores(documents, normalize=False):
    """
    Convert score strings to a single float value
    """
    print "Extracting scores"
    for document in documents:
        for event in document.events:
            if event.trigger != None:
                if event.trigger.triggerScores != None:
                    event.trigger.triggerScoreDict = getScoreDict(event.trigger.triggerScores)
            if event.trigger.unmergingScores != None:
                # unmerging scores should actually be in the event, but triggers are never shared anyway
                event.trigger.unmergingScoreDict = getScoreDict(event.trigger.unmergingScores)
    
    counts = defaultdict(int)
    if normalize:
        print "Normalizing ranges"
        rangeDicts = getRangeDicts(documents)
    for document in documents:
        counts["documents"] += 1
        for event in document.events:
            counts["events"] += 1
            if event.trigger != None:
                if event.trigger.triggerScores != None:
                    event.trigger.triggerScore, scoreKey = getScore(event.trigger.triggerScoreDict, event.trigger.type)
                    if normalize:
                        event.trigger.triggerScore = normalizeScore(event.trigger.triggerScore, scoreKey, rangeDicts["triggers"])
                    counts["event-trigger-scores"] += 1
            if event.trigger.unmergingScores != None:
                # unmerging scores should actually be in the event, but triggers are never shared anyway
                event.trigger.unmergingScore, scoreKey = getScore(event.trigger.unmergingScoreDict)
                if normalize:
                    event.trigger.unmergingScore = normalizeScore(event.trigger.unmergingScore, scoreKey, rangeDicts["unmerging"])
                counts["event-unmerging-scores"] += 1
    return counts

#def sortByUnmergingScore():
#    pass

def sortByScore(documents, sortMethod="unmerging"):
    """
    Make an ordered list for all events in all documents
    """
    eventList = []
    for document in documents:
        for event in document.events:
            if "unmerging" in sortMethod:
                eventList.append( (event.trigger.unmergingScore, event, document) )
            elif "triggers" in sortMethod:
                eventList.append( (event.trigger.triggerScore, event, document) )
    eventList.sort()
    return eventList

def markForRemoval(eventList, cutoff=1.0):
    """
    Take an ordered event list, and mark a fraction for removal by setting their arguments to [], thus
    causing them to be removed in validation.
    """
    breakPoint = cutoff * len(eventList)
    for i in range(len(eventList)):
        if i >= breakPoint:
            break
        eventList[i][1].arguments = [] # validation will remove events with 0 arguments

def evaluate(documents, sortMethod, verbose, cutoffs=[]):
    workdir = tempfile.gettempdir()
    outdir = os.path.join(workdir, "events")
    cutoffs.sort()
    eventList = sortByScore(documents, sortMethod)
    results = {}
    for cutoff in cutoffs:
        print "Cutoff", cutoff
        markForRemoval(eventList, cutoff)
        STTools.writeSet(documents, outdir, validate=True) # validation will remove events with 0 arguments
        results[cutoff] = BioNLP11GeniaTools.evaluateGE(outdir, task=2, evaluations=["approximate"], verbose=False, silent=not verbose)
        print results[cutoff]["approximate"]["ALL-TOTAL"]
    #shutil.rmtree(workdir)
    return results

def resultsToGraph(results, outputname):
    fig = figure()
    
    ax = subplot(111)
    ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)
    ax.yaxis.grid(True, linestyle='-', which='minor', color='lightgrey', alpha=0.5)
    ylabel('precision/recall/F-score', size=12)
    xlabel('events [%]', size=12)
    
    plots = {}
    plotNames = ["precision", "recall", "fscore"]
    plotColours = {"precision":"red", "recall":"green", "fscore":"blue"}
    for name in plotNames:
        plots[name] = []
    xValues = []
    for key in sorted(results):
        for name in plotNames:
            plots[name].append(results[key]["approximate"]["ALL-TOTAL"][name])
        xValues.append(results[key]["approximate"]["ALL-TOTAL"]["answer"])
    
    for name in plotNames:
        plot(xValues, plots[name], marker="o", color=plotColours[name], linestyle="-")
    
    savefig(outputname, bbox_inches='tight')
    #show()

if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-s", "--sortmethod", default="unmerging", dest="sortmethod", help="")
    optparser.add_option("-v", "--verbose", default=False, action="store_true", dest="verbose", help="")
    (options, args) = optparser.parse_args()
    
    print "Loading documents"
    documents = STTools.loadSet(options.input, readScores=True)
    print "Processing scores"
    print processScores(documents, normalize="normalize" in options.sortmethod)
    print "Evaluating"
    results = evaluate(documents, options.sortmethod, verbose=options.verbose, cutoffs=[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9])
    resultsToGraph(results, "scorefig-" + options.sortmethod + ".pdf")
