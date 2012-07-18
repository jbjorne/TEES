import sys, os
import STTools
import tempfile
import shutil
from collections import defaultdict
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../Evaluators")))
import BioNLP11GeniaTools
from pylab import *
import time, datetime
sys.path.append(os.path.abspath(os.path.join(thisPath,"../Statistics")))
import Utils.Libraries.stats

def getResults(results):
    if "approximate" in results and "ALL-TOTAL" in results["approximate"]:
        return results["approximate"]["ALL-TOTAL"]
    else:
        return results["TOTAL"]

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
        # per key
        if rangeDict[key][0] == None or rangeDict[key][0] > sourceDict[key]:
            rangeDict[key][0] = sourceDict[key]
        if rangeDict[key][1] == None or rangeDict[key][1] < sourceDict[key]:
            rangeDict[key][1] = sourceDict[key]
        # total

def getRangeDicts(documents):
    rangeDicts = {}
    rangeDicts["unmerging"] = defaultdict(lambda:[None, None])
    rangeDicts["triggers"] = defaultdict(lambda:[None, None])
    rangeDicts["arguments"] = defaultdict(lambda:[None, None])
    for doc in documents:
        for event in doc.events:
            updateRange(rangeDicts["triggers"], event.trigger.triggerScoreDict)
            updateRange(rangeDicts["unmerging"], event.trigger.unmergingScoreDict)
            for argScoreDict in event.argScoreDicts:
                updateRange(rangeDicts["arguments"], argScoreDict)
    print "Ranges", rangeDicts
    return rangeDicts

def getStatValues(documents):
    statValues = {}
    triggerValues = []
    unmergingValues = []
    argValues = []
    for doc in documents:
        for event in doc.events:
            for value in sorted(event.trigger.triggerScoreDict.values()):
                triggerValues.append(value)
            if hasattr(event.trigger, "unmergingScoreDict"):
                for value in sorted(event.trigger.unmergingScoreDict.values()):
                    unmergingValues.append(value)
            for argScoreDict in event.argScoreDicts:
                for value in sorted(argScoreDict.values()):
                    argValues.append(value)
        for relation in doc.relations:
            for argScoreDict in relation.argScoreDicts:
                for value in sorted(argScoreDict.values()):
                    argValues.append(value)
    #print triggerValues, unmergingValues, argValues
    if len(triggerValues) > 0:
        statValues["trigger-stdev"] = stats.lstdev(triggerValues)
        statValues["trigger-mean"] = stats.lmean(triggerValues)
    if len(unmergingValues) > 0:
        statValues["unmerging-stdev"] = stats.lstdev(unmergingValues)
        statValues["unmerging-mean"] = stats.lmean(unmergingValues)
    statValues["arg-stdev"] = stats.lstdev(argValues)
    statValues["arg-mean"] = stats.lmean(argValues)
    return statValues

def standardize(score, statValues, scoreType):
    return (score - statValues[scoreType+"-mean"]) / statValues[scoreType+"-stdev"]

def getEventEVEXScore(event, statValues):
    scores = []
    if event.trigger != None:
        scores.append( standardize(event.trigger.triggerScore, statValues, "trigger") )
        scores.append( standardize(event.trigger.triggerScore, statValues, "unmerging") )
    if hasattr(event, "argScores"):
        for argScore in event.argScores:
            scores.append( standardize(argScore, statValues, "arg") )
            #scores.append( (argScore - statValues["arg-mean"]) / statValues["arg-stdev"] )
    score = min(scores)
    for arg in event.arguments: # recursively pick the lowest score
        if arg[1].id[0] == "E": # a nested event
            score = min(score, getEventEVEXScore(arg[1], statValues))
    return score

def getScore(scoreDict, typeString=None):
    """
    Get the highest score (optionally for a known type)
    """
    currentScore = None
    # EPI sites
    if typeString == "Site" and "SiteArg" in scoreDict:
        assert "Site" not in scoreDict, scoreDict.keys()
        typeString = "SiteArg"
    # Find the values
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
    assert highestKey != "neg", (typeString, scoreDict)
    assert currentScore != None, (typeString, scoreDict)
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
            event.argScoreDicts = []
            for arg in event.arguments:
                #print arg
                event.argScoreDicts.append( getScoreDict(arg[3]) )
        for relation in document.relations:
            # Use only the first value so you don't get the relation score twice
            relation.argScoreDicts = []
            relation.argScoreDicts.append( getScoreDict(relation.arguments[0][3]) )
    
    counts = defaultdict(int)
    if normalize:
        print "Normalizing ranges"
        rangeDicts = getRangeDicts(documents)
    statValues = getStatValues(documents)
    for document in documents:
        counts["documents"] += 1
        for event in document.events + document.relations:
            counts["events"] += 1
            if event.trigger != None:
                if event.trigger.triggerScores != None:
                    event.trigger.triggerScore, event.trigger.triggerScoreKey = getScore(event.trigger.triggerScoreDict, event.trigger.type)
                    if normalize:
                        event.trigger.triggerScore = normalizeScore(event.trigger.triggerScore, event.trigger.triggerScoreKey, rangeDicts["triggers"])
                    counts["event-trigger-scores"] += 1
                if event.trigger.unmergingScores != None:
                    # unmerging scores should actually be in the event, but triggers are never shared anyway
                    event.trigger.unmergingScore, event.trigger.unmergingScoreKey = getScore(event.trigger.unmergingScoreDict)
                    if normalize:
                        event.trigger.unmergingScore = normalizeScore(event.trigger.unmergingScore, event.trigger.unmergingScoreKey, rangeDicts["unmerging"])
                    counts["event-unmerging-scores"] += 1
            # argument scores
            event.argScores = []
            event.argScoreKeys = []
            for i in range(len(event.arguments)):
                if i < len(event.argScoreDicts): # REL has only one score
                    argScore, argScoreKey = getScore(event.argScoreDicts[i])#, arg[1])
                    if normalize:
                        argScore = normalizeScore(argScore, argScoreKey, rangeDicts["arguments"])
                    event.argScores.append(argScore)
                    event.argScoreKeys.append(argScoreKey)
    return counts

#def sortByUnmergingScore():
#    pass

def sortByScore(documents, sortMethod="unmerging"):
    """
    Make an ordered list for all events in all documents
    """
    eventList = []
    if "EVEX" in sortMethod or "standardize" in sortMethod:
        statValues = getStatValues(documents)
        print "Stat values:", statValues
    for document in documents:
        for event in document.events + document.relations:
            if "unmerging" in sortMethod:
                score = event.trigger.unmergingScore
                if "standardize" in sortMethod:
                    score = standardize(score, statValues, "unmerging")
                eventList.append( (score, event.id, event, document) ) # event.id should keep things deterministic if two scores are the same
            elif "triggers" in sortMethod:
                score = event.trigger.triggerScore
                if "standardize" in sortMethod:
                    score = standardize(score, statValues, "trigger")
                eventList.append( (score, event.id, event, document) )
            elif "EVEX" in sortMethod:
                eventList.append( (getEventEVEXScore(event, statValues), event.id, event, document) )
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
        eventList[i][2].arguments = [] # validation will remove events with 0 arguments

def evaluate(documents, sortMethod, verbose, cutoffs=[], task="GE.2"):
    workdir = tempfile.gettempdir()
    outdir = os.path.join(workdir, "events")
    cutoffs.sort()
    eventList = sortByScore(documents, sortMethod)
    results = {}
    startTime = time.time()
    for cutoff in cutoffs:
        print "Cutoff", cutoff, str(datetime.timedelta(seconds=time.time()-startTime))
        markForRemoval(eventList, cutoff)
        STTools.writeSet(documents, outdir, validate=True) # validation will remove events with 0 arguments
        #results[cutoff] = getResults(BioNLP11GeniaTools.evaluateGE(outdir, task=2, evaluations=["approximate"], verbose=False, silent=not verbose))
        if "REL" not in task:
            results[cutoff] = getResults(BioNLP11GeniaTools.evaluate(outdir, task=task)[1])
        else:
            results[cutoff] = {}
        print results
        #print results[cutoff]["approximate"]["ALL-TOTAL"]
    #shutil.rmtree(workdir)
    #maxEvents = results[0.0]["approximate"]["ALL-TOTAL"]["answer"]
    maxEvents = results[0.0]["answer"]
    print "Max events", maxEvents
    return results, maxEvents

def resultsToGraph(results, outputname, maxEvents=None, manualEvaluationFile=None, graphs="prf"):
    fig = figure()
    
    ax = subplot(111)
    ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)
    ax.yaxis.grid(True, linestyle='-', which='minor', color='lightgrey', alpha=0.5)
    ax.xaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)
    ax.xaxis.grid(True, linestyle='-', which='minor', color='lightgrey', alpha=0.5)
    
    ylabel('precision / recall / F-score [%]', size=12)
    if maxEvents != None:
        xlabel('events [%]', size=12)
    else:
        xlabel('events', size=12)
    
    plots = {}
    plotNames = [] #["precision", "fscore", "recall"]
    legendText = []
    plotColours = {}
    lineStyles = {}
    markerStyles = {}
    graphs = graphs.lower()
    if "p" in graphs:
        plotNames.append("precision")
        legendText.append("precision (BioNLP'11)")
        plotColours["precision"] = "red"
        lineStyles["precision"] = "-"
        markerStyles["precision"] = "v"
    if "r" in graphs:
        plotNames.append("recall")
        legendText.append("recall (BioNLP'11)")
        plotColours["recall"] = "green"
        lineStyles["recall"] = "-"
        markerStyles["recall"] = "^"
    if "f" in graphs:
        plotNames.append("fscore")
        legendText.append("fscore (BioNLP'11)")
        plotColours["fscore"] = "blue"
        lineStyles["fscore"] = "-"
        markerStyles["fscore"] = "s"
    for name in plotNames:
        plots[name] = []
    xValues = []
    for key in sorted(results):
        for name in plotNames:
            plots[name].append(results[key][name])
        xValue = results[key]["answer"]
        if maxEvents != None:
            xValue = float(xValue) / maxEvents * 100.0
        xValues.append(xValue)
    
    if manualEvaluationFile != None:
        manualPrecisions = getManualEvaluationPrecisions(manualEvaluationFile)
        plotManualEvaluationPrecisions(manualPrecisions, binSize=5, makeFig=False)
    
    for name in plotNames:
        plot(xValues, plots[name], marker=markerStyles[name], color=plotColours[name], linestyle=lineStyles[name], markersize=4)
    
    ylim([0, 80])
    
    if manualEvaluationFile != None:
        legendText = ["precision (EVEX)"] + legendText
    
    leg = legend(legendText, 'lower right')
    ltext  = leg.get_texts()
    setp(ltext, fontsize='small')
    savefig(outputname, bbox_inches='tight')
    #show()

def getManualEvaluationPrecisions(manualEvaluationFile):
    f = open(manualEvaluationFile, "rt")
    lines = f.readlines()
    f.close()
    
    events = []
    truePositives = 0
    falsePositives = 0
    for line in lines:
        begin, middle = line.split("--->")
        end = "\n"
        if "#" in line:
            middle, end = middle.split("#")
        eventEvaluation = middle.split(",")[-1].strip()
        if "F" in eventEvaluation:
            eventIsTrue = False
            falsePositives += 1
        else:
            eventIsTrue = True
            truePositives += 1
        # get predicted event info
        beginSplits = begin.split()
        eventWeight = float(beginSplits[3])
        fromAbstract = beginSplits[4] == "ABSTRACT"
        # add to list
        events.append( (eventWeight, eventIsTrue) )
    events.sort()
    precisions = [float(truePositives) / (truePositives + falsePositives)]
    count = 0
    for event in events:
        if event[1]:
            truePositives -= 1
        else:
            falsePositives -= 1
        if truePositives + falsePositives > 0:
            precisions.append(float(truePositives) / (truePositives + falsePositives))
            count += 1
            #print "Count", count, event[0], (truePositives, falsePositives), precisions[-1]
    return precisions

def plotManualEvaluationPrecisions(precisions, binSize=1, makeFig=True):
    if makeFig:
        fig = figure()
        
        ax = subplot(111)
        ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)
        ax.yaxis.grid(True, linestyle='-', which='minor', color='lightgrey', alpha=0.5)
        ax.xaxis.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)
        ax.xaxis.grid(True, linestyle='-', which='minor', color='lightgrey', alpha=0.5)
        ylabel('precision', size=12)
        xlabel('events [%]', size=12)
    
    binnedScores = []
    currentBin = []
    count = 0
    for precision in precisions:
        currentBin.append(precision)
        count += 1
        if count >= binSize:
            binnedScores.append( float(sum(currentBin)) / len(currentBin) * 100.0 )
            currentBin = []
            count = 0 
    
    numEvents = len(binnedScores)
    xValues = []
    for i in range(numEvents):
        xValues.append( float(numEvents-i)/numEvents*100 ) 
    plot(xValues, binnedScores, marker="o", color="red", linestyle="-", markersize=4)
    
    if makeFig:
        savefig("manual-scores-binned.pdf", bbox_inches='tight')

if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    optparser = OptionParser(description="Analyze confidence scores")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-t", "--task", default="GE.2", dest="task", help="", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="", metavar="FILE")
    optparser.add_option("-m", "--manual", default=None, dest="manual", help="", metavar="FILE")
    optparser.add_option("-g", "--graphs", default="prf", dest="graphs", help="", metavar="FILE")
    optparser.add_option("-s", "--sortmethod", default="unmerging", dest="sortmethod", help="")
    optparser.add_option("-v", "--verbose", default=False, action="store_true", dest="verbose", help="")
    optparser.add_option("--steps", default=10, type="int", dest="steps", help="", metavar="FILE")
    optparser.add_option("--binSize", default=1, type="int", dest="binSize", help="", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    if options.manual != None and options.input == None:
        precisions = getManualEvaluationPrecisions(options.manual)
        plotManualEvaluationPrecisions(precisions, options.binSize)
    else:
        cutoffs = [float(x)/options.steps for x in range(options.steps)]
        print "Loading documents"
        documents = STTools.loadSet(options.input, readScores=True)
#        print "Testing evaluator"
#        tempdir = tempfile.mkdtemp()
#        print tempdir
#        STTools.writeSet(documents, tempdir, debug=True, validate=False) # validation will remove events with 0 arguments
#        BioNLP11GeniaTools.evaluate(tempdir, task=options.task)
        #shutil.rmtree(tempdir)
        print "Processing scores"
        print processScores(documents, normalize="normalize" in options.sortmethod)
        print "Evaluating"
        results, maxEvents = evaluate(documents, options.sortmethod, verbose=options.verbose, cutoffs=cutoffs, task=options.task)
        if options.output == None:
            output = "scorefig-" + options.sortmethod + ".pdf"
        else:
            output = options.output
        resultsToGraph(results, options.output, maxEvents, manualEvaluationFile=options.manual)
