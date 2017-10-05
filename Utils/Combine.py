import sys, os
import copy
from collections import defaultdict
import tempfile
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Detectors.Preprocessor import Preprocessor
import Utils.ElementTreeUtils as ETUtils
import Utils.STFormat.ConvertXML as ConvertXML
from Evaluators.ChemProtEvaluator import ChemProtEvaluator
import Evaluators.EvaluateInteractionXML as EvaluateIXML
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
from collections import OrderedDict
import itertools
from Utils.ProgressCounter import ProgressCounter

def getConfScores(interaction):
    intType = interaction.get("type")
    conf = interaction.get("conf")
    confScores = {}
    for commaSplit in conf.split(","):
        cls, confidence = commaSplit.rsplit(":", 1)
        confidence = float(confidence)
        if "---" not in cls:
            assert cls not in confScores
            confScores[cls] = confidence
    return confScores

def getScoreRange(root):
    scoreRange = [None, None]
    for interaction in root.iter("interaction"):
        scores = getConfScores(interaction)
        values = scores.values()
        minScore = min(values)
        if scoreRange[0] == None or minScore < scoreRange[0]:
            scoreRange[0] = minScore
        maxScore = max(values)
        if scoreRange[1] == None or maxScore > scoreRange[1]:
            scoreRange[1] = maxScore
    scoreRange.append(scoreRange[1] - scoreRange[0])
    return tuple(scoreRange)

def addInteraction(interaction, interactions, category):
    key = interaction.get("e1") + "/" + interaction.get("e2")
    if key not in interactions:
        interactions[key] = {"a":None, "b":None, "gold":None}
    assert category in ("a", "b", "gold")
    interactions[key][category] = interaction

def getInteractions(a, b, gold):
    interactions = OrderedDict()
    for interaction in a.findall('interaction'):
        addInteraction(interaction, interactions, "a")
    for interaction in b.findall('interaction'):
        addInteraction(interaction, interactions, "b")
    if gold:
        numIntersentence = 0
        for interaction in gold.findall('interaction'):
            #print interaction.get("e1").split(".i")[0], interaction.get("e2").split(".i")[0]
            if interaction.get("e1").split(".e")[0] != interaction.get("e2").split(".e")[0]:
                numIntersentence += 1
                continue
            addInteraction(interaction, interactions, "gold")
        #print "Skipped", numIntersentence, "intersentence interactions"
    return interactions

def getCombinedInteraction(intDict, mode, counts, scoreRange):
    assert mode in ("AND", "OR"), mode
    counts["total"] += 1
    if intDict["a"] == None and intDict["b"] == None:
        counts["both-None"] += 1
        return None
    elif intDict["a"] == None or intDict["b"] == None:
        if intDict["a"]:
            counts["only-A"] += 1
        else:
            counts["only-B"] += 1
        if mode == "AND":
            return None
        elif mode == "OR":
            return intDict["a"] if (intDict["a"] != None) else intDict["b"]
    else:
        if intDict["a"].get("type") == intDict["b"].get("type"):
            counts["both-same"] += 1
            return intDict["a"]
        confA = getConfScores(intDict["a"])[intDict["a"].get("type")]
        confA = (confA - scoreRange["a"][0]) / (scoreRange["a"][2])
        confB = getConfScores(intDict["b"])[intDict["b"].get("type")]
        confB = (confB - scoreRange["b"][0]) / (scoreRange["b"][2])
        if confA > confB:
            counts["conf-A"] += 1
            return intDict["a"]
        else:
            counts["conf-B"] += 1
            return intDict["b"]

def evaluateChemProt(xml, gold):
    EvaluateIXML.run(AveragingMultiClassEvaluator, xml, gold, "McCC")
    preprocessor = Preprocessor(steps=["EXPORT_CHEMPROT"])
    tempDir = tempfile.mkdtemp()
    print >> sys.stderr, "Using temporary evaluation directory", tempDir
    tsvPath = os.path.join(tempDir, "predictions.tsv")
    preprocessor.process(xml, tsvPath)
    ChemProtEvaluator().evaluateTSV(tsvPath, tempDir)
    print >> sys.stderr, "Removing temporary evaluation directory", tempDir
    shutil.rmtree(tempDir)
    
def combine(inputA, inputB, inputGold, outPath=None, mode="OR"):
    assert options.mode in ("AND", "OR")
    print "Loading the Interaction XML files"
    print "Loading A from", inputA
    a = ETUtils.ETFromObj(inputA)
    print "Loading B from", inputB
    b = ETUtils.ETFromObj(inputB)
    gold = None
    if inputGold:
        print "Loading gold from", inputGold
        gold = ETUtils.ETFromObj(inputGold) if inputGold else None
    print "Copying a as template"
    template = copy.deepcopy(a)
    print "Calculating confidence score ranges"
    scoreRanges = {}
    scoreRanges["a"] = getScoreRange(a)
    scoreRanges["b"] = getScoreRange(b)
    print scoreRanges
    print "Combining"
    counts = defaultdict(int)
    counter = ProgressCounter(len([x for x in a.findall("document")]), "Combine")
    for docA, docB, docGold, docTemplate in itertools.izip_longest(*[x.findall("document") for x in (a, b, gold, template)]):
        counter.update()
        assert len(set([x.get("id") for x in (docA, docB, docGold, docTemplate)])) == 1
        for sentA, sentB, sentGold, sentTemplate in itertools.izip_longest(*[x.findall("sentence") for x in (docA, docB, docGold, docTemplate)]):
            assert len(set([x.get("id") for x in (sentA, sentB, sentGold, sentTemplate)])) == 1
            interactions = getInteractions(sentA, sentB, sentGold)
            for interaction in sentTemplate.findall("interaction"):
                sentTemplate.remove(interaction)
            analyses = sentTemplate.find("analyses") 
            if analyses:
                sentTemplate.remove(analyses)
            for key in interactions:
                interaction = getCombinedInteraction(interactions[key], mode, counts, scoreRanges)
                if interaction != None:
                    sentTemplate.append(copy.deepcopy(interaction))
            if analyses:
                sentTemplate.append(analyses)
    print "Counts:", dict(counts)
    if gold != None:
        print "****** Evaluating A ******"
        evaluateChemProt(a, gold) #EvaluateIXML.run(AveragingMultiClassEvaluator, a, gold, "McCC")
        print "****** Evaluating B ******"
        evaluateChemProt(b, gold) #EvaluateIXML.run(AveragingMultiClassEvaluator, b, gold, "McCC")
        print "****** Evaluating Combined ******"
        evaluateChemProt(template, gold) #EvaluateIXML.run(AveragingMultiClassEvaluator, template, gold, "McCC")
    if outPath != None:
        print "Writing output to", outPath
        ETUtils.write(template, outPath)

if __name__=="__main__":       
    from optparse import OptionParser
    optparser = OptionParser(description="Combine interaction predictions")
    optparser.add_option("-a", "--inputA", default=None, dest="inputA", help="First set of predictions in Interaction XML format")
    optparser.add_option("-b", "--inputB", default=None, dest="inputB", help="Second set of predictions in Interaction XML format")
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="Gold interactions in Interaction XML format")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Path to output Interaction XML file (if exists will be overwritten)")
    optparser.add_option("-m", "--mode", default="OR", dest="mode", help="The combination for the output (AND or OR).")
    (options, args) = optparser.parse_args()
    
    combine(options.inputA, options.inputB, options.gold, options.output, options.mode)