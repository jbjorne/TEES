import sys
import types
import time, datetime

class StepSelector:
    def __init__(self, steps, fromStep=None, toStep=None, verbose=True, omitSteps=None):
        self.steps = steps
        if type(omitSteps) in types.StringTypes:
            omitSteps = [omitSteps]
        self.omitSteps = omitSteps
        self.currentStep = None
        self.currentStepStartTime = None
        self.setLimits(fromStep, toStep)
        self.verbose = verbose
    
    def markOmitSteps(self, steps):
        if self.omitSteps == None:
            self.omitSteps = []
        if type(steps) not in [types.ListType, types.TupleType]:
            steps = [steps]
        for step in steps:
            if step not in self.omitSteps:
                self.omitSteps.append(step)
    
    def setLimits(self, fromStep, toStep):
        self.fromStep = fromStep
        self.toStep = toStep
        self.doSteps = None
        if self.fromStep != None and (type(self.fromStep) == types.ListType or "," in self.fromStep):
            self.doSteps = self.fromStep
            if type(self.doSteps) != types.ListType:
                self.doSteps = self.doSteps.split(",")
                if self.doSteps[-1].strip() == "":
                    self.doSteps = self.doSteps[:-1]
            self.fromStep = None
            for step in self.doSteps:
                assert step in self.steps, (step, self.steps)
        elif self.fromStep != None:
            assert self.fromStep in self.steps, (self.fromStep, self.steps)
        if self.toStep != None:
            assert self.toStep in self.steps, (self.toStep, self.steps)
    
#    def getSharedStep(self, step, allSteps, direction=1):
#        allStepsIndex = allSteps.inxed(step)
#        while allSteps[allStepsIndex] not in self.steps:
#            allStepsIndex += direction
#            assert allStepsIndex > 0 and allStepsIndex < len(allSteps), (allStepsIndex, allSteps, self.steps)
#        assert allSteps[allStepsIndex] in self.steps
#        return allSteps[allStepsIndex]
    
    def printStepTime(self):
        if self.currentStep != None and self.currentStepStartTime != None:
            print >> sys.stderr, "===", "EXIT STEP", self.currentStep + ": " + str(datetime.timedelta(seconds=time.time()-self.currentStepStartTime)), "==="
    
    def getStepStatus(self, step):
        if self.omitSteps != None and step in self.omitSteps:
            return "OMIT"
        stepIndex = self.steps.index(step)
        # Get range
        fromIndex = 0
        if self.fromStep != None: 
            fromIndex = self.steps.index(self.fromStep)
        toIndex = len(self.steps) - 1
        if self.toStep != None: 
            toIndex = self.steps.index(self.toStep)
        # Determine if step is in range
        if stepIndex < fromIndex:
            return "BEFORE"
        if stepIndex > toIndex:
            return "AFTER"
        return "PROCESS"
    
    def check(self, step):
        #print "CHECK", step, self.currentStep, self.steps, self.fromStep, self.toStep
        assert step in self.steps
        assert self.fromStep == None or self.fromStep in self.steps, (self.fromStep, self.toStep, self.steps)
        assert self.toStep == None or self.toStep in self.steps, (self.fromStep, self.toStep, self.steps)
        if self.doSteps != None:
            for s in self.doSteps:
                assert s in self.steps, (a, self.steps)
        
        stepIndex = self.steps.index(step)
        # Get current index
        currentIndex = -1
        if self.currentStep != None:
            currentIndex = self.steps.index(self.currentStep)
        #assert stepIndex == currentIndex + 1, (step, self.currentStep, self.steps)
        # Get range
        fromIndex = 0
        if self.fromStep != None: 
            fromIndex = self.steps.index(self.fromStep)
        toIndex = len(self.steps) - 1
        if self.toStep != None: 
            toIndex = self.steps.index(self.toStep)
        # Determine if step is in range
        if stepIndex >= fromIndex and stepIndex <= toIndex:
            if currentIndex < stepIndex:
                if self.currentStepStartTime != None:
                    if self.verbose: print >> sys.stderr, "===", "EXIT STEP", self.currentStep, "time:", str(datetime.timedelta(seconds=time.time()-self.currentStepStartTime)), "==="
                self.currentStep = step
                self.currentStepStartTime = time.time()
                if self.omitSteps != None and step in self.omitSteps:
                    if self.verbose: print >> sys.stderr, "Omitting step", step
                    return False
                else:
                    return True
            else:
                if self.verbose: print >> sys.stderr, "Step", step, "already done, skipping."
                return False
        else:
            if self.verbose: print >> sys.stderr, "Step", step, "out of range"
            return False
        
        assert False
        
#        # Remember step ###########################################
#        if self.currentStep == None:
#            self.currentStep = step
#        elif self.steps.index(step) <= self.steps.index(self.currentStep):
#            print >> sys.stderr, "Step", step, "already done, skipping."
#            return False
#        else:
#            self.currentStep = step
#        
#        # User control ###########################################
#        # List control
#        if self.doSteps != None:
#            if step in self.doSteps:
#                if self.toStep == None:
#                    return True
#                else:
#                    assert self.toStep in self.steps
#                    if self.steps.index(self.toStep) >= self.steps.index(step):
#                        return True
#                    else:
#                        print >> sys.stderr, "Step", step, "out of range"
#                        return False
#            else:
#                print >> sys.stderr, "Skipping step", step, "by user request"
#                return False
#            
#        # From-to control
#        if self.fromStep == None and self.toStep == None:
#            return True
#        elif self.fromStep != None:
#            assert self.fromStep in self.steps
#            if self.steps.index(self.fromStep) <= self.steps.index(step):
#                if self.toStep == None:
#                    return True
#                assert self.toStep in self.steps
#                if self.steps.index(self.toStep) >= self.steps.index(step):
#                    return True
#                else:
#                    print >> sys.stderr, "Step", step, "out of range"
#                    return False
#            else:
#                print >> sys.stderr, "Skipping step", step, "by user request"
#                return False
#        else: # toStep != None
#            assert self.toStep in self.steps
#            if self.steps.index(self.toStep) >= self.steps.index(step):
#                return True
#            else:
#                print >> sys.stderr, "Step", step, "out of range"
#                return False