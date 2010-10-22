"""
Main API
"""
import sys,os,time
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Settings
from ExampleBuilders.TriggerExampleBuilder import TriggerExampleBuilder
from ExampleBuilders.MultiEdgeExampleBuilder import MultiEdgeExampleBuilder
from ExampleBuilders.Task3ExampleBuilder import Task3ExampleBuilder
#IF LOCAL
from ExampleBuilders.GeneralEntityTypeRecognizerGztr import GeneralEntityTypeRecognizerGztr
from ExampleBuilders.GeneralEntityTypeRecognizer import GeneralEntityTypeRecognizer
#from ExampleBuilders.EventExampleBuilder import EventExampleBuilder
from ExampleBuilders.DirectEventExampleBuilder import DirectEventExampleBuilder
from ExampleBuilders.PathGazetteer import PathGazetteer
from ExampleBuilders.CPPTriggerExampleBuilder import CPPTriggerExampleBuilder
from ExampleBuilders.UnmergingExampleBuilder import UnmergingExampleBuilder
#from ExampleBuilders.Round2TriggerExampleBuilder import Round2TriggerExampleBuilder
#from ExampleBuilders.BinaryEntityExampleBuilder import BinaryEntityExampleBuilder
from ExampleBuilders.UnmergedEdgeExampleBuilder import UnmergedEdgeExampleBuilder
from ExampleBuilders.AsymmetricEventExampleBuilder import AsymmetricEventExampleBuilder
from Murska.CSCConnection import CSCConnection
#ENDIF
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier as Cls
from Classifiers.AllCorrectClassifier import AllCorrectClassifier as ACCls
#IF LOCAL
#from Classifiers.LibLinearClassifier import LibLinearClassifier
#from Classifiers.LibLinearPoly2Classifier import LibLinearPoly2Classifier
#ENDIF
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator as Ev
from Evaluators.SharedTaskEvaluator import SharedTaskEvaluator as STEv
import Core.SentenceGraph as SentenceGraph
import Core.ExampleUtils as ExampleUtils
import InteractionXML as ix
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
from Core.OptimizeParameters import optimize
from Core.OptimizeParameters import getParameterCombinations
from Core.OptimizeParameters import getCombinationString
import Utils.Stream as Stream
import atexit, shutil
from Core.RecallAdjust import RecallAdjust
from Core.Gazetteer import Gazetteer
from ExampleWriters.BioTextExampleWriter import BioTextExampleWriter
from ExampleWriters.EdgeExampleWriter import EdgeExampleWriter

RELEASE = True
#IF LOCAL
RELEASE = False
#ENDIF

if RELEASE:
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../SharedTask/unflattening")))
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../SharedTask/formatConversion")))
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../SharedTask")))
#IF LOCAL
else:
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../../../../GeniaChallenge/unflattening")))
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../../../../GeniaChallenge/formatConversion")))
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../../../../GeniaChallenge")))
#ENDIF
from unflatten import unflatten

#IF LOCAL
import preserveTask2
#ENDIF
from gifxmlToGenia import gifxmlToGenia
import evaluation.EvaluateSharedTask
evaluateSharedTask = evaluation.EvaluateSharedTask.evaluate
from cElementTreeUtils import write as writeXML

mainProgramDir = None

def workdir(path, deleteIfExists=True):
    global mainProgramDir
    
    if os.path.exists(path):
        if deleteIfExists:
            print >> sys.stderr, "Output directory exists, removing", path
            shutil.rmtree(path)
            os.makedirs(path)
    else:
        os.makedirs(path)
    origDir = os.getcwd()
    os.chdir(path)
    atexit.register(os.chdir, origDir)

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def copyIdSetsToWorkdir(srcStem):
    print >> sys.stderr, "Copying id-sets from", srcStem 
    shutil.copy(srcStem+".feature_names", os.getcwd())
    shutil.copy(srcStem+".class_names", os.getcwd())
    return os.path.split(srcStem)[-1]

# Import Psyco if available
try:
    import psyco
    psyco.full()
    print >> sys.stderr, "Found Psyco, using"
except ImportError:
    print >> sys.stderr, "Psyco not installed"
