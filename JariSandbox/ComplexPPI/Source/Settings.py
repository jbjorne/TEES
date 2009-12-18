import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))

# External binaries
SVMMultiClassDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"
#IF NOT RELEASE
CPPTriggerExampleBuilder = os.path.abspath(thisPath + "/../../../GraphIE/exampleTest")
#ENDIF

# BioNLP'09 dataset in XML-format
TrainFile="/usr/share/biotext/GeniaChallenge/xml/train12-mini.xml"
DevelFile="/usr/share/biotext/GeniaChallenge/xml/devel12-mini.xml"
EverythingFile="/usr/share/biotext/GeniaChallenge/xml/everything123.xml"
TestFile="/usr/share/biotext/GeniaChallenge/xml/test.xml"

# Precalculated SVM-multiclass models
TrainTriggerModel="/usr/share/biotext/GeniaChallenge/release-files/train-trigger-model-c_100000"
TrainEdgeModel="/usr/share/biotext/GeniaChallenge/release-files/train-edge-model-c_60000"
EverythingTriggerModel="/usr/share/biotext/GeniaChallenge/release-files/everything-trigger-model-c_100000"
EverythingEdgeModel="/usr/share/biotext/GeniaChallenge/release-files/everything-edge-model-c_60000"

TriggerIds="/usr/share/biotext/GeniaChallenge/release-files/genia-trigger-ids"
EdgeIds="/usr/share/biotext/GeniaChallenge/release-files/genia-edge-ids"

# Genia Components
#evaluationsoftware
#gold devel set