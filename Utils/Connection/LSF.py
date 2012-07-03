import sys, os
import types
#import uuid
from ClusterConnection import ClusterConnection
import subprocess

class LSFConnection(ClusterConnection):
    def __init__(self, account=None, workDirBase=None, remoteSettingsPath=None, memory=4194304, cores=1):
        ClusterConnection.__init__(self, account, workDirBase, remoteSettingsPath)
        self.wallTime = "48:00"
        self.cores = 1
        self.modules = ["java", "python"]
        self.submitCommand = "bsub"
    
    def getJobStatus(self, job):
        if self.account == None:
            if not os.path.exists(job):
                return "QUEUED"
        else:
            if self.getFileStatus(job) == self.NOT_EXIST:
                return "QUEUED"

        lines = self.run("grep \"Resource usage summary:\" " + job)
        if len(lines) == 0:
            return "RUNNING"
        else:
            lines = self.run("grep \"Successfully completed.\" " + job)
            if len(lines) == 1:
                return "FINISHED"
            else:
                return "FAILED"
    
    def getNumJobs():
        """
        Get number of queued (pending or running) jobs
        """
        stdoutLines = self.run("bjobs | grep " + self.getUserName() + " | wc -l")
        return len(stdoutLines)
    
    def makeJobScript(self, script, name, jobWorkDir=None, stderr=None, stdout=None, wallTime=None, modules=None):
        """
        Make an LSF job submission script
        
        jobWorkDir = absolute path on the remote machine
        """
        if script == None:
            script = "\n".join(self.commands)
            self.commands = []
            
        s = "#!/bin/sh \n"
        s += "##execution shell environment \n\n"
        if jobWorkDir != None:
            s += "##OUTDIR: " + jobWorkDir + " \n\n"
        s += "##Memory limit \n"
        s += "#BSUB -M 4200000 \n"
        s += "##Max runtime \n"
        if wallTime == None:
            wallTime = self.wallTime
        s += "#BSUB -W " + wallTime + "\n" #48:00 \n"
        s += "#BSUB -J " + name + "\n"
        stdout, stderr = self.getStreams(stdout, stderr, name, jobWorkDir)
        s += "#BSUB -o " + stdout + "\n"
        s += "#BSUB -e " + stderr + "\n"
        s += "#BSUB -n 1 \n\n"
        
        s += "mkdir -p " + os.path.dirname(stdout) + "\n" # ensure output directory exists
        s += "mkdir -p " + os.path.dirname(stderr) + "\n" # ensure output directory exists
        
        if modules == None:
            modules = self.modules
        for module in modules:
            s += "module load " + module + "\n"
        if self.remoteSettingsPath != None: # Use a specific configuration file
            s += "export TEES_SETTINGS=" + self.remoteSettingsPath + "\n"
        if jobWorkDir != None:
            s += "mkdir -p " + jobWorkDir + "\n" # ensure output directory exists
            s += "cd " + jobWorkDir + "\n\n"
        s += script
        
        return s, stdout, stderr
