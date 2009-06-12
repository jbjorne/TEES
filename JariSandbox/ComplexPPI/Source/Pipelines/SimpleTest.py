import sys,os
sys.path.append("..")
import shutil
import ExampleBuilders.GeneralEntityTypeRecognizer as TriggerExampleBuilder

def optimizeParameters(workdir, trainSet, testSet):
    

def runPipeline(workdir):
    TriggerExampleBuilder.run(gifxmlfile, "examples", workdir)
    DivideExamples.divide("examples", workdir, 10)