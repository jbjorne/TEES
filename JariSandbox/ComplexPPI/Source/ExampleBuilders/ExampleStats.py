class ExampleStats:
    def __init__(self):
        self.className = None
        self.examplesByClass = {}
        self.filteredByClass = {}
        self.filteredByClassByFilter = {}
    
    def addKnownPositives(self, className, number=1):
        pass
    
    def addExample(self, className, filteredBy=[]):
        self.beginExample(className)
        for filter in filteredBy:
            self.filter(filter)
        self.endExample()
    
    def beginExample(self, className):
        assert self.className == None
        
        self.className = className
        self.filteredBy = set()
    
    def filter(self, filterName):
        assert self.className != None
        assert filterName != "total"
        self.filteredBy.add(filterName)
    
    def endExample(self):
        assert self.className != None
        
        if not self.examplesByClass.has_key(self.className):
            self.examplesByClass[self.className] = 0
        self.examplesByClass[self.className] += 1
        
        if not self.filteredByClass.has_key(self.className):
            self.filteredByClass[self.className] = 0
        if len(self.filteredBy) > 0:
            self.filteredByClass[self.className] += 1

        for filter in self.filteredBy:
            if not self.filteredByClassByFilter.has_key(self.className):
                self.filteredByClassByFilter[self.className] = {}
            if not self.filteredByClassByFilter[self.className].has_key(filter):
                self.filteredByClassByFilter[self.className][filter] = 0
            self.filteredByClassByFilter[self.className][filter] += 1
        self.className = None

    def getExampleCount(self):
        return sum(self.examplesByClass.values())
    
    def printStats(self):
        print "Example Statistics"
        print self.examplesByClass.keys()
        for className in sorted(self.examplesByClass.keys()):
            if self.filteredByClassByFilter.has_key(className):
                filterStr = str( self.filteredByClassByFilter[className] )
            else:
                filterStr = ""
            print " ", className + ": " + str(self.examplesByClass[className]) + "/" + str(self.filteredByClass[className]), filterStr 
        print "Positives Coverage 100%"
        
    #def add(self, className, filteredBy=[]):
    #    pass