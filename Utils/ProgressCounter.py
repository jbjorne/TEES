import sys, time

class ProgressCounter:
    def __init__(self, total=None, id="UNKNOWN", step=None):
        self.total = total
        if self.total != None:
            self.total = float(self.total)
        self.current = 0
        self.progress = 0.0
        self.prevProgress = -99.0
        self.id = id
        self.prevUpdateString = "None"
        self.step = step
        if total != None and step == None:
            self.step = 5.0 # If the total is known, update at 5 percentage point intervals
        self.showMilliseconds = False
        
        self.prevPrintTime = 0
        self.timeStep = 30
        self.startTime = time.time()
        self.prevUpdateStringLen = 0
    
    def endUpdate(self):
        if self.total == None:
            print >> sys.stderr, ""
    
    def markFinished(self):
        """
        Mark as finished to suppress the error message, regardless of actual status
        """
        self.progress = 100.0
    
    def __del__(self):
        # If this counter didn't finish, show the info about the last update
        if self.total != None and not self.progress >= 100.0:
            import sys
            print >> sys.stderr, "Counter \"" + self.id + "\" did not finish"
            self.showLastUpdate()
            
    def update(self, amount=1, string="Processing: "):
        self.current += amount
        if self.total != None:
            self.progress = self.current / self.total * 100.0
            self.prevUpdateString = string + "%.2f" % self.progress + " %"
        else:
            self.progress += amount
            self.prevUpdateString = string + str(self.current)
        
        currentTime = time.time()
        timeStepExceeded = currentTime - self.prevPrintTime > self.timeStep
        stepExceeded = self.step == None or (self.progress - self.prevProgress >= self.step)
        
        self.prevUpdateString += " (" + self.getElapsedTimeString(currentTime) + ")"
        
        if self.total != None:
            if self.progress >= 100.0 or stepExceeded or timeStepExceeded:
                print >> sys.stderr, "\r" + self.prevUpdateString + max(0, self.prevUpdateStringLen-len(self.prevUpdateString)) * " ",
                self.prevProgress = self.progress
                self.prevPrintTime = currentTime
                self.prevUpdateStringLen = len(self.prevUpdateString)
            if self.progress >= 100.0:
                print >> sys.stderr
        else:
            if stepExceeded or timeStepExceeded:
                self.progress = 0
                print >> sys.stderr, "\r" + self.prevUpdateString + max(0, self.prevUpdateStringLen-len(self.prevUpdateString)) * " ",
                self.prevProgress = self.progress
                self.prevPrintTime = currentTime
                self.prevUpdateStringLen = len(self.prevUpdateString)
    
    def getElapsedTimeString(self, currentTime):
        elapsedTime = currentTime - self.startTime
        hours = elapsedTime / 3600.0
        elapsedTime = elapsedTime % 3600.0
        minutes = elapsedTime / 60.0
        seconds = elapsedTime % 60.0
        if self.showMilliseconds:
            seconds = "%.3f" % seconds
        else:
            seconds = str(int(seconds))
        return str(int(hours)) + ":" + str(int(minutes)) + ":" + seconds
    
    def showLastUpdate(self):
        if self.total != None:
            print >> sys.stderr, "Last count: " + str(self.current) + "/" + str(int(self.total))
        else:
            print >> sys.stderr, "Last count: " + str(self.current)
        print >> sys.stderr, "Last update: " + self.prevUpdateString 
        