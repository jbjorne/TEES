import sys
import types

class StepSelector:
    def __init__(self, steps, fromStep=None, toStep=None, verbose=True):
        self.steps = steps
        self.currentStep = None
        self.setLimits(fromStep, toStep)
        self.verbose = verbose
    
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
    
    def check(self, step):
        #print "CHECK", step, self.currentStep, self.steps, self.fromStep, self.toStep
        assert step in self.steps
        stepIndex = self.steps.index(step)
        # Get current index
        currentIndex = -1
        if self.currentStep != None:
            currentIndex = self.steps.index(self.currentStep)
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
                self.currentStep = step
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