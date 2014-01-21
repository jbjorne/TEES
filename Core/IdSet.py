"""
Manages classification class and feature ids.
"""
__version__ = "$Revision: 1.20 $"

import codecs
import gzip

class IdSet:
    """
    A mapping from strings to id integers. This class is used for defining the ids for classes
    and features of machine learning systems.
    """ 
    def __init__(self, firstNumber=1, idDict=None, locked=False, filename=None, allowNewIds=True):
        """
        Creates a new IdSet or loads one from a dictionary or a file.
        
        To create a new, empty set: idset = IdSet(firstNumber = x). 
        To create a set from a str->int dictionary: idset = IdSet(idDict = x). 
        To load a dictionary from a file: idset = IdSet(filename = x).
        
        @param firstNumber: The number given to the first name defined. Subsequent names will
        have higher numbers.
        @type firstNumber: int
        @param idDict: Dictionary of name / integer pairs. The integer values must be unique.
        @type idDict: dictionary
        @param locked: Whether new names can be added to the set. If set to True, getId will
        return None for names that are not already in the set.
        @type locked: boolean
        @param filename: load name/id pairs from a file
        @type filename: str
        """
        self.Ids = {}
        self.nextFreeId = firstNumber
        self._namesById = {}
        self.allowNewIds = allowNewIds # allow new ids when calling getId without specifying "createIfNotExist"
        
        if idDict != None:
            self.locked = False
            self.nextFreeId = 999999999
            for name,id in idDict.iteritems():
                self.defineId(name, id)
            self.nextFreeId = max(self.Ids.values())+1
        self.locked = locked
        
        if filename != None:
            self.load(filename)
    
    def getId(self, key, createIfNotExist=None):
        """
        Returns the id number for a name. If the name doesn't already have an id, a new id is defined,
        unless createIfNotExist is set to false, in which case None is returned for these cases.
        
        @type key: str
        @param key: name
        @type createIfNotExist: True, False or None
        @param createIfNotExist: If the name doesn't have an id, define an id for it
        @rtype: int or None
        @return: an identifier
        """
        if createIfNotExist == None: # no local override to object level setting
            createIfNotExist = self.allowNewIds
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
        """
        Calls getId through the []-operator.
        """
        return self.getId(name)
    
    def defineId(self, name, id):
        """
        Give a specific id for a certain name. Neither the name nor the id must exist in the set
        and the id must be smaller than the largest id already in the set. Usually this method
        is used only when inserting name/id pairs from an existing source.
        """
        assert(not self.locked)
        assert(not id in self.Ids.values())
        assert(not name in self.Ids.keys())
        assert(id < self.nextFreeId)
        self.Ids[name] = id
        self._namesById[id] = name
    
    def getName(self, id):
        """
        Returns the name corresponding to the identifier. If the identifier doesn't exits, returns None.
        
        @param id: the identifier number
        @type id: int
        @rtype: str or None
        @return: a name
        """
        if self._namesById.has_key(id):
            return self._namesById[id]
        else:
            return None
    
    def getNames(self):
        """
        Returns a sorted list of all names. Can be slow for large IdSets.
        """
        names = self.Ids.keys()
        names.sort()
        return names
    
    def getIds(self):
        """
        Returns a sorted list of id numbers. Can be slow for large IdSets.
        """
        values = self.Ids.values()
        values.sort()
        return values
    
    def write(self, filename):
        """
        Writes the name/id pairs to a file, one pair per line, in the format "name: id".
        """
        #f = codecs.open(filename, "wt", "utf-8")
        if filename.endswith(".gz"):
            f = gzip.open(filename, 'wt')
            writer = codecs.getwriter("utf-8")(f)
        else:
            writer = codecs.open(filename, "wt", "utf-8")
            f = writer
        
        keys = self.Ids.keys()
        keys.sort()
        for key in keys:
            # key is assumed to be a string
            writer.write( key + ": " + str(self.Ids[key]) + "\n" )
            #f.write( (str(key)+": "+str(self.Ids[key])+"\n") ) # this causes unicode problems
            #f.write( (str(key)+": "+str(self.Ids[key])+"\n") )
            #f.write( (str(key)+": "+str(self.Ids[key])+"\n").encode("utf-8") )
        f.close()
    
    def load(self, filename):
        """
        Loads name/id pairs from a file. The IdSet is cleared of all existing ids before
        loading the ones from the file.
        """
        self.Ids = {}
        self._namesById = {}
        self.nextFreeId = -999999999999999999
        
        #f = codecs.open(filename, "rt", "utf-8")
        if filename.endswith(".gz"):
            f = gzip.open(filename, 'rt')
            reader = codecs.getreader("utf-8")(f)
        else:
            reader = codecs.open(filename, "rt", "utf-8")
            f = reader
        lines = reader.readlines()
        f.close()

        for line in lines:
            key, value = line.rsplit(":",1)
            key = key.strip()
            value = int(value.strip())
            if value >= self.nextFreeId:
                self.nextFreeId = value + 1
            self.Ids[key] = value
            self._namesById[value] = key
