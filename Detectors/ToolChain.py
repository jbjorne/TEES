import sys, os#, copy, types
from Detector import Detector
#from Core.Model import Model
import Utils.ElementTreeUtils as ETUtils
#import Utils.Parameters as Parameters
import itertools
import copy

#NOTHING = object()

class Step():
    def __init__(self, name, func, argDict=None, ioArgNames=None, funcCls=None, argListKey=None, group=None):
        self.name = name
        self.func = func
        self.funcCls = funcCls
        self.argDict = argDict if argDict != None else {}
        self.argListKey = argListKey
        self.ioArgNames = ioArgNames if ioArgNames != None else {"input":"input", "output":"output"}
        if self.ioArgNames != None:
            for key in self.ioArgNames:
                if self.ioArgNames[key] not in self.argDict:
                    self.argDict[self.ioArgNames[key]] = None
        self.group = group
    
    def isAlias(self):
        return isinstance(self.func, (list, tuple))
    
    def expandAlias(self):
        if self.isAlias():
            steps = self.func
            steps[0] = steps[0](**{x:self.argDict[x] for x in self.argDict if "x" != "output"})
            steps[-1] = steps[-1](**{"output":self.argDict["output"]})
            return steps
        else:
            return [self]
    
    def setArg(self, name, value):
        assert name in self.argDict
        self.argDict[name] = value
    
    def __call__(self, *args, **kwargs):
        clone = copy.copy(self) # Make a new copy for modifying the arguments of this step "prototype"
        clone.argDict = self.getArgs(*args, **kwargs)
        return clone
    
    def run(self, *args, **kwargs):
        arguments = self.getArgs(*args, **kwargs)
        print >> sys.stderr, "Running step", self.name, "with arguments", arguments
        if self.funcCls == None:
            return self.func(**arguments)
        else:
            return self.func(self.funcCls(), **arguments)
    
    def getArgs(self, *args, **kwargs):
        if len(args) > 0:
            assert self.argListKey != None, (self.argListKey, args, kwargs)
            assert self.argListKey not in kwargs, (self.argListKey, args, kwargs)
            kwargs[self.argListKey] = args
        arguments = self.argDict.copy()
        for argName in kwargs:
            if argName not in arguments:
                raise Exception("Unknown argument '" + argName + "' for step '" + self.name + "'")
            arguments[argName] = kwargs[argName]
        return arguments

class ToolChain(Detector):
    def __init__(self, steps=None):
        Detector.__init__(self)
        # Settings
        self.STATE_TOOLCHAIN = "PROCESS"
        self.group = None
        self.definedSteps = []
        self.definedStepDict = {}
        self.defineSteps()
        self.steps = self.getSteps(steps)
        #self.allSteps = {}
        #self.allStepsList = []
        #self.groups = []
        #self.presets = {}
        #for step in self.getDefaultSteps():
        #    self.addStep(*step)
        self.intermediateFilesAtSource = False
        self.compressIntermediateFiles = True
        self.intermediateFileTag = "temp"
        self.modelParameterStringName = None
    
    def getSteps(self, steps):
        print >> sys.stderr, "Initializing steps:", steps
        if steps == None:
            return []
        for step in self.definedSteps:
            exec(step.name + " = self.definedStepDict['" + step.name + "']")
        if isinstance(steps, basestring):
            steps = eval("[" + steps + "]")
        else:
            steps = [eval(x) if isinstance(x, basestring) else x for x in steps]
        # Alias expansion
        steps = list(itertools.chain(*[x.expandAlias() for x in steps]))
        return steps
    
    def defineSteps(self):
        pass
    
    def defGroup(self, group):
        self.group = group
    
    def defStep(self, name, func, argDict=None, ioArgNames=None, funcCls=None, argListKey=None):
        assert name not in self.definedStepDict
        step = Step(name, func, argDict, ioArgNames, funcCls, argListKey, self.group)
        self.definedStepDict[name] = step
        self.definedSteps.append(step)
    
    def defAlias(self, name, steps):
        assert name not in self.definedStepDict
        steps = [self.definedStepDict[x] for x in steps]
        step = Step(name, steps, None, None, None, None, self.group)
        self.definedStepDict[name] = step
        self.definedSteps.append(step)
    
#     def defineSteps(self, steps):
#         steps = self.expandPresets(steps)
#         for name in steps:
#             if name not in self.allSteps:
#                 raise Exception("Unknown preprocessor step '" + str(name) + "'")
#             step = self.allSteps[name]
#             self.addStep(step["name"], step["function"], step["argDict"], None, step["ioArgNames"])
#             #self.addStep(*([step] + self.allSteps[step][0:2] + [None]))
    
#     def expandPresets(self, steps):
#         newSteps = []
#         for step in steps:
#             if step.startswith("PRESET-"):
#                 assert step in self.presets
#                 newSteps.extend(self.presets[step])
#             else:
#                 newSteps.append(step)
#         return newSteps
#     
#     def initStepGroup(self, name):
#         self.groups.append(name)
    
#     def initStep(self, name, function, argDict, intermediateFile=None, ioArgNames={"input":"input", "output":"output"}):
#         assert name not in self.allSteps
#         self.allSteps[name] = {"name":name, "function":function, "argDict":argDict, "intermediateFile":intermediateFile, "ioArgNames":ioArgNames, "group":len(self.groups) - 1}
#         self.allStepsList.append(self.allSteps[name])
        
    #def getDefaultSteps(self):
    #    return []
    
#     def getDefaultParameters(self, defaults=None, defaultValue=None):
#         if defaults == None:
#             defaults = {"omitSteps":None, "intermediateFiles":None}
#         #valueTypes = {}
#         for step in self.steps: #self.getDefaultSteps():
#             for argName in sorted(step["argDict"].keys()):
#                 parameterName = step["name"] + "." + argName
#                 defaults[parameterName] = defaultValue
#                 #if defaultValue == NOTHING:
#                 #    defaults[parameterName] = NOTHING
#                 #else:
#                 #    defaults[parameterName] = defaultValue
#         return defaults
# 
#     def getParameters(self, parameters=None, model=None, defaultValue=None, modelParameterStringName=None):
#         if modelParameterStringName == None:
#             modelParameterStringName = self.modelParameterStringName
#         if parameters == None and model != None:
#             model = self.openModel(model, "r")
#             parameters = model.getStr(modelParameterStringName, defaultIfNotExist=None)
#         #defaultStepNames = [x[0] for x in self.getDefaultSteps()]
#         stepNames = [x["name"] for x in self.steps]
#         valueLimits={"omitSteps":stepNames + [None], "intermediateFiles":stepNames + [True, None]}
#         defaults = self.getDefaultParameters(defaultValue=defaultValue)
#         return Parameters.get(parameters, defaults, valueLimits=valueLimits)
    
#     def applyParameters(self, parameters):
#         self.select.markOmitSteps(parameters["omitSteps"])
#         for step in self.steps:
#             for argName in sorted(step["argDict"].keys()):
#                 parameterName = step["name"] + "." + argName
#                 if parameterName not in parameters:
#                     raise Exception("Unknown parameter name '" + str(parameterName) + "', parameters are " + str(parameters))
#                 if parameters[parameterName] != NOTHING:
#                     step["argDict"][argName] = parameters[parameterName]
#             if parameters["intermediateFiles"] != None:
#                 if parameters["intermediateFiles"] != True and step in parameters["intermediateFiles"]:
#                     self.setIntermediateFile(step["name"], step["intermediateFile"])
#                 else:
#                     self.setIntermediateFile(step["name"], None)
    
    def hasStep(self, name):
        return name in [x.name for x in self.steps]
    
    def getStep(self, name):
        return [x for x in self.steps if x.name == name][0]
    
#     def addStep(self, name, function, argDict, intermediateFile=None, ioArgNames={"input":"input", "output":"output"}):
#         assert name not in [x["name"] for x in self.steps], (name, self.steps)
#         self.steps.append({"name":name, "function":function, "argDict":argDict, "intermediateFile":intermediateFile, "ioArgNames":ioArgNames})
#     
#     def insertStep(self, index, name, function, argDict, intermediateFile=None, ioArgNames={"input":"input", "output":"output"}):
#         assert name not in [x["name"] for x in self.steps], (name, self.steps)
#         self.steps.insert(index, {"name":name, "function":function, "argDict":argDict, "intermediateFile":intermediateFile, "ioArgNames":ioArgNames})
        
    def setArgForAllSteps(self, argument, value, argMustExist=True):
        for step in self.steps:
            if argMustExist and argument not in step.argDict:
                continue
            step.argDict[argument] = value
    
#     def stepArgs(self, stepName):
#         for step in self.steps:
#             if step == step["name"]:
#                 return step.argDict
#         raise Exception("Step '" + str(step) + "' is not defined")
        
#     def setIntermediateFile(self, stepName, filename):
#         for s in self.steps:
#             if stepName == s["name"]:
#                 if filename == True:
#                     filename = self.allSteps[stepName]["intermediateFile"]
#                 elif filename in [False, "None", None]:
#                     filename = None
#                 s[3] = filename
#                 return
#         assert False, (stepName, filename)
    
#     def setIntermediateFiles(self, stepToFilename):
#         for key in sorted(stepToFilename.keys()):
#             self.setIntermediateFile(key, stepToFilename[key])
    
#     def setIntermediateFiles(self, state):
#         for step in self.steps:
#             self.setIntermediateFile(step["name"], state)
#     
#     def getIntermediateFilePath(self, step):
#         if step["intermediateFile"] != None:
#             if self.intermediateFilesAtSource:
#                 if type(self.source) in types.StringTypes:
#                     firstSource = self.source.split(",") # this may be a list of directories
#                     if os.path.isfile(firstSource):
#                         rv = firstSource + "-" + step["intermediateFile"]
#                     else: # is a directory
#                         rv = os.path.join(firstSource, step["intermediateFile"])
#                 else:
#                     rv = None #filename
#             else:
#                 rv = os.path.join(self.outDir, self.intermediateFileTag + "-" + step[3])
#             if self.compressIntermediateFiles and not rv.endswith(".gz"):
#                 rv += ".gz" 
#             return rv
#         else:
#             return None
    
    def process(self, source, output, model=None, fromStep=None, toStep=None, omitSteps=None):
        #self.initVariables(source=input, xml=input, outDir=os.path.dirname(output))
        if output != None:
            self.initVariables(outDir=os.path.dirname(output))
            if os.path.basename(output) != "":
                self.intermediateFileTag = os.path.basename(output)
            else:
                self.intermediateFileTag = ""
        self.enterState(self.STATE_TOOLCHAIN, [x.name for x in self.steps], fromStep, toStep, omitSteps)
        #parameters = self.getParameters(parameters, model, defaultValue=NOTHING)
        #self.applyParameters(parameters)
        # Run the tools
        #print >> sys.stderr, "Tool chain parameters:", Parameters.toString(parameters, skipKeysWithValues=[NOTHING], skipDefaults=self.getDefaultParameters())
        if output != None and os.path.exists(output) and not os.path.isdir(output):
            print >> sys.stderr, "Removing existing preprocessor output file", output
            os.remove(output)
        savedIntermediate = None # Output from a previous step if "fromStep" is used
        for step in self.steps:
            if self.checkStep(step.name):
                if savedIntermediate != None: # A previous run of the program saved an intermediate file
                    print >> sys.stderr, "Reading input from saved intermediate file", savedIntermediate
                    source = ETUtils.ETFromObj(savedIntermediate)
                    savedIntermediate = None
                stepArgs = {}
                #ioArgNames = {"input":"input", "output":"output"}
                #if step.ioArgNames != None:
                #    ioArgNames = step.ioArgNames
                #stepArgs = copy.copy(step["argDict"]) # make a copy of the arguments to which i/o can be added
                if source != None:
                    stepArgs[step.ioArgNames["input"]] = source # the input
                if step == self.steps[-1]: # The final step in the tool chain should save the final output
                    if "output" in step.ioArgNames: # not all steps have an output argument
                        stepArgs[step.ioArgNames["output"]] = output
#                 elif self.getIntermediateFilePath(step) != None: # This step can save an intermediate file
#                     stepArgs[ioArgNames["output"]] = self.getIntermediateFilePath(step)
                #else:
                #    stepArgs[step.ioArgNames["output"]] = None
                #print >> sys.stderr, "Running step", step.name, "with arguments", stepArgs
                source = step.run(**stepArgs) #source = step["function"](**stepArgs) # call the tool
            elif self.getStepStatus(step["name"]) == "BEFORE": # this step was run earlier
                savedIntermediate = self.getIntermediateFilePath(step)
        # End state and return
        #xml = self.xml # state-specific member variable self.xml will be removed when exiting state
        self.exitState()
        if self.state == None: # if the whole toolchain has finished, return the final product
            #if not os.path.isdir(output): # if output is a directory, it was given only for storing intermediate files ...
            #    ETUtils.write(xml, output) # ... otherwise, save the final output
            return source
        else:
            return None
    
    def save(self, input, output=None):
        xml = ETUtils.ETFromObj(input)
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(input, output)
        return xml