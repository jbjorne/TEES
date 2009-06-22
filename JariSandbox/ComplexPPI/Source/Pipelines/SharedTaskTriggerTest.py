from Pipeline import *

TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
CLASSIFIER_PARAMS="c:1000,10000,100000"
optimizeLoop = True
WORKDIR="/usr/share/biotext/GeniaChallenge/SharedTaskTriggerTest"
PARSE_TOK="split-Charniak-Lease"

workdir(WORKDIR, False)
log()

# Trigger detection
GeneralEntityTypeRecognizer.run(TRAIN_FILE, "trigger-train-examples", PARSE_TOK, PARSE_TOK, "style:typed", "trigger-ids")
GeneralEntityTypeRecognizer.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", "trigger-ids")
if optimizeLoop:
    best = optimize(Cls, Ev, "trigger-train-examples", "trigger-test-examples",\
        "trigger-ids.class_names", CLASSIFIER_PARAMS, "trigger-param-opt")
    evaluator = best[0]
else:
    Cls.train("trigger-train-examples", CLASSIFIER_PARAMS, "trigger-model")
    Cls.test("trigger-test-examples", "trigger-model", "trigger-test-classifications")
    evaluator = Ev.evaluate("trigger-test-examples", "trigger-test-classifications", "trigger-ids.class_names")
ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-triggers.xml", "trigger-ids.class_names", PARSE_TOK, PARSE_TOK)
ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)