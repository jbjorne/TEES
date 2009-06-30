import sys,os
sys.path.append("..")
from ExampleBuilders.GeneralEntityTypeRecognizerGztr import GeneralEntityTypeRecognizer
import ExampleBuilders.MultiEdgeExampleBuilder as MultiEdgeExampleBuilder
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier as Cls
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator as Ev
import Core.SentenceGraph as SentenceGraph
import Core.ExampleUtils as ExampleUtils
import InteractionXML as ix
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
from Core.OptimizeParameters import optimize
import Utils.Stream as Stream
import atexit, shutil
from Core.RecallAdjust import RecallAdjust
from Core.Gazetteer import Gazetteer

from Pipeline import workdir, log


TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
CLASSIFIER_PARAMS="c:25000,50000,87500"
WORKDIR="/usr/share/biotext/GeniaChallenge/SharedTaskTriggerTest"
PARSE_TOK="split-Charniak-Lease"

workdir(WORKDIR, False)
log()


# Trigger detection

#Gazetteer.run(TRAIN_FILE, "gazetteer-train")
#GeneralEntityTypeRecognizer.run(TRAIN_FILE, "trigger-train-examples", PARSE_TOK, PARSE_TOK, "style:typed", "trigger-ids")

GeneralEntityTypeRecognizer.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", "trigger-ids")
Cls.test("trigger-test-examples", "trigger-param-opt/model-c_75000", "trigger-test-classifications")
evaluator = Ev.evaluate("trigger-test-examples", "trigger-test-classifications", "trigger-ids.class_names")

#evaluator = optimize(Cls, Ev, "trigger-train-examples", "trigger-test-examples",\
#    "trigger-ids.class_names", CLASSIFIER_PARAMS, "trigger-param-opt")[0]

ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-triggers.xml", "trigger-ids.class_names", PARSE_TOK, PARSE_TOK)

# RecallAdjust.run("test-predicted-triggers.xml",1.0,"test-predicted-triggers-adj.xml")
# ix.splitMergedElements("test-predicted-triggers-adj.xml", "test-predicted-triggers-adj-split.xml")
# ix.recalculateIds("test-predicted-triggers-adj-split.xml", "test-predicted-triggers-adj-split-recids.xml", True)
# EvaluateInteractionXML.run(Ev, "test-predicted-triggers-adj-split-recids.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)

ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers-split.xml")
ix.recalculateIds("test-predicted-triggers-split.xml", "test-predicted-triggers-split-recids.xml", True)
EvaluateInteractionXML.run(Ev, "test-predicted-triggers-split-recids.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)
