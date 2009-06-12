import sys,os
sys.path.append("..")
import ExampleBuilders.GeneralEntityTypeRecognizer as GeneralEntityTypeRecognizer
import ExampleBuilders.MultiEdgeExampleBuilder as MultiEdgeExampleBuilder
import Classifiers.SVMMultiClassClassifier as SVMMultiClassClassifier
import Evaluators.AveragingMultiClassEvaluator as AveragingMultiClassEvaluator
import Core.SentenceGraph as SentenceGraph
import Core.ExampleUtils as ExampleUtils
import InteractionXML.RecalculateIds as RecalculateIds
import InteractionXML.SplitMergedElements as SplitMergedElements
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML

TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
CLASSIFIER_PARAMS="c:1000,10000,100000,1000000;timeout:600"
WORKDIR="/usr/share/biotext/GeniaChallenge/temp"
PARSE_TOK="split-Charniak-Lease"
cwd = os.getcwd()
os.chdir(WORKDIR)

# Trigger detection
#if os.path.exists("ids.class_names"): os.remove("ids.class_names")
#if os.path.exists("ids.feature_names"): os.remove("ids.feature_names")
#GeneralEntityTypeRecognizer.run(TRAIN_FILE, "trigger-train-examples", PARSE_TOK, PARSE_TOK, "style:typed", "ids")
#GeneralEntityTypeRecognizer.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", "ids")
#SVMMultiClassClassifier.train("trigger-train-examples", {"c":1000}, "trigger-model", "trigger-train")
#SVMMultiClassClassifier.test("trigger-test-examples", None, "trigger-model", "trigger-test-classifications", "trigger-test")
#evaluator = AveragingMultiClassEvaluator.run("trigger-test-examples", "trigger-test-classifications", "ids.class_names", "trigger-evaluation.csv")
#corpusElements = SentenceGraph.loadCorpus(TEST_FILE, PARSE_TOK, PARSE_TOK)
#ExampleUtils.writeToInteractionXML(evaluator.classifications, corpusElements, "test-predicted-triggers.xml", "ids.class_names")
#SplitMergedElements.run("test-predicted-triggers.xml", "test-predicted-triggers.xml")
#RecalculateIds.run("test-predicted-triggers.xml", "test-predicted-triggers.xml")


# Edge detection
#EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
TEST_FILE = "test-predicted-triggers.xml"
#if os.path.exists("ids.edge.class_names"): os.remove("ids.edge.class_names")
#if os.path.exists("ids.edge.feature_names"): os.remove("ids.edge.feature_names")
#MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
#MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
#SVMMultiClassClassifier.train("edge-train-examples", {"c":1000}, "edge-model", "edge-train")
#SVMMultiClassClassifier.test("edge-test-examples", None, "edge-model", "edge-test-classifications", "edge-test")
#evaluator = AveragingMultiClassEvaluator.run("edge-test-examples", "edge-test-classifications", "ids.edge.class_names", "edge-evaluation.csv")
#corpusElements = SentenceGraph.loadCorpus(TEST_FILE, PARSE_TOK, PARSE_TOK)
#ExampleUtils.writeToInteractionXML(evaluator.classifications, corpusElements, "test-predicted-edges.xml", "ids.edge.class_names")
#SplitMergedElements.run("test-predicted-edges.xml", "test-predicted-edges.xml")
#RecalculateIds.run("test-predicted-edges.xml", "test-predicted-edges.xml")
EvaluateInteractionXML.run(AveragingMultiClassEvaluator.AveragingMultiClassEvaluator, GOLD_TEST_FILE, "test-predicted-edges.xml", PARSE_TOK, PARSE_TOK)


os.chdir(cwd)