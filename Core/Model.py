import sys, os, shutil
import filecmp
import tarfile
import tempfile

class Model():
    def __init__(self, path, mode="r", verbose=True):
        self.members = {} # path_inside_model:[abspath_to_file_in_model, abspath_to_cache_file]
        self.workdir = None
        self.mode = None
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
        #f = open(self.get(name), "rt")
        #value = f.readline().strip()
        #f.close()
        #return value
        return self._getValues()[name]
    
    def save(self):
        if self.mode == "r":
            raise IOError("Model not open for writing")
        if self.isPackage:
            tf = tarfile.open(self.path, "r:gz")
            tarinfos = {}
            for tarinfo in tf.getmembers():
                tarinfos[tarinfo.name] = tarinfo
            tf.close()
        changed = []
        for name in sorted(self.members.keys()):
            member = self.members[name]
            if member[1] != None and os.path.exists(member[1]): # cache file exists
                if self.isPackage:
                    fi = os.stat(member[1])
                    ti = None
                    if name in tarinfos:
                        ti = tarinfos[name]
                    if ti == None or fi.st_size != ti.size or fi.st_mtime != ti.mtime:
                        changed.append(name)
                elif not os.path.exists(member[0]) or not filecmp.cmp(member[1], member[0]):
                    changed.append(name)
        if len(changed) > 0:
            if self.verbose: print >> sys.stderr, "Saving model \"" + self.path + "\" (cache:" + self.workdir + ", changed:" + ",".join(changed) + ")"
            if self.isPackage:
                tf = tarfile.open(self.path, "w:gz")
                tf.add(member[1], member[0])
                tf.close()
            else:
                for name in changed:
                    member = self.members[name]
                    shutil.copy2(member[1], member[0])     
    
    def saveAs(self, outPath):
        print >> sys.stderr, "Saving model \"" + self.path, "as", outPath
        if os.path.exists(outPath):
            print >> sys.stderr, outPath, "exists, removing"
            if os.path.isdir(outPath):
                shutil.rmtree(outPath)
            else:
                os.remove(outPath)
        if isPackage:
            # copy everything to tempdir
            tempdir = tempfile.mkdtemp()
            # copy files from model
            modelTar = tarfile.open(self.path, "r:gz")
            modelTar.extractAll(tempdir)
            modelTar.close()
            # copy cached files
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
            # copy cached files
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
        member = self.members[name]
        if member[1] == None: # file has not been cached yet
            cacheFile = os.path.join(self.workdir, name)
            if self.isPackage:
                if member[2] != None:
                    tf = tarfile.open(self.path, "r:gz")
                    tf.extract(name, self.workdir)
                    tf.close()
            else:
                if os.path.exists(member[0]): # member already exists inside the model
                    if self.verbose: print >> sys.stderr, "Caching model \"" + self.path + "\" member \"" + member[0] + "\" to \"" + cacheFile + "\""
                    shutil.copy2(member[0], cacheFile)
            member[1] = cacheFile
        return member[1]
    
    def open(self, path, mode="r"):
        assert mode in ["r", "w", "a"]
        self.mode = mode
        self.path = path
        if self.path.endswith('.tar.gz') or self.path.endswith('.tgz'):
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
            self.members[member] = [os.path.join(path, member), None]
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
            self.members[tarinfo.name] = [None, None]
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