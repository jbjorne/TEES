import sys, os, shutil, types
import subprocess
import getpass
import time
import atexit, signal
sys.path.append(os.path.normpath(os.path.abspath(os.path.dirname(__file__))+"/../.."))
from Utils.Timer import Timer
import Utils.Settings as Settings
import Utils.Parameters as Parameters
import tempfile

class UnixConnection:
    #programGroupSet = False
    
    def __init__(self, account=None, workdir=None, settings=None, memory=None, cores=None, jobLimit=None, killGroup=True, preamble=None, debug=False):
        self.account = account
        if memory == None:
            memory = 4194304
        self.memory = int(memory)
        if cores == None:
            cores = 1
        self.cores = int(cores)
        #self.machineName = account.split("@")[-1]
        self.workDir = workdir
        self.preamble = preamble
        #self._workDirBase = workDirBase
        #self.setWorkDir("", False)
        # State constants
        self.NOT_EXIST = "NOT_EXIST"
        self.NONZERO = "NONZERO"
        self.ZERO = "ZERO"
        
        # Batch command queue
        self.commands = []
        
        self.compression = False #True
        self.remoteSettingsPath = settings
        self.cachedRemoteSettings = None
        self._logs = {}
        if jobLimit == None:
            jobLimit = -1
        self.jobLimit = int(jobLimit)
        self.debug = debug
        self.resubmitOnlyFinished = True
        
        # Make sure local processes are killed on exit
        if self.account == None and killGroup: # and not UnixConnection.programGroupSet:
            #UnixConnection.programGroupSet = True
            os.setpgrp() # All child processes from subprocess should be in this group
#            atexit.register(os.killpg, 0, signal.SIGKILL)
#            #if jobLimit == None: # limit parallel processes on a local account
#            #    self.jobLimit = 1
    
    def clearWorkDir(self, subDir=""):
        if self.account == None:
            print >> sys.stderr, "Local connection, remote directory not removed"
            return
        workSubDir = self.getRemotePath(subDir)
        assert workSubDir != self.workDir, (self.workDir, subDir) # prevent removal of the whole remote work directory
        print >> sys.stderr, "Removing remote directory", workSubDir
        self.run("rm -R " + workSubDir)
    
    def isLocal(self):
        return self.account == None
    
    def getRemotePath(self, path, addAccount=False):
        if self.workDir != None: # a working directory has been set
            path = os.path.normpath(self.workDir + "/" + os.path.abspath(path.split(":")[-1]))
        if addAccount and self.account != None: # this connection refers to a remote machine
            path = self.account + ":" + path
        return path
    
    def getLocalPath(self, path):
        localPath = os.path.abspath(path.split(":")[-1])
        if self.workDir != None and localPath.startswith(self.workDir): # remote work directory path
            localPath = os.path.normpath("/" + localPath[len(self.workDir):])
            #assert not localPath.startswith(self.workDir), (path, localPath) # check for duplicates
        return localPath
        
    def getSetting(self, name, mustExist=True):
        if self.account == None:
            if mustExist and not (hasattr(Settings, name) and getattr(Settings, name) != None):
                raise Exception("Undefined local setting " + str(name))
                #assert hasattr(Settings, name), name
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
                assert self.remoteSettingsPath != None
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
        if mustExist:
            assert name in self.cachedRemoteSettings, (name, self.cachedRemoteSettings)
        if name in self.cachedRemoteSettings:
            return self.cachedRemoteSettings[name]
        else:
            return None
    
#    def setWorkDir(self, workDir, delete=False):
#        if self._workDirBase == None:
#            self.workDir = None
#            return
#        self.workDir = os.path.normpath(self._workDirBase + "/" + workDir)
#        if delete:
#            if self.workDir == self._workDirBase:
#                print >> sys.stderr, "No workdir defined"
#            else:
#                print "Removing", self.__name__, "work directory", self.workDir, "(if it exists)"
#                self.run("rm -fr " + self.workDir)
#        self.run("mkdir -p " + self.workDir)
    
    def exists(self, filename):
        stdout = self.run("ls -lh " + filename, silent=True)
        if len(stdout) > 0:
            return True
        else:
            return False
    
    def mkdir(self, dir):
        stdout = self.run("mkdir -p " + dir)
        if len(stdout) > 0:
            return True
        else:
            return False
    
    def getFileStatus(self, filename):
        filePath = self.getRemotePath(filename)
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

    def scp(self, par1, par2, verbose="transfer"):
        """
        General scp command, par1 and par2 must be full paths, including machine name
        """
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
                os.makedirs(dirPath)
            if verbose != None:
                print >> sys.stderr, verbose + "(local copy):", par1.split(":")[-1], par2.split(":")[-1]
            shutil.copy2(par1.split(":")[-1], par2.split(":")[-1])
        else:
            # remote copy
            print >> sys.stderr, verbose + ": scp " + par1 + " " + par2
            if ":" in par2:
                self.mkdir(os.path.dirname(par2.split(":")[-1]))
            elif not os.path.exists(os.path.dirname(par2)):
                os.makedirs(os.path.dirname(par2))
            subprocess.call("scp " + par1 + " " + par2, shell=True)
    
    def upload(self, src, dst=None, replace=True, compress=False, uncompress=False):
        """
        Mirror a file from "SRC" to "ACCOUNT:WORKDIR/DST"
        """
        assert ":" not in src # must be a local file
        if self.account == None: # local connection...
            return src # ...no upload required
        if dst == None: # default upload location
            dst = src
        dst = self.getRemotePath(dst)
        
        if replace == False and ( self.exists(dst) or (uncompress and dst.endswith(".gz") and self.exists(dst[:-3])) ):
            if uncompress and dst.endswith(".gz"): # has been uncompressed already
                dst = dst.rsplit(".", 1)[0]
            print >> sys.stderr, "Existing remote file", dst, "not overwritten"
            return dst
        else:
            if (self.compression or compress) and not src.endswith(".gz"):
                print >> sys.stderr, "Compressing " + src + ": ",
                subprocess.call("gzip -fv < " + src + " > " + src + ".gz", shell=True)
                src += ".gz"
                dst += ".gz"
            self.mkdir(os.path.dirname(dst))
            self.scp(src, self.account + ":" + dst, verbose="upload")
            if (self.compression or uncompress) and dst.endswith(".gz"):
                self.run("gunzip -fv " + dst)
                dst = dst.rsplit(".", 1)[0]
            return dst
        
    def download(self, src, dst=None, replace=True, compress=False, uncompress=False):
        """
        Mirror a file from "ACCOUNT:WORKDIR/SRC" to "DST"
        """
        # Determine src path
        if ":" in src: # src is a full pathname, with a machine name
            srcAccount, src = src.split(":")
            assert self.account == srcAccount # check that the accoutn corresponds to this connection
        else: # src is a remote path relative to remote workdir
            src = self.getRemotePath(src)
        # Determine dst path
        if dst == None: # default download location
            dst = src
            dst = self.getLocalPath(dst)
        assert ":" not in dst # must be a local file
        if self.account == None: # local connection ... 
            return dst # ... no download required
        
        if replace == False and os.path.exists(dst):
            return dst # already downloaded
        else: # download
            if (self.compression or compress) and not src.endswith(".gz"):
                print >> sys.stderr, "Compressing " + src + ": ",
                self.run("gzip < " + self.workDir + "/" + src + " > " + self.workDir + "/" + src + ".gz")
                src = src + ".gz"
                dst = dst + ".gz"
            self.scp(self.account + ":" + src, dst, verbose="download")
            if (self.compression or uncompress) and dst.endswith(".gz"):
                subprocess.call("gunzip -f " + dst, shell=True)
                dst = dst.rsplit(".", 1)[0]
            return dst
    
    def run(self, script, chdirTo=None, silent=False):
        """
        Immediately run a command.
        """
        if chdirTo != None:
            script = "cd " + chdirTo + " ; " + script
        stderr = None
        if silent:
            stderr = subprocess.PIPE
        if self.account == None: # a local process
            p = subprocess.Popen(script, shell=True, stdout=subprocess.PIPE, stderr=stderr)
        else:
            p = subprocess.Popen("ssh " + self.account + " '" + script + "'", shell=True, stdout=subprocess.PIPE, stderr=stderr)
        if silent:
            p.stderr.readlines()
        return p.stdout.readlines()
    
    def _getScript(self, script=None, joinString=" ; "):
        if script == None: # use command buffer
            script = joinString.join(self.commands)
            self.commands = []
        return script
    
    def addCommand(self, string):
        self.commands.append(string)
    
    def clearCommands(self):
        self.commands = []
        
    def getJob(self, jobDir, jobName):
        return self._getJobPath(jobDir, jobName)
    
    def _getJobPath(self, jobDir, jobName):
        return jobDir + "/" + jobName + ".job"
    
    def _writeJobFile(self, jobDir, jobName, attrDict={}, append=False):
        jobPath = self.getRemotePath(self._getJobPath(jobDir, jobName))
        jobFileText = ""
        if not append:
            jobFileText += "name=" + jobName + "\n"
            assert not "name" in attrDict
        for key in sorted(attrDict.keys()):
            jobFileText += str(key) + "=" + str(attrDict[key]) + "\n"
        if not os.path.exists(self.getRemotePath(jobDir)):
            self.mkdir(self.getRemotePath(jobDir))
        if append:
            operator = ">>"
        else:
            operator = ">"
        if self.account == None: # a local process
            jobPopen = subprocess.Popen("cat " + operator + " " + jobPath, shell=True, stdin=subprocess.PIPE)
        else:
            jobPopen = subprocess.Popen("ssh " + self.account + " '" + "cat " + operator + " " + jobPath + "'", shell=True, stdin=subprocess.PIPE)
        jobPopen.communicate(input=jobFileText)
        return self._getJobPath(jobDir, jobName)
    
    def _readJobFile(self, job):
        jobPath = self.getRemotePath(job)
        if not self.exists(jobPath):
            if self.debug:
                print >> sys.stderr, "Job status file", jobPath, "does not exist"
            return None
        jobLines = self.run("cat " + jobPath)
        if self.debug:
            print >> sys.stderr, "Job status file", jobPath, "=", jobLines
        #localJobFile = open(self.download(job), "rt")
        attrDict = {}
        for line in jobLines: #localJobFile:
            key, value = line.strip().split("=", 1)
            assert key not in attrDict, (key, value, attrDict, jobLines)
            attrDict[key] = value
        #localJobFile.close()
        return attrDict
    
    def submit(self, script=None, jobDir=None, jobName=None, stdout=None, stderr=None):
        """
        Queue a command.
        """
        if self.jobLimit != -1:
            self.waitForJobCount(self.jobLimit)
        script = self._getScript(script)
        logFiles = [None, None]
        if type(stdout) in types.StringTypes:
            print >> sys.stderr, "Job", jobName + "'s stdout at local file", stdout
            logFiles[0] = stdout = open(stdout, "wt")
        if type(stderr) in types.StringTypes:
            print >> sys.stderr, "Job", jobName + "'s stderr at local file", stderr
            logFiles[1] = stderr = open(stderr, "wt")
        script = self.makeJobScript(script, jobDir, jobName)
        if self.debug:
            print >> sys.stderr, "------- Job script -------"
            print >> sys.stderr, script
            print >> sys.stderr, "--------------------------"
        prevStatus = self.getJobStatus(self._getJobPath(jobDir, jobName))
        if self.resubmitOnlyFinished and prevStatus == "RUNNING":
            assert False, prevStatus
        # The job status file must be open before the job is submitted, so that the return code can be
        # written to it.
        self._writeJobFile(jobDir, jobName)
        # Submit the job
        if self.account == None: # a local process
            jobPopen = subprocess.Popen(script, shell=True, stdout=stdout, stderr=stderr)
        else:
            jobPopen = subprocess.Popen("ssh " + self.account + " '" + script + "'", shell=True, stdout=stdout, stderr=stderr)
        # The 'time' attribute marks a time after the program has started. When checking for the PID,
        # only those programs whose STIME < 'time' are considered.
        jobArgs = {"PID":jobPopen.pid, "time":time.time() + 10}
        job = self._writeJobFile(jobDir, jobName, jobArgs, append=True)
        # Keep track of log files so they can be closed
        if logFiles != [None, None]:
            assert job not in self._logs
            self._logs[job] = logFiles
        print >> sys.stderr, "Submitted job", jobArgs["PID"], jobArgs["time"]
        return job
    
    def makeJobScript(self, commands, jobDir=None, jobName=None):
        script = ""
        if self.preamble != None:
            script += self.preamble + ";"
        if jobDir != None:
            script += "cd " + jobDir + "; " + commands
        script += "; echo retcode=$? >> " + self.getRemotePath(self._getJobPath(jobDir, jobName)) # store return value
        return script
    
    def _closeLogs(self, job):
        if job in self._logs:
            if self._logs[job][0] != None:
                self._logs[job][0].close()
            if self._logs[job][1] != None:
                self._logs[job][1].close()
            del self._logs[job]
    
    def getUserName(self):
        if self.account != None:
            return self.account.split("@")[0]
        else:
            return getpass.getuser() #os.getlogin()
            
    def getNumJobs(self, includeQueued=True):
        #stdoutLines = self.run("ps -u " + self.getUserName())
        stdoutLines = self.run("ps -u " + self.getUserName() + " -o ppid")
        groupId = str(os.getpgrp())
        numProcesses = 0
        for line in stdoutLines:
            if line.strip() == groupId:
                numProcesses += 1
        return numProcesses
    
    def waitForJobCount(self, targetCount=0, pollIntervalSeconds=60, verbose=True):
        if targetCount == -1:
            return
        numJobs = self.getNumJobs()
        if numJobs <= targetCount:
            return
        waitTimer = Timer()
        while numJobs > targetCount:
            sleepTimer = Timer()
            accountName = self.account
            if self.account == None:
                accountName = "local"
            if verbose:
                sleepString = " [          ]     "
                print >> sys.stderr, "\rWaiting for " + str(numJobs) + " on " + accountName + " (limit=" + str(targetCount) + ")", waitTimer.elapsedTimeToString() + sleepString,
            while sleepTimer.getElapsedTime() < pollIntervalSeconds:
                if verbose:
                    steps = int(10 * sleepTimer.getElapsedTime() / pollIntervalSeconds) + 1
                    sleepString = " [" + steps * "." + (10-steps) * " " + "]     "
                    print >> sys.stderr, "\rWaiting for " + str(numJobs) + " on " + accountName + " (limit=" + str(targetCount) + ")", waitTimer.elapsedTimeToString() + sleepString,
                time.sleep(5)                
            numJobs = self.getNumJobs()
        print >> sys.stderr, "\nAll jobs done"
    
    def waitForJob(self, job, pollIntervalSeconds=10):
        while self.getJobStatus(job) not in ["FINISHED", "FAILED"]:
            time.sleep(pollIntervalSeconds)
    
    def waitForJobs(self, jobs, pollIntervalSeconds=60, timeout=None, verbose=True):
        print >> sys.stderr, "Waiting for results"
        waitTimer = Timer()
        while(True):
            jobStatus = {"FINISHED":0, "QUEUED":0, "FAILED":0, "RUNNING":0}
            for job in jobs:
                jobStatus[self.getJobStatus(job)] += 1
            jobStatusString = str(jobStatus["QUEUED"]) + " queued, " + str(jobStatus["RUNNING"]) + " running, " + str(jobStatus["FINISHED"]) + " finished, " + str(jobStatus["FAILED"]) + " failed"
            if jobStatus["QUEUED"] + jobStatus["RUNNING"] == 0:
                if verbose:
                    print >> sys.stderr, "\nAll runs done (" + jobStatusString + ")"
                break
            # decide what to do
            if timeout == None or timeoutTimer.getElapsedTime() < timeout:
                sleepTimer = Timer()
                accountName = self.account
                if self.account == None:
                    accountName = "local"
                if verbose:
                    sleepString = " [          ]     "
                    print >> sys.stderr, "\rWaiting for " + str(len(jobs)) + " on " + accountName + "(" + jobStatusString + "),", waitTimer.elapsedTimeToString() + sleepString,
                while sleepTimer.getElapsedTime() < pollIntervalSeconds:
                    if verbose:
                        steps = int(10 * sleepTimer.getElapsedTime() / pollIntervalSeconds) + 1
                        sleepString = " [" + steps * "." + (10-steps) * " " + "]     "
                        print >> sys.stderr, "\rWaiting for " + str(len(jobs)) + " on " + accountName + "(" + jobStatusString + "),", waitTimer.elapsedTimeToString() + sleepString,
                    time.sleep(5)                
            else:
                if verbose:
                    print >> sys.stderr, "\nTimed out, ", trainTimer.elapsedTimeToString()
                break
        return jobStatus
    
    def getJobStatusByName(self, jobDir, jobName):
        return self.getJobStatus(self._getJobPath(jobDir, jobName))
    
    def getJobStatus(self, job):
        # Get jobfile
        jobAttr = self._readJobFile(job)
        # Check whether job exists
        if jobAttr == None:
            return None
        # Check for a finished process
        if "retcode" in jobAttr:
            if jobAttr["retcode"] == "0":
                self._closeLogs(job)
                return "FINISHED"
            else:
                self._closeLogs(job)
                return "FAILED"
        
        # Check for a running process
        jobAttr["time"] = float(jobAttr["time"])
        currentTime = time.time()
        processes = []
        for line in self.run("ps -p " + jobAttr["PID"] + " -o etime")[1:]:
            line = line.strip()
            days = 0
            if "-" in line:
                days, line = line.split("-")
            hours = 0
            if line.count(":") == 2:
                hours, minutes, seconds = line.split(":")
            else:
                assert line.count(":") == 1, line
                minutes, seconds = line.split(":")
            elapsedTime = int(days) * 86400 + int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            #print days, hours, minutes, seconds
            #print elapsedTime, currentTime - elapsedTime, jobAttr["time"]
            if currentTime - elapsedTime <= jobAttr["time"]: # skip processes started after submit time (won't work with stopped processes)
                processes.append(jobAttr["PID"])
        assert len(processes) <= 1
        if len(processes) == 1:
            return "RUNNING"
        else:
            self._closeLogs(job)
            return "FAILED" # failed without writing return code

if __name__=="__main__":
    c = CSCConnection("remoteTest", "jakrbj@louhi.csc.fi", True)
    f = "/usr/share/biotext/Autumn2010/TriggerEdgeTest/TriggerEdge2TestDeterminismTest101103/uploadtest"
    c.upload(f)
    c.download(os.path.basename(f), "delme")
    #c.test()
    #c.exists("merg-info.py")
    #classifier.trainAndTestOnLouhi("trigger-train-examples", "trigger-test-examples", {"c":1000}, c)
    #print c.exists("trigger-test-examples")