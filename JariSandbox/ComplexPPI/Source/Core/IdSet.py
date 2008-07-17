class IdSet:    
    def __init__(self, firstNumber=1):
        self.Ids = {}
        self.firstNumber = firstNumber

    def getId(self, name):
        if not self.Ids.has_key(name):
            self.Ids[name] = len(self.Ids) + self.firstNumber
        return self.Ids[name]
    
    def getName(self, id):
        for k, v in self.Ids:
            if v == id:
                return k
            else:
                return None
    
    def write(self, filename):
        f = open(filename, "wt")
        keys = self.Ids.keys()
        keys.sort()
        for key in keys:
            f.write(str(key)+": "+str(self.Ids[key])+"\n")
        f.close()
    
    def toStrings(self, rowLength=80):
        strings = [""]
        keys = self.Ids.keys()
        keys.sort()
        currLen = 0
        for key in keys:
            pair = str(key)+":"+str(self.Ids[key])
            currLen += len(pair) + 1
            if currLen > rowLength:
                currLen = 0
                strings.append("")
            if strings[-1] != "":
                strings[-1] += ";"
            strings[-1] += pair
        return strings
    
    def load(self, filename):
        self.Ids = {}
        self.firstNumber = 0
        
        f = open(filename, "rt")
        lines = f.readlines()
        f.close()
        for line in lines:
            key, value = line.split(":")
            key = key.strip()
            value = int(value.strip())
            if self.firstNumber > value:
                self.firstNumber = value
            self.Ids[key] = value
