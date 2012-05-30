import sys, os, shutil, types
import subprocess
import getpass
sys.path.append(os.path.abspath(os.path.dirname(__file__))+"/..")
from Utils.Timer import Timer
import Utils.Settings as Settings
import tempfile

class UnixConnection:    
    def __init__(self, account=None, workDirBase=None, remoteSettingsPath=None, memory=4194304, cores=1):
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
        
        # Batch command queue
        self.commands = []
        
        self.compression = False #True
        self.remoteSettingsPath = remoteSettingsPath
        self.cachedRemoteSettings = None
        self._logs = {}
        self.debug = True
    
    def getUsername(self):
        if self.account == None: # local machine
            return getpass.getuser()
        else:
            return self.account.split("@")[0]
    
    def getPath(self, path, addAccount=False):
        if self.workDir != None: # a working directory has been set
            path = os.path.normpath(self.workDir + "/" + path)
        if addAccount and self.account != None: # this connection refers to a remote machine
            path = self.account + ":" + path
        return path 
        
    def getSetting(self, name):
        if self.account == None:
            if hasattr(Settings, name):
                return getattr(Settings, name)
            else:
                return None
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
                    remoteName, remoteValue = line.split("=", 1)
                    remoteName = remoteName.strip()
                    remoteValue = remoteValue.strip().strip("\"")
                    self.cachedRemoteSettings[remoteName] = remoteValue
            f.close()
            shutil.rmtree(tempdir)
        # Return the remote value
        if name in self.cachedRemoteSettings:
            return self.cachedRemoteSettings[name]
        else:
            return None
    
    def setWorkDir(self, workDir, delete=False):
        if self._workDirBase == None:
            self.workDir = None
            return
        self.workDir = os.path.normpath(self._workDirBase + "/" + workDir)
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
            return dst
        else:
            if (self.compression or compress) and not src.endswith(".gz"):
                print >> sys.stderr, "Compressing " + src + ": ",
                subprocess.call("gzip -fv < " + src + " > " + src + ".gz", shell=True)
                src += ".gz"
                dst += ".gz"
            dst = os.path.normpath(self.workDir + "/" + dst)
            self.scp(src, self.account + ":" + dst, verbose="upload")
            if self.compression or uncompress:
                assert dst.endswith(".gz")
                self.run("gunzip -fv " + dst)
                dst = dst.rsplit(".", 1)[0]
            return dst
        
    def scp(self, par1, par2, verbose="transfer"):
        account1 = None
        if ":" in par1:
            account1 = par1.split(":")[0]
        account2 = None
        if ":" in par2:
            account2 = par2.split(":")[0]
        if account1 == None and account2 == None:
            # local copy
            dirPath = os.path.normpath(os.path.dirname(par2.split(":")[-1]))
            if not os.path.exists(dirPath):
                os.makedirs()
            if verbose != None:
                print >> sys.stderr, verbose + "(local copy):", par1.split(":")[-1], par2.split(":")[-1]
            shutil.copy2(par1.split(":")[-1], par2.split(":")[-1])
        else:
            # remote copy
            self.run("mkdir -p " + os.path.dirname(par2.split(":")[-1]))
            print "scp " + par1 + " " + par2
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
            return dst
        else:
            if (self.compression or compress) and not src.endswith(".gz"):
                print >> sys.stderr, "Compressing " + src + ": ",
                self.run("gzip < " + self.workDir + "/" + src + " > " + self.workDir + "/" + src + ".gz")
                src = src + ".gz"
                dst = dst + ".gz"
            self.scp(src, dst, verbose="download")
            if self.compression or uncompress:
                assert dst.endswith(".gz")
                subprocess.call("gunzip -f " + dst, shell=True)
                dst = dst.rsplit(".", 1)[0]
            return dst
    
    def run(self, script, cdWrkDir=False):
        """
        Immediately run a command.
        """
        if cdWrkDir:
            script = "cd " + self.workDir + " ; " + script
        if self.account == None: # a local process
            p = subprocess.Popen(script, shell=True, stdout=subprocess.PIPE)
        else:
            p = subprocess.Popen("ssh " + self.account + " '" + script + "'", shell=True, stdout=subprocess.PIPE)
        return p.stdout.readlines()
    
    def getScript(self, script=None, joinString=" ; "):
        if script == None: # use command buffer
            script = joinString.join(self.commands)
            self.commands = []
        return script
    
    def addCommand(self, string):
        self.commands.append(string)
    
    def submit(self, script=None, jobWorkDir=None, name=None, stdout=None, stderr=None):
        """
        Queue a command.
        """
        script = self.getScript(script)
        logFiles = [None, None]
        if type(stdout) in types.StringTypes:
            print >> sys.stderr, "Job stdout at", stdout
            logFiles[0] = stdout = open(stdout, "wt")
        if type(stderr) in types.StringTypes:
            print >> sys.stderr, "Job stderr at", stderr
            logFiles[1] = stderr = open(stderr, "wt")
        if self.debug:
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

from LSF import LSFConnection
from SLURM import SLURMConnection
#import LSF.LSFConnection

def getConnection(connection, account=None, workDirBase=None, remoteSettingsPath=None):
    if connection == None: # return a "dummy" local connection
        return getConnection("Unix")
    elif type(connection) in types.StringTypes and hasattr(Settings, connection): # connection is a Settings key
        print >> sys.stderr, "Using connection", connection
        return getConnection(*getattr(Settings, connection))
    else: # connection is the connection object type
        if account == None:
            assert workDirBase == None
            assert remoteSettingsPath == None
            print >> sys.stderr, "New local", connection, "connection"
        else: 
            print >> sys.stderr, "New remote", connection, "connection:", account, workDirBase, remoteSettingsPath
        if connection == "Unix":
            return UnixConnection(account, workDirBase, remoteSettingsPath)
        elif connection == "LSF":
            return LSFConnection(account, workDirBase, remoteSettingsPath)
        elif connection == "SLURM":
            return SLURMConnection(account, workDirBase, remoteSettingsPath)
        else:
            assert False, connection

if __name__=="__main__":
    c = CSCConnection("remoteTest", "jakrbj@louhi.csc.fi", True)
    f = "/usr/share/biotext/Autumn2010/TriggerEdgeTest/TriggerEdge2TestDeterminismTest101103/uploadtest"
    c.upload(f)
    c.download(os.path.basename(f), "delme")
    #c.test()
    #c.exists("merg-info.py")
    #classifier.trainAndTestOnLouhi("trigger-train-examples", "trigger-test-examples", {"c":1000}, c)
    #print c.exists("trigger-test-examples")