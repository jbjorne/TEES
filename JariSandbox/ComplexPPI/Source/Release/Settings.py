"""
File paths
"""

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
def relPath(path):
    return os.path.abspath(os.path.join(thisPath, path))

# External binaries
SVMMultiClassDir = None

# BioNLP'09 dataset in XML-format (merged for task 1&2)
TrainFile = relPath("../data/train123.xml")
DevelFile = relPath("../data/devel123.xml")
EverythingFile = relPath("../data/everything123.xml")
TestFile = relPath("../data/test.xml") # doesn't have any annotation that could be merged/unmerged

# BioNLP'09 dataset in XML-format (unmerged for task 3)
TrainFileWithDuplicates = relPath("../data/train-with-duplicates123.xml")
DevelFileWithDuplicates = relPath("../data/devel-with-duplicates123.xml")
EverythingFileWithDuplicates = relPath("../data/everything-with-duplicates123.xml")

# Precalculated SVM-multiclass models
TrainTriggerModel = relPath("../data/train-trigger-model-c_200000")
TrainEdgeModel = relPath("../data/train-edge-model-c_28000")
TrainSpeculationModel = relPath("../data/train-speculation-model-c_13000")
TrainNegationModel = relPath("../data/train-negation-model-c_10000")
EverythingTriggerModel = relPath("../data/everything-trigger-model-c_200000")
EverythingEdgeModel = relPath("../data/everything-edge-model-c_28000")
EverythingSpeculationModel = relPath("../data/everything-speculation-model-c_13000")
EverythingNegationModel = relPath("../data/everything-negation-model-c_10000")

# Id sets that the precalculated models use
TriggerIds = relPath("../data/genia-trigger-ids")
EdgeIds = relPath("../data/genia-edge-ids")
Task3Ids = relPath("../data/genia-task3-ids")
