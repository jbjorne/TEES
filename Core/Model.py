"""
For storing the results of TEES training.
"""
import sys, os, shutil
import filecmp
import zipfile
import tempfile

NOTHING = object()

class Model():
    """ 
    The Model object is an interface to a model file on the disk. The model file
    itself is simply a directory or zip-archive storing all the files that result
    from TEES being trained. In addition, it can store named string values for 
    saved settings etc.
    
    When a member of a model is accessed, it is copied to a temporary cache directory.
    When a model is saved, files that have changed in the cache are copied to the model
    directory/archive. Note that for both files and strings that are added to the model,
    are saved to it only when Model.save is called.
    """    
    def __init__(self, path, mode="r", verbose=True, compression=zipfile.ZIP_DEFLATED):
        """
        Make a new model or open an existing one
        
        @param path: The model file or directory. If making a new model, a path ending in ".zip" results in a compressed archive.
        @param mode: r, w or a for read, write or append
        @param verbose: Model reports what is happening
        @param compression: The compression method if a the model is a zip-archive.
        """
        self.members = {} # path_inside_model:path_to_cache_file (path_to_cache_file == None for members not yet requested)
        self.valueFileName = "TEES_MODEL_VALUES.tsv"
        self.compression = compression
        self.workdir = None
        self.mode = None
        self.path = None
        self.open(path, mode)
        self.verbose = verbose
    
    def __del__(self):
        self.close()
    
    def close(self):
        if self.workdir != None:
            shutil.rmtree(self.workdir)
        self.workdir = None
        self.path = None
        self.members = None
    
    def add(self, name):
        self.members[name] = None
    
    def insert(self, filepath, name):
        """
        Adds a new file to the model.
        
        @param filepath: Path to the file being added
        @param name: Path of the file inside the model  
        """
        shutil.copy2(filepath, os.path.join(self.workdir, name))
        self.members[name] = os.path.join(self.workdir, name)
    
    def importFrom(self, model, members, strings=None, allowMissing=True):
        """
        Copy several members from another model
        """
        for member in members:
            if model.hasMember(member):
                self.insert(model.get(member), member)
            elif not allowMissing:
                raise IOError("Model to import from has no member \"" + name + "\"")
        if strings != None:
            for string in strings:
                stringValue = model.getStr(string, defaultIfNotExist=None)
                if stringValue != None:
                    self.addStr(string, stringValue)
                elif not allowMissing:
                    raise IOError("Model to import from has no string \"" + string + "\"")
    
    def addStrings(self, dict):
        """
        Add multiple name/value pairs
        """
        for key in sorted(dict.keys()):
            self.addStr(key, dict[key])
    
    def addStr(self, name, value):
        """
        Add a named string to the model
        
        @param : the name of the string
        @param : the string
        """
        for c in ["\n", "\t", "\r"]:
            assert c not in name, (c, name, value)
            assert c not in value, (c, name, value)
        values = self._getValues()
        if name != None:
            values[name] = value
        elif name in values: # remove the parameter
            del values[name]
        self._setValues(values)
    
    def getStr(self, name, defaultIfNotExist=NOTHING, asType=None):
        """
        Get a named string from the model
        
        @param name : the name of the string
        @param defaultIfNotExist: if set to a value != NOTHING, will be returned if a name does not exist. Otherwise an exception is raised.
        @param asType : if set, cast the return value to this type  
        """
        values = self._getValues()
        if name in values:
            if asType == None:
                return values[name]
            else:
                return asType(values[name])
        elif defaultIfNotExist != NOTHING:
            return defaultIfNotExist
        else:
            raise IOError("String named '" + name + "' not defined in model " + self.path)
        
    def save(self):
        """
        Save a model.
        
        When saving a model, files that have changed in the cache are written to the model.
        """
        if self.mode == "r":
            raise IOError("Model not open for writing")
        if self.isPackage:
            package = zipfile.ZipFile(self.path, "r", self.compression)
            packageNames = package.namelist()
        # Check which files have changed in the cache
        changed = []
        for name in sorted(self.members.keys()):
            cached = self.members[name]
            if cached != None and os.path.exists(cached): # cache file exists
                if self.isPackage:
                    cachedInfo = os.stat(cached)
                    packageFileInfo = None
                    if name in packageNames:
                        packageFileInfo = package.getinfo(name)
                    if packageFileInfo == None or cachedInfo.st_size != packageFileInfo.file_size:
                        changed.append(name)
                else:
                    modelFilename = os.path.join(self.path, name)
                    if not os.path.exists(modelFilename) or not filecmp.cmp(modelFilename, cached):
                        changed.append(name)
        # Copy changed files from the cache to the model
        if len(changed) > 0:
            if self.verbose: print >> sys.stderr, "Saving model \"" + self.path + "\" (cache:" + self.workdir + ", changed:" + ",".join(changed) + ")"
            if self.isPackage:
                tempdir = tempfile.mkdtemp() # place to unpack existing model
                package.extractall(tempdir) # unpack model
                package.close() # close model
                for name in changed: # add changed files from cache
                    shutil.copy2(self.members[name], os.path.join(tempdir, name)) # from cache to unpacked model
                package = zipfile.ZipFile(self.path, "w", self.compression) # recreate the model
                for name in os.listdir(tempdir): # add all files to model
                    package.write(os.path.join(tempdir, name), name) # add file from tempdir
                shutil.rmtree(tempdir) # remove temporary directory
            else:
                for name in changed:
                    shutil.copy2(self.members[name], os.path.join(self.path, name))
        if self.isPackage:
            package.close()     
    
    def saveAs(self, outPath):
        """
        Save a model with a different name.
        """
        print >> sys.stderr, "Saving model \"" + self.path, "as", outPath
        if os.path.exists(outPath):
            print >> sys.stderr, outPath, "exists, removing"
            if os.path.isdir(outPath):
                shutil.rmtree(outPath)
            else:
                os.remove(outPath)
        if self.isPackage:
            # copy current model to new location
            shutil.copy2(self.path, outPath)
            # add cached (potentially updated) files
            package = zipfile.ZipFile(outPath, "a")
            for f in os.listdir(self.workdir):
                package.write(f)
            package.close()
        else:
            # copy files from model
            shutil.copytree(self.path, outPath)
            # copy cached (potentially updated) files
            for f in os.listdir(self.workdir):
                shutil.copy2(os.path.join(self.workdir, f), outPath)
    
    def hasMember(self, name):
        return name in self.members
    
    def get(self, name, addIfNotExist=False, defaultIfNotExist=NOTHING):
        """
        Return a file member from the model. The member is extracted to a cached directory
        and returned as a path name. If this file is modified, when the model is saved,
        it will be copied back to the model.
        
        @param name : the path to the file inside the model
        @param addIfNotExist : Return a file name which can be created for adding the file
        """
        if name not in self.members:
            if addIfNotExist:
                self.add(name)
            elif defaultIfNotExist != NOTHING:
                return defaultIfNotExist
            else:
                raise IOError("Model has no member \"" + name + "\"")
        # Cache member if not yet cached
        if self.members[name] == None: # file has not been cached yet
            cacheFilename = os.path.join(self.workdir, name)
            if self.isPackage:
                package = zipfile.ZipFile(self.path, "r")
                try:
                    if self.verbose: print >> sys.stderr, "Caching model \"" + self.path + "\" member \"" + name + "\" to \"" + cacheFilename + "\""
                    package.extract(name, self.workdir)
                except: # member does not exist yet
                    pass
                package.close()
            elif os.path.exists(os.path.join(self.path, name)): # member already exists inside the model directory
                if self.verbose: print >> sys.stderr, "Caching model \"" + self.path + "\" member \"" + name + "\" to \"" + cacheFilename + "\""
                shutil.copy2(os.path.join(self.path, name), cacheFilename)
            self.members[name] = cacheFilename
        return self.members[name]
    
    def open(self, path, mode="r"):
        assert mode in ["r", "w", "a"]
        self.mode = mode
        self.path = path
        if self.path.endswith('.zip'):
            self._openPackage(path, mode)
        else:
            self._openDir(path, mode)
        self.workdir = tempfile.mkdtemp()
    
    def _openDir(self, path, mode):
        if mode == "w" and os.path.exists(path):
            shutil.rmtree(path)
        if not os.path.exists(path):
            os.mkdir(path)
            open(os.path.join(path, self.valueFileName), "wt").close()
        # get members
        members = os.listdir(path)
        for member in members:
            self.members[member] = None
        self.isPackage = False
    
    def _openPackage(self, path, mode):
        if mode == "w" and os.path.exists(path):
            os.remove(path)
        if not os.path.exists(path): # create empty archive
            package = zipfile.ZipFile(path, "w", self.compression)
            temp = tempfile.mkstemp()
            package.write(temp[1], self.valueFileName)
            package.close()
            os.remove(temp[1])
        # get members
        package = zipfile.ZipFile(path, "r")
        for name in package.namelist():
            self.members[name] = None
        package.close()
        self.isPackage = True
    
    # Value file
    def _getValues(self):
        values = {}
        settingsFileName = self.get(self.valueFileName, True)
        if os.path.exists(settingsFileName):            
            f = open(settingsFileName, "rt")
            for line in f:
                key, value = line.split("\t", 1)
                key = key.strip()
                value = value.strip()
                values[key] = value
            f.close()
        return values
    
    def _setValues(self, values):
        f = open(self.get(self.valueFileName, True), "wt")
        for key in sorted(values.keys()):
            f.write(key + "\t" + values[key] + "\n")
        f.close()