import sys, os
import STTools
import tempfile
import shutil
from collections import defaultdict
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../Evaluators")))
import BioNLP11GeniaTools

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
    return currentScore

def processScores(documents):
    """
    Convert score strings to a single float value
    """
    counts = defaultdict(int)
    for document in documents:
        counts["documents"] += 1
        for event in document.events:
            counts["events"] += 1
            if event.trigger != None:
                if event.trigger.triggerScores != None:
                    event.trigger.triggerScore = getScore(getScoreDict(event.trigger.triggerScores), event.trigger.type)
                    counts["event-trigger-scores"] += 1
            if event.trigger.unmergingScores != None:
                # unmerging scores should actually be in the event, but triggers are never shared anyway
                event.trigger.unmergingScore = getScore(getScoreDict(event.trigger.unmergingScores))
                counts["event-unmerging-scores"] += 1
    return counts

def sortByUnmergingScore():
    pass

def sortByScore(sortFunc=None):
    """
    Make an ordered list for all events in all documents
    """
    eventList = []
    for document in documents:
        for event in document.events:
            eventList.append( (event, document) )
    eventList.sort(sortFunc)

def markForRemoval(cutoff=1.0, eventList):
    """
    Take an ordered event list, and remove a fraction
    """
    breakPoint = cutoff * len(eventList)
    for i in range(len(eventList)):
        if i >= breakPoint:
            break
        eventList[i][0].arguments = [] # validation will remove events with 0 arguments

def evaluate(documents):
    workdir = tempfile.gettempdir()
    outdir = os.path.join(workdir, "events")
    STTools.writeSet(documents, outdir, validate=True) # validation will remove events with 0 arguments
    results = BioNLP11GeniaTools.evaluateGE(outdir, task=2, evaluations=["approximate"], verbose=True, silent=False)
    print results["approximate"]["ALL-TOTAL"]
    shutil.rmtree(workdir)

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
    (options, args) = optparser.parse_args()
    
    print "Loading documents"
    documents = STTools.loadSet(options.input, readScores=True)
    print "Processing scores"
    print processScores(documents)
    print "Evaluating"
    evaluate(documents)
