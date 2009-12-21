import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
def relPath(path):
    return os.path.abspath(os.path.join(thisPath, path))

# External binaries
SVMMultiClassDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"

# BioNLP'09 dataset in XML-format
TrainFile = relPath("../data/train123.xml")
DevelFile = relPath("../data/devel123.xml")
EverythingFile = relPath("../data/everything123.xml")
TestFile = relPath("../data/test.xml")

# Precalculated SVM-multiclass models
TrainTriggerModel = relPath("../data/train-trigger-model-c_100000")
TrainEdgeModel = relPath("../data/train-edge-model-c_60000")
EverythingTriggerModel = relPath("../data/everything-trigger-model-c_100000")
EverythingEdgeModel = relPath("../data/everything-edge-model-c_60000")

# Id sets that the precalculated models use
TriggerIds = relPath("../data/genia-trigger-ids")
EdgeIds = relPath("../data/genia-edge-ids")
