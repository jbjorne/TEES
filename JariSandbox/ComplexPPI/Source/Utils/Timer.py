import time

class Timer:
    def __init__(self):
        self.startTime = time.time()
        self.endTime = None
    
    def stop(self):
        self.endTime = time.time()
    
    def startTimeToString(self):
        return time.ctime(self.startTime)
    
    def elapsedTimeToString(self):
        if self.endTime == None:
            now = time.time()
        else:
            now = self.endTime
        secs = int(now-self.startTime)
        hours = secs / 3600
        secs = secs % 3600
        mins = secs / 60
        secs = secs % 60
        return str(hours) + ":" + str(mins) + ":" + str(secs)
    
    def toString(self):
        return "Time: " + self.elapsedTimeToString() + " (start: " + time.ctime(self.startTime) + ", now: " + time.ctime(time.time()) + ")"

if __name__=="__main__":
    import sys
    timer = Timer()
    print >> sys.stderr, timer.toString()
    time.sleep(10)
    print >> sys.stderr, timer.toString()
