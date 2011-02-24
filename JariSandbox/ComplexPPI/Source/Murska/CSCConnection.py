import sys, os
import subprocess
sys.path.append(os.path.abspath(os.path.dirname(__file__))+"/..")
#from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier as classifier
from Utils.Timer import Timer

class CSCConnection:    
    def __init__(self, workSubDir, account="jakrbj@louhi.csc.fi", deleteWorkDir=False, memory=4194304, cores=1):
        self.account = account
        self.memory = memory
        self.cores = cores
        self.machineName = account.split("@")[-1]
        self.setWorkSubDir(workSubDir, deleteWorkDir)        
        # State constants
        self.NOT_EXIST = "NOT_EXIST"
        self.NONZERO = "NONZERO"
        self.ZERO = "ZERO"
        
        # Batch job queue
        self.commands = []
        
        self.compression = True
    
    def setWorkSubDir(self, workSubDir, deleteWorkDir=False):
        self.workDir = "/wrk/jakrbj/" + workSubDir
        if deleteWorkDir:
            assert workSubDir != None and workSubDir != ""
            print "Removing CSC work directory (if it exists)"
            self.run("rm -fr " + self.workDir)
        self.run("mkdir -p " + self.workDir)
    
    def exists(self, filename):
        p = subprocess.Popen("ssh " + self.account + " 'ls -lh " + self.workDir + "/" + filename + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if len(p.stdout.readlines()) > 0:
            return True
        else:
            return False
    
    def mkdir(self, dir):
        p = subprocess.Popen("ssh " + self.account + " 'mkdir -p " + self.workDir + "/" + dir + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if len(p.stdout.readlines()) > 0:
            return True
        else:
            return False
    
    def getFileStatus(self, filename):
        filePath = self.workDir + "/" + filename
        p = subprocess.Popen("ssh " + self.account + " 'filetest -e " + filePath + "; filetest -z " + filePath + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lines = p.stdout.readlines()
        assert len(lines) == 2
        if int(lines[0]) == 0:
            return self.NOT_EXIST
        if int(lines[1]) == 1:
            return self.ZERO
        else:
            return self.NONZERO
        
    def upload(self, src, dst=None, replace=True):
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and self.exists(dst):
            return False
        else:
            if self.compression:
                print >> sys.stderr, "Compressing " + src + ": ",
                subprocess.call("gzip -fv < " + src + " > " + src + ".gz", shell=True)
                src += ".gz"
                dst += ".gz"
            print "scp " + src + " " + self.account + ":" + self.workDir + "/" + dst
            subprocess.call("scp " + src + " " + self.account + ":" + self.workDir + "/" + dst, shell=True)
            if self.compression:
                self.run("gunzip -fv " + self.workDir + "/" + dst)
            return True
        
    def download(self, src, dst=None, replace=True):
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and os.path.exists(dst):
            return False
        else:
            if self.compression:
                print >> sys.stderr, "Compressing " + src + ": ",
                self.run("gzip < " + self.workDir + "/" + src + " > " + self.workDir + "/" + src + ".gz")
                src = src + ".gz"
                dst = dst + ".gz"
            #print "SCP:", "scp " + self.account + ":" + self.workDir + "/" + src + " " + dst
            subprocess.call("scp " + self.account + ":" + self.workDir + "/" + src + " " + dst, shell=True)
            if self.compression:
                subprocess.call("gunzip -f " + dst, shell=True)
            return True
    
    def run(self, script, cdWrkDir=False):
        if cdWrkDir:
            script = "cd " + self.workDir + " ; " + script
        #print "SCRIPT:", script
        subprocess.call("ssh " + self.account + " '" + script + "'", shell=True)
    
    def test(self):
        print "testing"
        subprocess.call("ssh jakrbj@louhi.csc.fi 'ls; exit'", shell=True)
        subprocess.call("scp scp-test-file.txt jakrbj@louhi.csc.fi:/home/u1/jakrbj/scp-test-file.txt", shell=True)
        #p = subprocess.Popen("ls", stdout=subprocess.PIPE)
        #print p.stdout.readlines()
    
    def beginJob(self):
        self.commands = []
    
    def addCommand(self, string):
        self.commands.append(string)
    
    def submitJob(self, localWorkDir, name):
        if self.account.find("murska") != -1:
            isMurska = True
        else:
            isMurska = False
        scriptName = name
        if self.exists(scriptName):
            print >> sys.stderr, "Script already on " + cscConnection.machineName + ", process not queued for", scriptName
            return False
        
        # Build script
        scriptFilePath = scriptName
        if localWorkDir != None:
            scriptFilePath = os.path.join(localWorkDir, scriptName)
        scriptFile = open(scriptFilePath, "wt")
        scriptFile.write("#!/bin/bash\ncd " + self.workDir + "\n")
        # write commands to script
        for command in self.commands:
            if not isMurska: # louhi
                scriptFile.write("aprun -n 1 ")
            scriptFile.write(command + "\n")
        scriptFile.close()
                
        self.upload(scriptFilePath, scriptName)
        self.run("chmod a+x " + self.workDir + "/" + scriptName)
        cscScriptPath = self.workDir + "/" + scriptName
        if isMurska:
            runCmd = "bsub -o " + cscScriptPath + "-stdout -e " + cscScriptPath + "-stderr -W 10:0 -M " + str(self.memory) 
            if self.cores != 1:
                runCmd += " -n " + str(self.cores)
            runCmd += " < " + cscScriptPath
            self.run(runCmd)
        else:
            self.run("qsub -o " + self.workDir + "/" + scriptName + "-stdout -e " + self.workDir + "/" + scriptName + "-stderr " + self.workDir + "/" + scriptName)
        
        self.commands = []

    def getJobStatus(scriptName):
        filePath = self.workDir + "/" + scriptName + "-stdout"
        stdoutStatus = self.getFileStatus(scriptName + "-stdout")
        if stdoutStatus == self.NOT_EXIST:
            return "QUEUED"

        p = subprocess.Popen("ssh " + self.account + " 'grep \"Resource usage summary:\" " + filePath + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lines = p.stdout.readlines()
        if len(lines) == 0:
            return "RUNNING"
        else:
            p = subprocess.Popen("ssh " + self.account + " 'grep \"Successfully completed.\" " + filePath + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            lines = p.stdout.readlines()
            if len(lines) == 1:
                return "FINISHED"
            else:
                return "FAILED"
    
    def waitForJobs(self, scriptNames, timeout=None):
        assert len(scriptNames) == len(outputFileNames)
        print >> sys.stderr, "Waiting for results"
        finished = 0
        louhiTimer = Timer()
        combinationStatus = {}
        while(True):
            # count finished
            finished = 0
            processStatus = {"FINISHED":0, "QUEUED":0, "FAILED":0, "RUNNING":0}
            for scriptName in scriptNames:
                status = self.getLouhiStatus(scriptName)
                combinationStatus[id] = status
                processStatus[status] += 1
            p = processStatus
            processStatusString = str(p["QUEUED"]) + " queued, " + str(p["RUNNING"]) + " running, " + str(p["FINISHED"]) + " finished, " + str(p["FAILED"]) + " failed"
            if processStatus["QUEUED"] + processStatus["RUNNING"] == 0:
                print >> sys.stderr
                print >> sys.stderr, "All jobs done (" + processStatusString + ")"
                break
            # decide what to do
            if timeout == None or louhiTimer.getElapsedTime() < timeout:
                sleepString = " [          ]     "
                print >> sys.stderr, "\rWaiting for " + str(len(combinations)) + " on " + cscConnection.machineName + "(" + processStatusString + "),", louhiTimer.elapsedTimeToString() + sleepString,
                #time.sleep(60)
                sleepTimer = Timer()
                while sleepTimer.getElapsedTime() < 60:
                    steps = int(10 * sleepTimer.getElapsedTime() / 60) + 1
                    sleepString = " [" + steps * "." + (10-steps) * " " + "]     "
                    print >> sys.stderr, "\rWaiting for " + str(len(combinations)) + " on " + cscConnection.machineName + "(" + processStatusString + "),", louhiTimer.elapsedTimeToString() + sleepString,
                    time.sleep(5)                
            else:
                print >> sys.stderr
                print >> sys.stderr, "Timed out, ", louhiTimer.elapsedTimeToString()
                return False
        return True


if __name__=="__main__":
    c = CSCConnection("remoteTest", "jakrbj@louhi.csc.fi", True)
    f = "/usr/share/biotext/Autumn2010/TriggerEdgeTest/TriggerEdge2TestDeterminismTest101103/uploadtest"
    c.upload(f)
    c.download(os.path.basename(f), "delme")
    #c.test()
    #c.exists("merg-info.py")
    #classifier.trainAndTestOnLouhi("trigger-train-examples", "trigger-test-examples", {"c":1000}, c)
    #print c.exists("trigger-test-examples")