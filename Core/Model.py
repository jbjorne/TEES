import sys, os, shutil
import filecmp
import tarfile
import tempfile

class Model():
    def __init__(self, path, mode="r", verbose=True):
        self.members = {} # path_inside_model:[abspath_to_file_in_model, abspath_to_cache_file]
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
        self.members[name] = [os.path.join(self.path, name), None]
    
    def insert(self, filepath, name):
        shutil.copy2(filepath, os.path.join(self.workdir, name))
        self.members[name] = [os.path.join(self.path, name), os.path.join(self.workdir, name), None]
    
    def importFrom(self, model, members, strings=None):
        for member in members:
            self.insert(model.get(member), member)
        if strings != None:
            for string in strings:
                self.addStr(string, model.getStr(string))
    
    def addStrings(self, dict):
        for key in sorted(dict.keys()):
            self.addStr(key, dict[key])
    
    def addStr(self, name, value):
        for c in ["\n", "\t", "\r"]:
            assert c not in name, (c, name, value)
            assert c not in value, (c, name, value)
        values = self._getValues()
        if name != None:
            values[name] = value
        elif name in values: # remove the parameter
            del values[name]
        self._setValues(values)
        #f = open(self.get(name, True), "wt")
        #f.write(value)
        #f.close()
    
    def getStr(self, name):
        return self._getValues()[name]
    
    def save(self):
        if self.mode == "r":
            raise IOError("Model not open for writing")
        if self.isPackage():
            tf = tarfile.open(self.path, "r:gz")
            tarinfos = {}
            for tarinfo in tf.getmembers():
                tarinfos[tarinfo.name] = tarinfo
            tf.close()
        # Check which files have changed in the cache
        changed = []
        for name in sorted(self.members.keys()):
            cached = self.members[name]
            if cached != None and os.path.exists(cached): # cache file exists
                if self.isPackage():
                    fi = os.stat(cached)
                    ti = None
                    if name in tarinfos:
                        ti = tarinfos[name]
                    if ti == None or fi.st_size != ti.size or fi.st_mtime != ti.mtime:
                        changed.append(name)
                else:
                    modelFilename = os.path.join(self.path, name)
                    if not os.path.exists(modelFilename) or not filecmp.cmp(modelFilename, cached):
                        changed.append(name)
        # Copy changed files from the cache to the model
        if len(changed) > 0:
            if self.verbose: print >> sys.stderr, "Saving model \"" + self.path + "\" (cache:" + self.workdir + ", changed:" + ",".join(changed) + ")"
            if self.isPackage():
                for name in changed:
                    tf = tarfile.open(self.path, "w:gz")
                    tf.add(self.members[name])
                    tf.close()
            else:
                for name in changed:
                    shutil.copy2(self.members[name], os.path.join(self.path, name))     
    
    def saveAs(self, outPath):
        print >> sys.stderr, "Saving model \"" + self.path, "as", outPath
        if os.path.exists(outPath):
            print >> sys.stderr, outPath, "exists, removing"
            if os.path.isdir(outPath):
                shutil.rmtree(outPath)
            else:
                os.remove(outPath)
        if self.isPackage():
            # copy everything to tempdir
            tempdir = tempfile.mkdtemp()
            # copy all files from model to tempdir
            modelTar = tarfile.open(self.path, "r:gz")
            modelTar.extractAll(tempdir)
            modelTar.close()
            # copy cached (potentially updated) files to tempdir
            for f in os.listdir(self.workdir):
                shutil.copy2(f, tempdir)
            # add everything to the new model
            newTar = tarfile.open(outPath, "w:gz")
            for filename in os.listdir(tempdir):
                newTar.add(tempdir + "/" + filename, filename)
            newTar.close()
            # cleanup
            shutil.rmtree(tempdir)
        else:
            # copy files from model
            shutil.copytree(self.path, outPath)
            # copy cached (potentially updated) files
            for f in os.listdir(self.workdir):
                shutil.copy2(f, outPath)
    
    def hasMember(self, name):
        return name in self.members
    
    def get(self, name, addIfNotExist=False):
        if name not in self.members:
            if addIfNotExist:
                self.add(name)
            else:
                raise IOError("Model has no member \"" + name + "\"")
        # Cache member if not yet cached
        if self.members[name] == None: # file has not been cached yet
            cacheFile = os.path.join(self.workdir, name)
            if self.isPackage:
                tf = tarfile.open(self.path, "r:gz")
                try:
                    if self.verbose: print >> sys.stderr, "Caching model \"" + self.path + "\" member \"" + name + "\" to \"" + cacheFile + "\""
                    tf.extract(name, self.workdir)
                except: # member does not exist yet
                    pass
                tf.close()
            elif os.path.exists(os.path.join(self.path, name)): # member already exists inside the model
                if self.verbose: print >> sys.stderr, "Caching model \"" + self.path + "\" member \"" + name + "\" to \"" + cacheFile + "\""
                shutil.copy2(os.path.join(self.path, name), cacheFile)
            self.members[name] = cacheFile
        return self.members[name]
    
    def isPackage(self):
        if self.path.endswith('.tar.gz') or self.path.endswith('.tgz'):
            return True
        else:
            return False
    
    def open(self, path, mode="r"):
        assert mode in ["r", "w", "a"]
        self.mode = mode
        self.path = path
        if self.isPackage():
            self._openPackage(path, mode)
        else:
            self._openDir(path, mode)
        self.workdir = tempfile.mkdtemp()
        self._openDir(path)
    
    def _openDir(self, path, mode):
        if mode == "w" and os.path.exists(path):
            shutil.rmtree(path)
        if not os.path.exists(path):
            os.mkdir(path)
        # get members
        members = os.listdir(path)
        for member in members:
            self.members[member] = None
        self.isPackage = False
    
    def _openPackage(self, path, mode):
        if mode == "w" and os.path.exists(path):
            os.remove(path)
        if not os.path.exists(path):
            tarfile.open(path, 'w:gz').close()
        # get members
        package = tarfile.open(path, 'r:gz')
        tarinfos = tarfile.getmembers()
        for tarinfo in tarinfos:
            self.members[tarinfo.name] = None
        self.isPackage = True
    
    # Value file
    def _getValues(self):
        values = {}
        settingsFileName = self.get("settings.tsv", True)
        if os.path.exists(settingsFileName):            
            f = open(settingsFileName, "rt")
            for line in f:
                key, value = line.strip().split("\t", 1)
                values[key] = value
            f.close()
        return values
    
    def _setValues(self, values):
        f = open(self.get("settings.tsv", True), "wt")
        for key in sorted(values.keys()):
            f.write(key + "\t" + values[key] + "\n")
        f.close()