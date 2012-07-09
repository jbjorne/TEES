import sys, os
import types
#import uuid
import subprocess
from ClusterConnection import ClusterConnection

class SLURMConnection(ClusterConnection):
    def __init__(self, account=None, workDirBase=None, remoteSettingsPath=None):
        ClusterConnection.__init__(self, account, workDirBase, remoteSettingsPath)
        self.wallTime = "48:00:00"
        self.cores = 1
        self.memory = 4000
        self.modules = ["python"]
        self.submitCommand = "sbatch"
    
    def submit(self, script=None, jobDir=None, jobName=None, stdout=None, stderr=None):
        prevStatus = self.getJobStatus(self._getJobPath(jobDir, jobName))
        if self.resubmitOnlyFinished and prevStatus == "RUNNING":
            raise Exception("Tried to resubmit a job whose current status is", prevStatus)

        script = self._getScript(script, "\n")
        #if name == None:
        #    name = uuid.uuid1().hex
        script = self.makeJobScript(script, jobDir, jobName, stdout, stderr)
        if self.account == None:
            command = [self.submitCommand]
        else:
            command = ["ssh", self.account, "'" + self.submitCommand + "'"]
        if self.debug:
            print >> sys.stderr, "------- Job script -------"
            print >> sys.stderr, script
            print >> sys.stderr, "--------------------------"
        # The job status file must be open before the job is submitted, so that the return code can be
        # written to it.
        self._writeJobFile(jobDir, jobName)
        print >> sys.stderr, "Submitting job", jobName
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        pstdout = p.communicate(input=script)[0]
        print >> sys.stderr, pstdout
        assert pstdout.startswith("Submitted batch job"), pstdout
        jobId = int(pstdout.split()[-1])
        return self._writeJobFile(jobDir, jobName, {"SLURMID":jobId}, append=True)
    
    def getNumJobs(self):
        """
        Get number of queued (pending or running) jobs
        """
        stdoutLines = self.run("squeue | grep " + self.getUserName() + " | wc -l")
        return len(stdoutLines)
    
    def getJobStatus(self, job):
        jobAttr = self._readJobFile(job)
        # Check whether job exists
        if jobAttr == None:
            return None
        for line in self.run("sacct -u " + self.getUserName() + " -j " + jobAttr["SLURMID"]):
            line = line.strip()
            splits = line.split()
            #if self.debug:
            #    print >> sys.stderr, "sacct line:", line
            #print splits
            if splits[0] == jobAttr["SLURMID"]:
                if self.debug:
                    print >> sys.stderr, "sacct:", line
                jobStatus = splits[5]
                if jobStatus in ["RUNNING", "COMPLETING"]:
                    return "RUNNING"
                elif jobStatus == "COMPLETED":
                    if "retcode" not in jobAttr: # file hasn't had the time to be updated?
                        return "RUNNING"
                    elif jobAttr["retcode"] == "0":
                        return "FINISHED"
                    else:
                        return "FAILED"
                elif jobStatus in ["FAILED", "CANCELLED", "NODE_FAIL", "PREEMPTED", "TIMEOUT"]:
                    return "FAILED"
                elif jobStatus in ["PENDING", "RESIZING", "SUSPENDED"]:
                    return "QUEUED"
                else:
                    assert False, jobStatus
        return "QUEUED"

    def makeJobScript(self, script, jobDir=None, jobName=None, stdout=None, stderr=None, wallTime=None, modules=None, cores=None, memory=None):
        """
        Make a SLURM job submission script
        """
        s = "#!/bin/bash -l \n"
        s += "##execution shell environment \n\n"
        
        #stdout, stderr = self.getStreams(stdout, stderr, name, jobWorkDir)
        s += "## name of your job" + "\n"
        s += "#SBATCH -J " + jobName + "\n"
        stdout, stderr = self.getStreams(stdout, stderr, jobDir, jobName)
        s += "## system error message output file" + "\n"
        s += "#SBATCH -e " + stderr + "\n"
        s += "## system message output file" + "\n"
        s += "#SBATCH -o " + stdout + "\n"
        s += "## a per-process (soft) memory limit" + "\n"
        s += "## limit is specified in MB" + "\n"
        s += "## example: 1 GB is 1000" + "\n"
        #s += "#SBATCH --mem-per-cpu=16000" + "\n"
        if memory == None: memory = self.memory
        s += "#SBATCH --mem-per-cpu=" + str(memory) + "\n"
        if wallTime == None: wallTime = self.wallTime
        s += "## how long a job takes, wallclock time hh:mm:ss" + "\n"
        s += "#SBATCH -t " + wallTime + "\n"
        if cores == None: cores = self.cores
        s += "## number of processes" + "\n"
        s += "#SBATCH -n " + str(cores) + "\n"
        
        s += "mkdir -p " + os.path.dirname(stdout) + "\n" # ensure output directory exists
        s += "mkdir -p " + os.path.dirname(stderr) + "\n" # ensure output directory exists
                
        if modules == None:
            modules = self.modules
        for module in modules:
            s += "module load " + module + "\n"
        if self.remoteSettingsPath != None: # Use a specific configuration file
            s += "export TEES_SETTINGS=" + self.remoteSettingsPath + "\n"
        if jobDir != None:
            s += "mkdir -p " + self.getRemotePath(jobDir) + "\n" # ensure output directory exists
            s += "cd " + self.getRemotePath(jobDir) + "\n\n" # move to output directory where the program will be run
        s += script + "\n"
        # Store return value in job file
        s += "echo retcode=$? >> " + self.getRemotePath(self._getJobPath(jobDir, jobName))
        
        return s
