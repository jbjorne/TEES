import sys, os
import subprocess
sys.path.append(os.path.dirname(__file__)+"/..")
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier as classifier

class CSCConnection:    
    def __init__(self, workSubDir, account="jakrbj@louhi.csc.fi", deleteWorkDir=False, memory=4194304, cores=1):
        self.account = account
        self.memory = memory
        self.cores = cores
        self.machineName = account.split("@")[-1]
        self.workDir = "/wrk/jakrbj/" + workSubDir
        if deleteWorkDir:
            print "Removing CSC work directory (if it exists)"
            self.run("rm -fr " + self.workDir)
        self.run("mkdir -p " + self.workDir)
        
        # State constants
        self.NOT_EXIST = "NOT_EXIST"
        self.NONZERO = "NONZERO"
        self.ZERO = "ZERO"
        
        # Batch job queue
        self.commands = []
    
    def exists(self, filename):
        p = subprocess.Popen("ssh " + self.account + " 'ls " + self.workDir + "/" + filename + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            print "scp " + src + " " + self.account + ":" + self.workDir + "/" + dst
            subprocess.call("scp " + src + " " + self.account + ":" + self.workDir + "/" + dst, shell=True)
            return True
        
    def download(self, src, dst=None, replace=True):
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and os.path.exists(dst):
            return False
        else:
            subprocess.call("scp " + self.account + ":" + self.workDir + "/" + src + " " + dst, shell=True)
            return True
    
    def run(self, script):
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
        if cscConnection.exists(scriptName):
            print >> sys.stderr, "Script already on " + cscConnection.machineName + ", process not queued for", scriptName
            return False
        
        # Build script
        scriptFilePath = scriptName
        if localWorkDir != None:
            scriptFilePath = os.path.join(localWorkDir, scriptName)
        scriptFile = open(scriptFilePath, "wt")
        scriptFile.write("#!/bin/bash\ncd " + cscConnection.workDir + "\n")
        # write commands to script
        for command in commands:
            if not isMurska: # louhi
                scriptFile.write("aprun -n 1 ")
            scriptFile.write(command + "\n")
        scriptFile.close()
        
        return
        
        cscConnection.upload(scriptFilePath, scriptName)
        cscConnection.run("chmod a+x " + cscConnection.workDir + "/" + scriptName)
        cscScriptPath = self.workDir + "/" + scriptName
        if isMurska:
            runCmd = "bsub -o " + cscScriptPath + "-stdout -e " + cscScriptPath + "-stderr -W 10:0 -M " + str(self.memory) 
            if cscConnection.cores != 1:
                runCmd += " -n " + str(self.cores)
            runCmd += " < " + cscScriptPath
            cscConnection.run(runCmd)
        else:
            cscConnection.run("qsub -o " + cscConnection.workDir + "/" + scriptName + "-stdout -e " + cscConnection.workDir + "/" + scriptName + "-stderr " + cscConnection.workDir + "/" + scriptName)
        
        self.commands = []
        return idStr

if __name__=="__main__":
    c = CSCConnection("remoteTest")
    #c.test()
    #c.exists("merg-info.py")
    classifier.trainAndTestOnLouhi("trigger-train-examples", "trigger-test-examples", {"c":1000}, c)
    print c.exists("trigger-test-examples")