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
import atexit, shutil

def workdir(path, deleteIfExists=True):
    if os.path.exists(path):
        if deleteIfExists:
            print >> sys.stderr, "Output directory exists, removing", path
            shutil.rmtree(path)
            os.mkdir(path)
    else:
        os.mkdir(path)
    origDir = os.getcwd()
    os.chdir(path)
    atexit.register(os.chdir, origDir)

def log():
    Stream.setLog("log.txt", True)
    Stream.setTimeStamp("[%H:%M:%S]", True)