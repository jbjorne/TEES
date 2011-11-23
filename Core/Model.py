import sys, os, shutil
import filecmp
import tempfile

class Model():
    def __init__(self, path, mode="r"):
        self.members = {} # path_inside_model:[abspath_to_model, cache_file, tar_info]
        self.workdir = None
        self.mode = None
        self.open(path, mode)
    
    def close(self):
        shutil.rmtree(self.workdir)
        self.path = None
        self.members = None
        self.workdir = None
    
    def add(self, name):
        self.members[name] = [os.path.join(self.path, name), None, None]
    
    def insert(self, path, name):
        shutil.copy2(path, os.path.join(self.workdir, name))
        self.members[name] = [os.path.join(self.path, name), os.path.join(self.workdir, name), None]
    
    def save(self):
        if self.mode == "r":
            return
        for name in sorted(self.members.keys()):
            member = self.members[name]
            if member[1] != None and (not os.path.exists(member[0]) or not filecmp.cmp(member[1], member[0])):
                print "Updating model member", member[0]
                shutil.copy2(member[1], member[0])
    
    def get(self, name, addIfNotExist=True):
        if name not in self.members and addIfNotExist:
            self.add(name)
        member = self.members[name]
        if member[1] == None:
            cacheFile = os.path.join(self.workdir, name)
            if os.path.exists(member[0]):
                print "Caching model member", member[0], "to", cacheFile
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