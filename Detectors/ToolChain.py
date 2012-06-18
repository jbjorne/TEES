import sys, os, copy, types
from Detector import Detector
import cElementTreeUtils as ETUtils

class ToolChain(Detector):
    def __init__(self):
        Detector.__init__(self)
        # Settings
        self.STATE_TOOLCHAIN = "PROCESS"
        self.steps = []
        self.intermediateFilesAtSource = False
        self.compressIntermediateFiles = False
        self.intermediateFileTag = "temp"
    
    def addStep(self, name, function, argDict, intermediateFile=None, ioArgNames={"input":"input", "output":"output"}):
        assert name not in [x[0] for x in self.steps], (name, steps)
        self.steps.append([name, function, argDict, intermediateFile, ioArgNames])
    
    def setArgForAllSteps(self, argument, value, argMustExist=True):
        for step in self.steps:
            if argMustExist and argument not in step[2]:
                continue
            step[2][argument] = value
    
    def stepArgs(self, step):
        for s in self.steps:
            if step == s[0]:
                return s[2]
        assert False
        
    def setIntermediateFile(self, step, filename):
        for s in self.steps:
            if step == s[0]:
                s[3] = filename
                return
        assert False
    
    def setNoIntermediateFiles(self):
        for step in self.steps:
            self.setIntermediateFile(step[0], None)
    
    def getIntermediateFilePath(self, step):
        if step[3] != None:
            if self.intermediateFilesAtSource:
                if type(self.source) in types.StringTypes:
                    firstSource = self.source.split(",") # this may be a list of directories
                    if os.path.isfile(firstSource):
                        rv = self.source + "-" + step[3]
                    else: # is a directory
                        rv = os.path.join(firstSource, step[3])
                else:
                    rv = filename
            else:
                rv = os.path.join(self.outDir, self.intermediateFileTag + "-" + step[3])
            if self.compressIntermediateFiles and not rv.endswith(".gz"):
                rv += ".gz" 
            return rv
        else:
            return None
    
    def process(self, input, outDir, fromStep=None, toStep=None, omitSteps=None):
        self.initVariables(source=input, xml=input, outDir=outDir)
        self.enterState(self.STATE_TOOLCHAIN, [x[0] for x in self.steps], fromStep, toStep, omitSteps)
        # Run the tools
        savedOutput = None # Output from a previous step if "fromStep" is used
        for step in self.steps:
            if self.checkStep(step[0]):
                if savedOutput != None: # A previous run of the program saved an intermediate file
                    self.xml = ETUtils.ETFromObj(savedOutput)
                    savedOutput = None
                stepArgs = copy.copy(step[2]) # make a copy of the arguments to which i/o can be added
                stepArgs[step[4]["input"]] = self.xml # the input
                if self.getIntermediateFilePath(step) != None: # this step should save an intermediate file
                    stepArgs[step[4]["output"]] = self.getIntermediateFilePath(step)
                step[1](**stepArgs) # call the tool
            elif self.getStepStatus(step[0]) == "BEFORE": # this step was run earlier
                savedOutput = self.getIntermediateFilePath(step)
        # End state and return
        xml = self.xml # state-specific member variable self.xml will be removed when exiting state
        self.exitState()
        if self.state == None: # if the whole toolchain has finished, return the final product
            return xml
        else:
            return None