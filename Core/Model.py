import sys, os, shutil
import filecmp
import tempfile

class Model():
    def __init__(self, path, mode="r", verbose=True):
        self.members = {} # path_inside_model:[abspath_to_model, cache_file, tar_info]
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
        self.members[name] = [os.path.join(self.path, name), None, None]
    
    def insert(self, path, name):
        shutil.copy2(path, os.path.join(self.workdir, name))
        self.members[name] = [os.path.join(self.path, name), os.path.join(self.workdir, name), None]
    
    def importFrom(self, model, members):
        for member in members:
            self.insert(model.get(member), member)
    
    def addStr(self, name, value):
        f = open(self.get(name, True), "wt")
        f.write(value)
        f.close()
    
    def getStr(self, name):
        f = open(self.get(name), "rt")
        value = f.readline().strip()
        f.close()
        return value
    
    def save(self):
        if self.mode == "r":
            raise IOError("Model not open for writing")
        changed = []
        for name in sorted(self.members.keys()):
            member = self.members[name]
            if member[1] != None and os.path.exists(member[1]) and (not os.path.exists(member[0]) or not filecmp.cmp(member[1], member[0])):
                changed.append(name)
        if len(changed) > 0:
            if self.verbose: print >> sys.stderr, "Saving model \"" + self.path + "\" (cache:" + self.workdir + ", changed:" + ",".join(changed) + ")"
            for name in changed:
                member = self.members[name]
                shutil.copy2(member[1], member[0])
    
    def saveAs(self, outPath):
        print >> sys.stderr, "Saving model \"" + self.path, "as", outPath
        if os.path.exists(outPath):
            print >> sys.stderr, outPath, "exists, removing"
            shutil.rmtree(outPath)
        shutil.copytree(self.workdir, outPath)
    
    def hasMember(self, name):
        return name in self.members
    
    def get(self, name, addIfNotExist=False):
        if name not in self.members:
            if addIfNotExist:
                self.add(name)
            else:
                raise IOError("Model has no member \"" + name + "\"")
        member = self.members[name]
        if member[1] == None:
            cacheFile = os.path.join(self.workdir, name)
            if os.path.exists(member[0]):
                if self.verbose: print >> sys.stderr, "Caching model \"" + self.path + "\" member \"" + member[0] + "\" to \"" + cacheFile + "\""
                shutil.copy2(member[0], cacheFile)
            member[1] = cacheFile
        return member[1]
    
    def open(self, path, mode="r"):
        assert mode in ["r", "w", "a"]
        self.mode = mode
        self.path = path
        if mode == "w" and os.path.exists(path):
            shutil.rmtree(path)
        if not os.path.exists(path):
            os.mkdir(path)
        self.workdir = tempfile.mkdtemp()
        self._openDir(path)
    
    def _openDir(self, path):
        members = os.listdir(path)
        for member in members:
            self.members[member] = [os.path.join(path, member), None, None]