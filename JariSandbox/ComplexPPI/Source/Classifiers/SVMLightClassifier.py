import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
from Classifiers.JoachimsSVMBase import JoachimsSVMBase
import copy
import time
import killableprocess
import types

class SVMLightClassifier(JoachimsSVMBase):
    def __init__(self, workDir=None):
        JoachimsSVMBase.__init__(self, workDir=workDir)
        self.trainBin = "/usr/share/biotext/ComplexPPI/SVMLight/svm_learn"
        self.classifyBin = "/usr/share/biotext/ComplexPPI/SVMLight/svm_classify"
        self.type = "binary"
        self.defaultEvaluator = "BinaryEvaluator"