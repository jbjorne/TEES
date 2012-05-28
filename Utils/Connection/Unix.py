import sys, os, shutil, types
import subprocess
sys.path.append(os.path.abspath(os.path.dirname(__file__))+"/..")
from Utils.Timer import Timer
import Utils.Settings as Settings
import tempfile

class UnixConnection:    
    def __init__(self, workDirBase=None, account=None, memory=4194304, cores=1):
        self.account = account    
        self.memory = memory
        self.cores = cores
        #self.machineName = account.split("@")[-1]
        self._workDirBase = workDirBase
        self.setWorkDir("", False)
        # State constants
        self.NOT_EXIST = "NOT_EXIST"
        self.NONZERO = "NONZERO"
        self.ZERO = "ZERO"
        
        # Batch job queue
        self.commands = []
        
        self.compression = False #True
        self.remoteSettingsPath = None
        self.cachedRemoteSettings = None
        self._logs = {}
    
    def isLocal(self):
        return self.account == None
    
    def getPath(self, path, addAccount=False):
        if self.workDir != None: # a working directory has been set
            path = os.path.normpath(self.workDir + "/" + path)
        if addAccount and self.account != None: # this connection refers to a remote machine
            path = self.account + ":" + path
        return path 
        
    def getSetting(self, name):
        if self.account == None:
            return getattr(Settings, name)
        elif self.cachedRemoteSettings == None:
            self.cachedRemoteSettings = {}
            # Determine location of remote TEES_SETTINGS
            if self.remoteSettingsPath == None: # not yet known, so look for environment variable
                rsp = self.run("echo $TEES_SETTINGS")
            else: # download from defined location
                rsp = self.remoteSettingsPath
            # Download settings to local computer
            print >> sys.stderr, "Reading remote TEES_SETTINGS from", self.account + ":" + rsp
            tempdir = tempfile.mkdtemp()
            self.scp(self.account + ":" + rsp, tempdir + "/RemoteSettings.py")
            # Read remote settings as a text file (limited to simple variables)
            # I guess it could also be evaluated as Python, but it may contain code
            # dependent on the remote environment.
            f = open(tempdir + "/RemoteSettings.py", "rt")
            for line in f.readlines():
                if "=" in line:
                    name, value = line.split("=", 1)
                    name = name.strip()
                    value = value.strip()
                    self.cachedRemoteSettings[name] = value
            f.close()
            shutil.rmtree(tempdir)
        # Return the remote value
        return self.cachedRemoteSettings[name]
    
    def setWorkDir(self, workDir, delete=False):
        if self._workDirBase == None:
            self.workDir = None
            return
        self.workDir = os.path.normpath(self._workDirBase + "/" + workSubDir)
        if delete:
            if self.workDir == self._workDirBase:
                print >> sys.stderr, "No workdir defined"
            else:
                print "Removing", self.__name__, "work directory", self.workDir, "(if it exists)"
                self.run("rm -fr " + self.workDir)
        self.run("mkdir -p " + self.workDir)
    
    def exists(self, filename):
        stdout = self.run("ls -lh " + self.workDir + "/" + filename)
        if len(stdout) > 0:
            return True
        else:
            return False
    
    def mkdir(self, dir):
        stdout = self.run("mkdir -p " + self.workDir + "/" + dir)
        if len(stdout) > 0:
            return True
        else:
            return False
    
    def getFileStatus(self, filename):
        filePath = self.workDir + "/" + filename
        if self.account == None:
            if not os.path.exists(filePath):
                return self.NOT_EXIST
            elif os.path.getsize(filePath) == 0:
                return self.ZERO
            else:
                return self.NONZERO
        else:
            lines = self.run("filetest -e " + filePath + "; filetest -z " + filePath)
            #assert len(lines) == 2
            if int(lines[0]) == 0:
                return self.NOT_EXIST
            if int(lines[1]) == 1:
                return self.ZERO
            else:
                return self.NONZERO
        
    def upload(self, src, dst=None, replace=True, compress=False, uncompress=False):
        if self.account == None:
            return src
        
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and ( self.exists(dst) or (uncompress and dst.endswith(".gz") and self.exists(dst[:-3])) ):
            return False
        else:
            if (self.compression or compress) and not src.endswith(".gz"):
                print >> sys.stderr, "Compressing " + src + ": ",
                subprocess.call("gzip -fv < " + src + " > " + src + ".gz", shell=True)
                src += ".gz"
                dst += ".gz"
            print "scp " + src + " " + self.account + ":" + self.workDir + "/" + dst
            self.scp(src, self.account + ":" + self.workDir + "/" + dst)
            #subprocess.call("scp " + src + " " + self.account + ":" + self.workDir + "/" + dst, shell=True)
            if self.compression or uncompress:
                self.run("gunzip -fv " + self.workDir + "/" + dst)
            return True
        
    def scp(self, par1, par2):
        account1 = None
        if ":" in par1:
            account1 = par1.split(":")[0]
        account2 = None
        if ":" in par2:
            account2 = par2.split(":")[0]
        if (account1 == None or account1 == self.account) and (account2 == None or account2 == self.account):
            # local copy
            subprocess.call("cp -f " + par1.split(":")[-1] + " " + par2.split(":")[-1], shell=True)
        else:
            # remote copy
            subprocess.call("scp " + par1 + " " + par2, shell=True)
        
    def download(self, src, dst=None, replace=True, compress=False, uncompress=False):
        """
        Copy a file from the remote location to the local computer
        """
        if self.account == None:
            return src
        
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and os.path.exists(dst):
            return False
        else:
            if (self.compression or compress) and not src.endswith(".gz"):
                print >> sys.stderr, "Compressing " + src + ": ",
                self.run("gzip < " + self.workDir + "/" + src + " > " + self.workDir + "/" + src + ".gz")
                src = src + ".gz"
                dst = dst + ".gz"
            self.scp(self.account + ":" + self.workDir + "/" + src, dst)
            if self.compression or uncompress:
                subprocess.call("gunzip -f " + dst, shell=True)
            return True
    
    def run(self, script, cdWrkDir=False):
        """
        Immediately run a command.
        """
        if cdWrkDir:
            script = "cd " + self.workDir + " ; " + script
        if self.account == None: # a local process
            p = subprocess.Popen(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen("ssh " + self.account + " '" + script + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.stdout.readlines()
    
    def addCommand(self, string):
        self.commands.append(string)
    
    def submit(self, script=None, stdout=None, stderr=None):
        """
        Queue a command.
        """
        if script == None:
            script = " ; ".join(self.commands)
            self.commands = []
        logFiles = [None, None]
        if type(stdout) in types.StringTypes:
            print >> sys.stderr, "Job stdout at", stdout
            logFiles[0] = stdout = open(stdout, "wt")
        if type(stderr) in types.StringTypes:
            print >> sys.stderr, "Job stderr at", stderr
            logFiles[1] = stderr = open(stderr, "wt")
        print >> sys.stderr, "Submitting script:", script
        if self.account == None: # a local process
            job = subprocess.Popen(script, shell=True, stdout=stdout, stderr=stderr)
        else:
            job = subprocess.Popen("ssh " + self.account + " '" + script + "'", shell=True, stdout=stdout, stderr=stderr)
        if logFiles != [None, None]:
            assert job not in self._logs
            self._logs[job] = logFiles
        print >> sys.stderr, "Submitted job", job.pid
        return job
    
    def _closeLogs(self, job):
        if job in self._logs:
            if self._logs[job][0] != None:
                self._logs[job][0].close()
            if self._logs[job][1] != None:
                self._logs[job][1].close()
            del self._logs[job]
    
    def getJobStatus(self, job):
        returncode = job.poll()
        if returncode == None:
            return "RUNNING"
        elif returncode == 0:
            self._closeLogs(job)
            return "FINISHED"
        else:
            self._closeLogs(job)
            return "FAILED"

if __name__=="__main__":
    c = CSCConnection("remoteTest", "jakrbj@louhi.csc.fi", True)
    f = "/usr/share/biotext/Autumn2010/TriggerEdgeTest/TriggerEdge2TestDeterminismTest101103/uploadtest"
    c.upload(f)
    c.download(os.path.basename(f), "delme")
    #c.test()
    #c.exists("merg-info.py")
    #classifier.trainAndTestOnLouhi("trigger-train-examples", "trigger-test-examples", {"c":1000}, c)
    #print c.exists("trigger-test-examples")