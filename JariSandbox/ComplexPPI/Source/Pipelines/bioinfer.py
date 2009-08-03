from Pipeline import *

WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/bioinfer/bioinfer.visible.equalRem-negationRem.stanford-gold"
TRAIN_STEM="bioinfer.visible-1.equalRem-negationRem.stanford-gold"
TEST_STEM="bioinfer.visible-2.equalRem-negationRem.stanford-gold"
TRAIN_FILE="%s/%s.gold.gif.xml"%(WORKDIR,TRAIN_STEM)
TEST_FILE="%s/%s.gold.gif.xml"%(WORKDIR,TEST_STEM)
PARSE="stanford-gold"
CLASSIFIER_PARAMS="c:1000,10000,100000"

# Select a working directory, don't remove existing files
workdir(WORKDIR, False) 
log()

###############################################################################
# Trigger detection
###############################################################################

Gazetteer.run(TRAIN_FILE,
              "%s.gazetteer.dict"%TRAIN_STEM,
              PARSE)
GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE,
                                    "%s.trigger.examples"%TRAIN_STEM,
                                    PARSE,
                                    PARSE,
                                    "style:typed",
                                    "%s.trigger.ids"%TRAIN_STEM,
                                    "%s.gazetteer.dict"%TRAIN_STEM)
GeneralEntityTypeRecognizerGztr.run(TEST_FILE,
                                    "%s.trigger.examples"%TEST_STEM,
                                    PARSE,
                                    PARSE,
                                    "style:typed",
                                    "%s.trigger.ids"%TRAIN_STEM,
                                    "%s.gazetteer.dict"%TRAIN_STEM)
result = optimize(Cls,
                  Ev,
                  "%s.trigger.examples"%TRAIN_STEM,
                  "%s.trigger.examples"%TEST_STEM,
                  "%s.trigger.ids.class_names"%TRAIN_STEM,
                  CLASSIFIER_PARAMS,
                  "%s|%s.trigger.params"%(TRAIN_STEM,TEST_STEM))
evaluator = result[0] # pick the evaluator
ExampleUtils.writeToInteractionXML(evaluator.classifications,
                                   TEST_FILE,
                                   "%s.trigger-pred.gif.xml"%TEST_STEM,
                                   "%s.trigger.ids.class_names"%TRAIN_STEM,
                                   PARSE,
                                   PARSE)
ix.splitMergedElements("%s.trigger-pred.gif.xml"%TEST_STEM,
                       "%s.trigger-pred.gif.xml"%TEST_STEM)
ix.recalculateIds("%s.trigger-pred.gif.xml"%TEST_STEM,
                  "%s.trigger-pred.gif.xml"%TEST_STEM,
                  True)

###############################################################################
# Edge detection
###############################################################################

PRED_FILE = "%s.trigger-pred.gif.xml"%TEST_STEM
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
CLASSIFIER_PARAMS="c:100,500,1000"

MultiEdgeExampleBuilder.run(TRAIN_FILE,
                            "%s.edge.examples"%TRAIN_STEM,
                            PARSE,
                            PARSE,
                            EDGE_FEATURE_PARAMS,
                            "%s.edge.ids"%TRAIN_STEM)
MultiEdgeExampleBuilder.run(PRED_FILE,
                            "%s.edge-pred.examples"%TEST_STEM,
                            PARSE,
                            PARSE,
                            EDGE_FEATURE_PARAMS,
                            "%s.edge.ids"%TRAIN_STEM)
MultiEdgeExampleBuilder.run(TEST_FILE,
                            "%s.edge-gold.examples"%TEST_STEM,
                            PARSE,
                            PARSE,
                            EDGE_FEATURE_PARAMS,
                            "%s.edge.ids"%TRAIN_STEM)
result = optimize(Cls,
                  Ev,
                  "%s.edge.examples"%TRAIN_STEM,
                  "%s.edge-gold.examples"%TEST_STEM,
                  "%s.edge.ids.class_names"%TRAIN_STEM,
                  CLASSIFIER_PARAMS,
                  "%s|%s.edge.params"%(TRAIN_STEM,TEST_STEM))
Cls.test("%s.edge-pred.examples"%TEST_STEM,
         result[1],
         "%s.edge-pred.classifications"%TEST_STEM)
evaluator = Ev.evaluate("%s.edge-pred.examples"%TEST_STEM,
                        "%s.edge-pred.classifications"%TEST_STEM,
                        "%s.edge.ids.class_names"%TRAIN_STEM)
ExampleUtils.writeToInteractionXML(evaluator.classifications,
                                   TEST_FILE,
                                   "%s.trigger-pred.edge-pred.gif.xml"%TEST_STEM,
                                   "%s.edge.ids.class_names"%TRAIN_STEM,
                                   PARSE,
                                   PARSE)
ix.splitMergedElements("%s.trigger-pred.edge-pred.gif.xml"%TEST_STEM,
                       "%s.trigger-pred.edge-pred.gif.xml"%TEST_STEM)
ix.recalculateIds("%s.trigger-pred.edge-pred.gif.xml"%TEST_STEM,
                  "%s.trigger-pred.edge-pred.gif.xml"%TEST_STEM,
                  True)
