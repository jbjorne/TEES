import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))

# External binaries
SVMMultiClassDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"
#IF NOT RELEASE
CPPTriggerExampleBuilder = os.path.abspath(thisPath + "/../../../GraphIE/exampleTest")
#ENDIF

# BioNLP'09 dataset in XML-format
TrainFile="/usr/share/biotext/GeniaChallenge/xml/train123.xml"
DevelFile="/usr/share/biotext/GeniaChallenge/xml/devel123.xml"
DevelFileWithDuplicates="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates123.xml"
EverythingFile="/usr/share/biotext/GeniaChallenge/xml/everything123.xml"
TestFile="/usr/share/biotext/GeniaChallenge/xml/test.xml"

RELEASE_FILES_PATH = "/usr/share/biotext/GeniaChallenge/CI-release/release-files/release-files-review-version-models/"
# Precalculated SVM-multiclass models
TrainTriggerModel = RELEASE_FILES_PATH + "train-trigger-model-c_100000"
TrainEdgeModel = RELEASE_FILES_PATH + "train-edge-model-c_60000"
TrainSpeculationModel = RELEASE_FILES_PATH + "train-speculation-model-c_13000"
TrainNegationModel = RELEASE_FILES_PATH + "train-negation-model-c_10000"
EverythingTriggerModel = RELEASE_FILES_PATH + "everything-trigger-model-c_100000"
EverythingEdgeModel = RELEASE_FILES_PATH + "everything-edge-model-c_60000"
EverythingSpeculationModel = RELEASE_FILES_PATH + "everything-speculation-model-c_13000"
EverythingNegationModel = RELEASE_FILES_PATH + "everything-negation-model-c_10000"

TriggerIds = RELEASE_FILES_PATH + "genia-trigger-ids"
EdgeIds = RELEASE_FILES_PATH + "genia-edge-ids"
Task3Ids = RELEASE_FILES_PATH + "genia-task3-ids"

# Genia Components
#evaluationsoftware
#gold devel set