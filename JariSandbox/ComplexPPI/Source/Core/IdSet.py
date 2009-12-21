import codecs

class IdSet:    
    def __init__(self, firstNumber=1, idDict=None, locked=False, filename=None):
        self.Ids = {}
        self.nextFreeId = firstNumber
        self._namesById = {}
        
        if idDict != None:
            self.locked = False
            self.nextFreeId = 999999999
            for name,id in idDict.iteritems():
                self.defineId(name, id)
            self.nextFreeId = max(self.Ids.values())+1
        self.locked = locked
        
        if filename != None:
            self.load(filename)
    
    def getId(self, key, createIfNotExist=True):
        if not self.Ids.has_key(key):
            if self.locked or createIfNotExist == False:
                return None
            id = self.nextFreeId
            self.nextFreeId += 1
            #assert(not id in self.Ids.values())
            self.Ids[key] = id
            self._namesById[id] = key
        return self.Ids[key]
    
    def __getitem__( self, name ):
        return getId(name)
    
    def defineId(self, name, id):
        assert(not self.locked)
        assert(not id in self.Ids.values())
        assert(not name in self.Ids.keys())
        assert(id < self.nextFreeId)
        self.Ids[name] = id
        self._namesById[id] = name
    
    def getName(self, id):
        if self._namesById.has_key(id):
            return self._namesById[id]
        else:
            return None
    
    def getNames(self):
        names = self.Ids.keys()
        names.sort()
        return names
    
    def getIds(self):
        values = self.Ids.values()
        values.sort()
        return values
    
    def write(self, filename):
        f = codecs.open(filename, "wt", "utf-8")
        keys = self.Ids.keys()
        keys.sort()
        for key in keys:
            f.write( (str(key)+": "+str(self.Ids[key])+"\n") )
            #f.write( (str(key)+": "+str(self.Ids[key])+"\n").encode("utf-8") )
        f.close()
    
    def load(self, filename):
        self.Ids = {}
        self._namesById = {}
        self.nextFreeId = -999999999999999999
        
        f = codecs.open(filename, "rt", "utf-8")
        lines = f.readlines()
        f.close()
        for line in lines:
            key, value = line.rsplit(":",1)
            key = key.strip()
            value = int(value.strip())
            if value >= self.nextFreeId:
                self.nextFreeId = value + 1
            self.Ids[key] = value
            self._namesById[value] = key
