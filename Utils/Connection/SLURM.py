import sys, os
import types
import uuid
import subprocess
from ClusterConnection import ClusterConnection

class SLURMConnection(ClusterConnection):
    def __init__(self, account=None, workDirBase=None, remoteSettingsPath=None):
        ClusterConnection.__init__(self, account, workDirBase, remoteSettingsPath)
        self.wallTime = "48:00:00"
        self.cores = 1
        self.modules = ["python"]
        self.submitCommand = "sbatch"
    
    def submit(self, script=None, jobWorkDir=None, name=None, stdout=None, stderr=None):
        if name == None:
            name = uuid.uuid1().hex
        script, stdout, stderr = self.makeJobScript(script, name, jobWorkDir, stderr, stdout)
        if self.account == None:
            command = [self.submitCommand]
        else:
            command = ["ssh", self.account, "'" + self.submitCommand + "'"]
        if self.debug:
            print >> sys.stderr, "------- Job script -------"
            print >> sys.stderr, script
            print >> sys.stderr, "--------------------------"
        print >> sys.stderr, "Submitting job", stdout
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        pstdout = p.communicate(input=script)[0]
        print >> sys.stderr, pstdout
        assert pstdout.startswith("Submitted batch job"), pstdout
        jobId = int(pstdout.split()[-1])
        return jobId
    
    def getJobStatus(self, job):
        strJob = str(job)
        for line in self.run("sacct -u " + self.getUsername() + " -j " + strJob):
            splits = line.split()
            #print splits
            if splits[0] == strJob:
                jobStatus = splits[5]
                if jobStatus in ["RUNNING", "COMPLETING"]:
                    return "RUNNING"
                elif jobStatus == "COMPLETED":
                    return "FINISHED"
                elif jobStatus in ["FAILED", "CANCELLED", "NODE_FAIL", "PREEMPTED", "TIMEOUT"]:
                    return "FAILED"
                elif jobStatus in ["PENDING", "RESIZING", "SUSPENDED"]:
                    return "QUEUED"
                else:
                    assert False, jobStatus
        return "QUEUED"

    def makeJobScript(self, script, name, jobWorkDir=None, stderr=None, stdout=None, wallTime=None, modules=None, cores=None):
        """
        Make a SLURM job submission script
        """
        script = self.getScript(script, "\n")

        s = "#!/bin/bash -l \n"
        s += "##execution shell environment \n\n"
        
        stdout, stderr = self.getStreams(stdout, stderr, name, jobWorkDir)
        s += "## name of your job" + "\n"
        s += "#SBATCH -J " + name + "\n"
        s += "## system error message output file" + "\n"
        s += "#SBATCH -e " + stderr + "\n"
        s += "## system message output file" + "\n"
        s += "#SBATCH -o " + stdout + "\n"
        s += "## a per-process (soft) memory limit" + "\n"
        s += "## limit is specified in MB" + "\n"
        s += "## example: 1 GB is 1000" + "\n"
        #s += "#SBATCH --mem-per-cpu=16000" + "\n"
        s += "#SBATCH --mem-per-cpu=4000" + "\n"
        if wallTime == None:
            wallTime = self.wallTime
        s += "## how long a job takes, wallclock time hh:mm:ss" + "\n"
        s += "#SBATCH -t " + wallTime + "\n"
        if cores == None:
            cores = self.cores
        s += "## number of processes" + "\n"
        s += "#SBATCH -n " + str(cores) + "\n"
        
        s += "mkdir -p " + os.path.dirname(stdout) + "\n" # ensure output directory exists
        s += "mkdir -p " + os.path.dirname(stderr) + "\n" # ensure output directory exists
        
        #s += "module load java \n"
        if modules == None:
            modules = self.modules
        for module in modules:
            s += "module load " + module + "\n"
        if self.remoteSettingsPath != None: # Use a specific configuration file
            s += "export TEES_SETTINGS=/v/users/jakrbj/TEESLocalSettings.py \n"
        
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
