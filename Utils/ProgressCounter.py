import sys, time

class ProgressCounter:
    def __init__(self, total, id="UNKNOWN", step=5.0):
        self.total = total
        if self.total != None:
            self.total = float(self.total)
        self.current = 0
        self.progress = 0.0
        self.prevProgress = -99.0
        self.id = id
        self.prevUpdateString = "None"
        self.step = step
        self.showMilliseconds = False
        
        self.prevPrintTime = 0
        self.timeStep = 30
        self.startTime = time.time()
        self.prevUpdateStringLen = 0
    
    def markFinished(self):
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
        timeStepExceeded = False
        if currentTime - self.prevPrintTime > self.timeStep:
            timeStepExceeded = True
        
        self.prevUpdateString += " (" + self.getElapsedTimeString(currentTime) + ")"
        
        if self.total != None:
            if self.progress >= 100.0 or self.progress - self.prevProgress >= self.step or timeStepExceeded:
                print >> sys.stderr, "\r" + self.prevUpdateString + max(0, self.prevUpdateStringLen-len(self.prevUpdateString)) * " ",
                self.prevProgress = self.progress
                self.prevPrintTime = currentTime
                self.prevUpdateStringLen = len(self.prevUpdateString)
            if self.progress >= 100.0:
                print >> sys.stderr
        else:
            if self.progress >= self.step:
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
        