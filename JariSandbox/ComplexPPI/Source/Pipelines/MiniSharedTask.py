import sys,os
sys.path.append("..")
import ExampleBuilders.GeneralEntityTypeRecognizer as GeneralEntityTypeRecognizer
import ExampleBuilders.MultiEdgeExampleBuilder as MultiEdgeExampleBuilder
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier as Cls
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator as Ev
import Core.SentenceGraph as SentenceGraph
import Core.ExampleUtils as ExampleUtils
import InteractionXML as ix
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
from Core.OptimizeParameters import optimize
import Utils.Stream as Stream

TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
CLASSIFIER_PARAMS="c:1000,10000,100000"
WORKDIR="/usr/share/biotext/GeniaChallenge/temp"
PARSE_TOK="split-Charniak-Lease"
cwd = os.getcwd()
os.chdir(WORKDIR)
Stream.setLog("log.txt", True)

## Trigger detection
##GeneralEntityTypeRecognizer.run(TRAIN_FILE, "trigger-train-examples", PARSE_TOK, PARSE_TOK, "style:typed", "ids")
##GeneralEntityTypeRecognizer.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", "ids")
#best = optimize(Cls, Ev, "trigger-train-examples", "trigger-test-examples",\
#    "ids.class_names", CLASSIFIER_PARAMS, "trigger-param-opt")
#evaluator = best[0]
#ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-triggers.xml", "ids.class_names", PARSE_TOK, PARSE_TOK)
#ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
#ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)
#
### Edge detection
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
TEST_FILE = "test-predicted-triggers.xml"
CLASSIFIER_PARAMS="c:100,500,1000"
#MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
#MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
#MultiEdgeExampleBuilder.run(GOLD_TEST_FILE, "edge-gold-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
best = optimize(Cls, Ev, "edge-train-examples", "edge-gold-test-examples",\
    "ids.edge.class_names", CLASSIFIER_PARAMS, "edge-param-opt")
Cls.test("edge-test-examples", best[1], "edge-test-classifications")
evaluator = Ev.evaluate("edge-test-examples", "edge-test-classifications", "ids.edge.class_names")
ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-edges.xml", "ids.edge.class_names", PARSE_TOK, PARSE_TOK)
ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
ix.recalculateIds("test-predicted-edges.xml", "test-predicted-edges.xml", True)
EvaluateInteractionXML.run(Ev, "test-predicted-edges.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)

os.chdir(cwd)