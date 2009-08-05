import time

class Timer:
    def __init__(self, startCount=True):
        if startCount:
            self.startTime = time.time()
        else:
            self.startTime = None
        self.totalTime = 0
    
    def stop(self):
        assert(self.startTime != None)
        self.totalTime += time.time() - self.startTime
        self.startTime = None
    
    def start(self):
        assert(self.startTime == None)
        self.startTime = time.time()
        self.endTime = None
    
    def getElapsedTime(self):
        if self.startTime != None:
            now = time.time()
            elapsedTime = now-self.startTime + self.totalTime
        else:
            elapsedTime = self.totalTime
        return elapsedTime
            
    def startTimeToString(self):
        return time.ctime(self.startTime)
    
    def elapsedTimeToString(self):
        elapsedTime = self.getElapsedTime()
        msecs = int(elapsedTime*1000)
        hours = msecs / (3600*1000)
        msecs = msecs % (3600*1000)
        mins = msecs / (60*1000)
        msecs = msecs % (60*1000)
        secs = msecs / (1000)
        msecs = msecs % (1000)
        return str(hours) + ":" + str(mins) + ":" + str(secs) + ":" + str(msecs)
    
    def toString(self):
        return "Time: " + self.elapsedTimeToString() + " (start: " + time.ctime(self.startTime) + ", now: " + time.ctime(time.time()) + ")"

if __name__=="__main__":
    import sys
    timer = Timer()
    print >> sys.stderr, timer.toString()
    time.sleep(1)
    print >> sys.stderr, timer.toString()
    time.sleep(10)
    print >> sys.stderr, timer.toString()
    
