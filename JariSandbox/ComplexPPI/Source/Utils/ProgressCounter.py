import sys

class ProgressCounter:
    def __init__(self, total, id="UNKNOWN"):
        self.total = float(total)
        self.current = 0
        self.progress = 0.0
        self.prevProgress = -99.0
        self.id = id
        self.prevUpdateString = "None"
    
    def __del__(self):
        # If this counter didn't finish, show the info about the last update
        if not self.progress >= 100.0:
            import sys
            print >> sys.stderr, "Counter \"" + self.id + "\" did not finish, count: " + str(self.current) + "/" + str(int(self.total))
            print >> sys.stderr, "Last update: " + self.prevUpdateString 
    
    def update(self, amount=1, string="Processing: "):
        self.current += amount
        self.progress = self.current / self.total * 100.0
        self.prevUpdateString = string + "%.2f" % self.progress + " %"
        if self.progress >= 100.0 or self.progress - self.prevProgress >= 5.0:
            print >> sys.stderr, "\r" + self.prevUpdateString,
            self.prevProgress = self.progress
        if self.progress >= 100.0:
            print >> sys.stderr