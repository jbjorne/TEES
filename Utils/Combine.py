import sys, os
import copy
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
import Utils.STFormat.ConvertXML as ConvertXML
import Evaluators.EvaluateInteractionXML as EvaluateIXML
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
from collections import OrderedDict
import itertools
from Utils.ProgressCounter import ProgressCounter

# from sklearn.metrics import classification_report
# #from sklearn.cross_validation import LabelKFold
# from sklearn.grid_search import GridSearchCV
# from sklearn.feature_extraction import DictVectorizer
# from sklearn.svm import SVC
# from sklearn.ensemble import ExtraTreesClassifier
# from sklearn.tree import DecisionTreeClassifier
# from sklearn.neighbors import KNeighborsClassifier
# import copy
# from collections import defaultdict
# from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
# from sklearn.linear_model.perceptron import Perceptron
# from sklearn.ensemble.gradient_boosting import GradientBoostingClassifier
# from sklearn.linear_model.stochastic_gradient import SGDClassifier
# from sklearn.neighbors.nearest_centroid import NearestCentroid
# from sklearn.metrics import f1_score

# def showStats(interactions, entities, useGold):
#     stats = defaultdict(int)
#     statsIds = defaultdict(str)
#     confScores = {"a":set(), "b":set()}
#     for key in interactions:
#         interaction = interactions[key]
#         if useGold:
#             goldClass = interaction["gold"].get("type")
#             combination = goldClass
#         else:
#             goldClass = "neg"
#             combination = "unknown" 
#         combination += "(" + entities[interaction["a"].get("e1")].get("type") + "/" + entities[interaction["a"].get("e2")].get("type") + ")" 
#         for setName in ("a", "b"):
#             combination += "_" + setName + ":"
#             predClass = interaction[setName].get("type")
#             if useGold:
#                 combination += "t" if goldClass == predClass else "f"
#             combination += "n" if predClass == "neg" else "p"
#             confScores[setName].add(getConfScore(interaction[setName]))
#         stats[combination] += 1
#         statsIds[combination] += key + "_"
#     for key in sorted(stats.keys()):
#         print key, stats[key] #, statsIds[key][0:100]
#     print "Confidence score ranges"
#     for setName in ("a", "b"):
#         print setName, [min(confScores[setName]), max(confScores[setName])]

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
#     try:
#         confScores = {x[0]:float(x[1]) for x in [y.split(":") for y in conf.split(",")]}
#     except Exception as e:
#         print conf
#         print e.__doc__
#         print e.message
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

# def buildFeatures(interactions, entities, show=10):
#     features = []
#     for key in interactions:
#         f = {}
#         confidences = {}
#         combined = {"types":"comb_pred"}
#         aPos = interactions[key]["a"].get("type") != "neg"
#         bPos = interactions[key]["b"].get("type") != "neg"
#         #f["AND"] = combinePredictions(aPos, bPos, "AND")
#         f["OR"] = combinePredictions(aPos, bPos, "OR")
#         if True:
#             for setName in ("a", "b"):
#                 # interaction
#                 interaction = interactions[key][setName]
#                 predType = interaction.get("type")
#                 f["pred-" + setName] = 1 if predType != "neg" else -1
# #                 combined["types"] += "-" + predType
# #                for intType in ("neg", "Lives_In"):
# #                     if predType == intType:
# #                         f[setName + "_type_" + intType] = 1
# #                     else:
# #                         f[setName + "_type_not_" + intType] = 1
#                 #f[setName + "_pred"] = 1 if interaction.get("type") != "neg" else -1
#                 # entities
#                 e1 = entities[interaction.get("e1")]
#                 e2 = entities[interaction.get("e2")]
#                 #distance = abs(int(e1.get("charOffset").split("-")[0]) - int(e2.get("charOffset").split("-")[0]))
#                 #f["distance"] = distance
#                 for entity, entKey in [(e1, "e1"), (e2, "e2")]:
#                     f[entKey + "_type_" + entity.get("type")] = 1
#                     #for token in entity.get("text").split():
#                     #    f[entKey + "_token_" + token] = 1
#                     #f[entKey + "_text_" + entity.get("text").split()[-1].lower()] = 1
#                 f["e_types_" + e1.get("type") + "-" + e2.get("type")] = 1
#                 # confidence scores
#                 confScore = getConfScore(interaction)
#                 confidences[setName] = confScore
#                 f[setName + "_conf"] = confScore
#             f["combined_conf"] = (confidences["a"] + confidences["b"]) / 2.0
#             #f["combined_pred"] = 1 if f["combined_conf"] > 0 else -1
#             f["combined_pred_type_" + ("pos" if f["combined_conf"] > 0 else "neg")] = 1
#             for combinedFeature in sorted(combined.values()):
#                 f[combinedFeature] = 1
#         if show > 0:
#             print f
#             show -= 1
#         features.append(f)
#     return DictVectorizer(sparse=False).fit_transform(features)

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
        counts["both-different"] += 1
        confA = getConfScores(intDict["a"])[intDict["a"].get("type")]
        confA = (confA - scoreRange["a"][0]) / (scoreRange["a"][2])
        confB = getConfScores(intDict["b"])[intDict["b"].get("type")]
        confB = (confB - scoreRange["b"][0]) / (scoreRange["b"][2])
        return intDict["a"] if confA > confB else intDict["b"]
    

#def mapHeads(entities, xml):
#    for template.getroot().iter('sentence'):

# def getERole(entity):
#     eType = entity.get("type")
#     assert eType in ("Bacteria", "Habitat", "Geographical")
#     if eType == "Bacteria":
#         return "Bacteria"
#     else:
#         return "Location"

# def writeOutput(template, predictions, outPath):
#     print "Generating output"
#     template = copy.deepcopy(template)
#     entities = {x.get("id"):x for x in template.getroot().iter('entity')}
#     outInteractions = [x for x in template.getroot().iter('interaction')]
#     assert len(outInteractions) == len(predictions)
#     for i in range(len(predictions)):
#         interaction = outInteractions[i]
#         interaction.set("type", "Lives_In" if predictions[i] > 0 else "neg")
#     print "Writing output to", outPath
#     ETUtils.write(template.getroot(), outPath)
#     ConvertXML.toSTFormat(template, outPath + "-events.zip", outputTag="a2", useOrigIds=False, debug=False, allAsRelations=False, writeExtra=False)
# 
# def combinePredictions(aPos, bPos, mode="AND"):
#     if mode == "AND":
#         return 1 if (aPos and (aPos == bPos)) else -1
#     elif mode == "OR":
#         return 1 if (aPos or bPos) else -1
# 
# def getSimpleCombinedPredictions(interactions, mode = "AND"):
#     predictions = []
#     for key in interactions:
#         interaction = interactions[key]
#         aPos = interaction["a"].get("type") != "neg"
#         bPos = interaction["b"].get("type") != "neg"
#         predictions.append(combinePredictions(aPos, bPos, mode))
#     return predictions

# def evaluatePerformance(labels, predictions, results, title, tag=None, verbose=True):
#     if verbose:
#         print title
#         print classification_report(labels, predictions)
#     f1score = f1_score(labels, predictions)
#     #print f1score
#     results.append((f1score, tag, title, predictions))
    
def combine(inputA, inputB, inputGold, outPath=None, mode="AND"):
    print "Loading the Interaction XML files"
    print "Loading A from", inputA
    a = ETUtils.ETFromObj(inputA)
    print "Loading B from", inputB
    b = ETUtils.ETFromObj(inputB)
    print "Loading gold from", inputGold
    gold = ETUtils.ETFromObj(inputGold) if inputGold else None
    print "Copying gold as template"
    template = copy.deepcopy(gold)
    print "Calculating scores"
    scoreRanges = {}
    scoreRanges["a"] = getScoreRange(a)
    scoreRanges["b"] = getScoreRange(b)
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
    print "Counts:", dict(counts)
    if gold != None:
        print "Evaluating A"
        EvaluateIXML.run(AveragingMultiClassEvaluator, a, gold, "McCC")
        print "Evaluating B"
        EvaluateIXML.run(AveragingMultiClassEvaluator, b, gold, "McCC")
        print "Evaluating Combined"
        EvaluateIXML.run(AveragingMultiClassEvaluator, template, gold, "McCC")
    if outPath != None:
        ETUtils.write(template, outPath)
    
#     if not concise: print "Reading interactions from input XML files"
#     interactions = getInteractions(a, b, gold)
#     entities = {x.get("id"):x for x in a.getroot().iter('entity')}
#     if not concise:
#         print "===============", "Statistics", "===============" 
#         showStats(interactions, entities, inputGold != None)
# 
#     documentLabels = [key.split(".s")[0] for key in interactions]
#     if not concise: print "Total interactions =", len(interactions)
#     if not concise: print "Unique K-fold labels =", len(set(documentLabels))
#     if gold != None:
#         y_all = [1 if (interactions[key]["gold"].get("type") != "neg") else -1 for key in interactions]
#     else:
#         y_all = [-1 for key in interactions]
#     if not concise: print "pos / neg = ", y_all.count(1), "/", y_all.count(-1)    
#     learnedPredictions = None
#     if learning:
#         print "===============", "Learning", "===============" 
#         X_all = buildFeatures(interactions, entities)
#         learnedPredictions = [None for key in interactions] 
#         lkfOuter = LabelKFold(documentLabels, n_folds=10)
#         outerIndex = 0
#         for train, test in lkfOuter:
#             outerIndex += 1
#             print "Outer loop", outerIndex, (len(train), len(test))
#             trainDocumentLabels = [documentLabels[i] for i in train]
#             train_y = [y_all[i] for i in train]
#             train_X = [X_all[i] for i in train]
#             print "GridSearchCV inner loop, size =", len(trainDocumentLabels)
#             lkfInner = LabelKFold(trainDocumentLabels, n_folds=5)
#             verbose = 0
#             n_jobs = 3
#             metric = "roc_auc"
#             #clf = GridSearchCV(SVC(C=1), {"C":[0.001,0.01,0.1,0.5,1,5,10,100,1000,10000]}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             clf = GridSearchCV(SVC(C=1), {"C":[0.001,0.01,0.1,1,10,100,1000,10000], "kernel":["rbf"]}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs, scoring=metric)
#             #clf = GridSearchCV(SVC(C=1), {"C":[0.001,0.01,0.1,1,10,100,1000,10000], "kernel":["linear", "sigmoid", "rbf", "poly"]}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             #clf = GridSearchCV(ExtraTreesClassifier(), {"n_estimators":[1,2,10,50,100]}, cv=lkfInner)
#             #clf = GridSearchCV(DecisionTreeClassifier(), {"criterion":["gini"]}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             #clf = GridSearchCV(KNeighborsClassifier(), {"n_neighbors":[1, 5, 10, 20, 50, 100, 150, 200]}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             #clf = GridSearchCV(GaussianNB(), {}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             #clf = GridSearchCV(Perceptron(), {}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             #clf = GridSearchCV(GradientBoostingClassifier(), {"n_estimators":[1,2,10,50,100]}, cv=lkfInner)
#             #clf = GridSearchCV(SGDClassifier(), {}, cv=lkfInner)
#             #clf = GridSearchCV(BernoulliNB(), {}, cv=lkfInner)
#             #clf = GridSearchCV(NearestCentroid(), {}, cv=lkfInner, verbose=verbose, n_jobs=n_jobs)
#             clf.fit(train_X, train_y)
#             print "Best params", (clf.best_params_, clf.best_score_)
#             print "Predicting the outer loop test fold"
#             test_X = [X_all[i] for i in test]
#             testPredictions = clf.predict(test_X)
#             for prediction, index in zip(testPredictions, test):
#                 assert learnedPredictions[index] == None
#                 learnedPredictions[index] = prediction
    
#     # Evaluate the performance for the different combination modes
#     if not concise: print "===============", "Performance", "==============="
#     results = []
#     evaluatePerformance(y_all, [-1 if (interactions[key]["a"].get("type") == "neg") else 1 for key in interactions], results, "Performance for dataset a, " + inputA, "A", verbose=not concise)
#     evaluatePerformance(y_all, [-1 if (interactions[key]["b"].get("type") == "neg") else 1 for key in interactions], results, "Performance for dataset b, " + inputB, "B", verbose=not concise)
#     for mode in ("AND", "OR"):
#         evaluatePerformance(y_all, getSimpleCombinedPredictions(interactions, mode), results, "Performance for simple combination " + mode, mode, verbose=not concise)
#     if learning:
#         assert None not in learnedPredictions
#         evaluatePerformance(y_all, learnedPredictions, results, "Outer loop results", "LEARN", verbose=not concise)
#     
#     # Sort the different results by performance
#     print "===============", "Sorted Results", "==============="
#     results = sorted(results, reverse=True)
#     for result in results:
#         print result[0:3]
#     
#     # Save the combined output file
#     if outPath != None:
#         outResult = None
#         print "===============", "Writing Output", "==============="
#         if outMode != None:
#             print "Result '" + str(outMode) + "' will be used for output"
#             for result in results:
#                 if result[1] == outMode:
#                     outResult = result
#                     break
#             if outResult == None:
#                 raise Exception("No result for output mode '" + str(outMode) + "'")
#         else:
#             print "The result with the best performance will be used for output"
#             outResult = results[0]
#         print "Saving result:", outResult[0:3], "to", outPath
#         writeOutput(a, outResult[3], outPath)

if __name__=="__main__":       
    from optparse import OptionParser
    optparser = OptionParser(description="Combine relation predictions (All input files must include both positive and negative interaction elements)")
    optparser.add_option("-a", "--inputA", default=None, dest="inputA", help="First set of predictions in Interaction XML format")
    optparser.add_option("-b", "--inputB", default=None, dest="inputB", help="Second set of predictions in Interaction XML format")
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="Gold interactions in Interaction XML format")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Path to output Interaction XML file (if exists will be overwritten)")
    #optparser.add_option("-l", "--learning", default=False, action="store_true", dest="learning", help="Train a classifier for combining the predictions")
    optparser.add_option("-m", "--mode", default="OR", dest="mode", help="The combination for the output. If none is defined, the best performing one is used.")
    #optparser.add_option("-w", "--write", default="OR", dest="write", help="The combination for the output. If none is defined, the best performing one is used.")
    #optparser.add_option("--concise", default=False, action="store_true", dest="concise", help="")
    (options, args) = optparser.parse_args()
    
    assert options.mode in ("AND", "OR")
    combine(options.inputA, options.inputB, options.gold, options.output, options.mode)