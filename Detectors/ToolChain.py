import sys, os, copy, types
from Detector import Detector
from Core.Model import Model
import Utils.ElementTreeUtils as ETUtils
import Utils.Parameters as Parameters
import Utils.ElementTreeUtils as ETUtils

NOTHING = object()

class ToolChain(Detector):
    def __init__(self):
        Detector.__init__(self)
        # Settings
        self.STATE_TOOLCHAIN = "PROCESS"
        self.steps = []
        for step in self.getDefaultSteps():
            self.addStep(*step)
        self.intermediateFilesAtSource = False
        self.compressIntermediateFiles = True
        self.intermediateFileTag = "temp"
        self.modelParameterStringName = None
    
    def getDefaultSteps(self):
        return []
    
    def getDefaultParameters(self, defaults=None, defaultValue=None):
        if defaults == None:
            defaults = {"omitSteps":None, "intermediateFiles":None}
        for step in self.getDefaultSteps():
            for argName in sorted(step[2].keys()):
                parameterName = step[0] + "." + argName
                if defaultValue == NOTHING:
                    defaults[parameterName] = NOTHING
                else:
                    defaults[parameterName] = defaultValue
        return defaults

    def getParameters(self, parameters=None, model=None, defaultValue=None, modelParameterStringName=None):
        if modelParameterStringName == None:
            modelParameterStringName = self.modelParameterStringName
        if parameters == None and model != None:
            model = self.openModel(model, "r")
            parameters = model.getStr(modelParameterStringName, defaultIfNotExist=None)
        defaultStepNames = [x[0] for x in self.getDefaultSteps()]
        valueLimits={"omitSteps":defaultStepNames + [None], "intermediateFiles":defaultStepNames + [True, None]}
        defaults = self.getDefaultParameters(defaultValue=defaultValue)
        return Parameters.get(parameters, defaults, valueLimits=valueLimits)
    
    def applyParameters(self, parameters):
        self.select.markOmitSteps(parameters["omitSteps"])
        for step in self.steps:
            for argName in sorted(step[2].keys()):
                parameterName = step[0] + "." + argName
                if parameters[parameterName] != NOTHING:
                    step[2][argName] = parameters[parameterName]
            if parameters["intermediateFiles"] != None:
                if parameters["intermediateFiles"] != True and step in parameters["intermediateFiles"]:
                    self.setIntermediateFile(step[0], step[3])
                else:
                    self.setIntermediateFile(step[0], None)
    
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
        
    def setIntermediateFile(self, stepName, filename):
        for s in self.steps:
            if stepName == s[0]:
                if filename == True:
                    filename = s[3]
                elif filename in [False, "None", None]:
                    filename = None
                s[3] = filename
                return
        assert False, (stepName, filename)
    
    def setIntermediateFiles(self, stepToFilename):
        for key in sorted(stepToFilename.keys()):
            self.setIntermediateFile(key, stepToFilename[key])
    
    def setNoIntermediateFiles(self):
        for step in self.steps:
            self.setIntermediateFile(step[0], None)
    
    def getIntermediateFilePath(self, step):
        if step[3] != None:
            if self.intermediateFilesAtSource:
                if type(self.source) in types.StringTypes:
                    firstSource = self.source.split(",") # this may be a list of directories
                    if os.path.isfile(firstSource):
                        rv = firstSource + "-" + step[3]
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
    
    def process(self, input, output, parameters=None, model=None, fromStep=None, toStep=None, omitSteps=None):
        self.initVariables(source=input, xml=input, outDir=os.path.dirname(output))
        if os.path.basename(output) != "":
            self.intermediateFileTag = os.path.basename(output)
        else:
            self.intermediateFileTag = ""
        self.enterState(self.STATE_TOOLCHAIN, [x[0] for x in self.steps], fromStep, toStep, omitSteps)
        parameters = self.getParameters(parameters, model, defaultValue=NOTHING)
        self.applyParameters(parameters)
        # Run the tools
        print >> sys.stderr, "Tool chain parameters:", Parameters.toString(parameters, skipKeysWithValues=[NOTHING], skipDefaults=self.getDefaultParameters())
        if os.path.exists(output) and not os.path.isdir(output):
            print >> sys.stderr, "Removing existing preprocessor output file", output
            os.remove(output)
        savedIntermediate = None # Output from a previous step if "fromStep" is used
        for step in self.steps:
            if self.checkStep(step[0]):
                if savedIntermediate != None: # A previous run of the program saved an intermediate file
                    print >> sys.stderr, "Reading input from saved intermediate file", savedIntermediate
                    self.xml = ETUtils.ETFromObj(savedIntermediate)
                    savedIntermediate = None
                stepArgs = copy.copy(step[2]) # make a copy of the arguments to which i/o can be added
                stepArgs[step[4]["input"]] = self.xml # the input
                if self.getIntermediateFilePath(step) != None: # this step should save an intermediate file
                    stepArgs[step[4]["output"]] = self.getIntermediateFilePath(step)
                print >> sys.stderr, "Running step", step[0], "with arguments", stepArgs
                step[1](**stepArgs) # call the tool
            elif self.getStepStatus(step[0]) == "BEFORE": # this step was run earlier
                savedIntermediate = self.getIntermediateFilePath(step)
        # End state and return
        xml = self.xml # state-specific member variable self.xml will be removed when exiting state
        self.exitState()
        if self.state == None: # if the whole toolchain has finished, return the final product
            if not os.path.isdir(output): # if output is a directory, it was given only for storing intermediate files ...
                ETUtils.write(xml, output) # ... otherwise, save the final output
            return xml
        else:
            return None