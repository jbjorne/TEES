import sys, os
import types
#import uuid
from UnixConnection import UnixConnection
import subprocess

class ClusterConnection(UnixConnection):
    def __init__(self, account=None, workdir=None, settings=None, memory=None, cores=None, modules=None, wallTime=None, preamble=None, debug=False):
        UnixConnection.__init__(self, killGroup=False, account=account, workdir=workdir, settings=settings, memory=memory, cores=cores, preamble=preamble, debug=debug)
        self.wallTime = wallTime
        self.modules = modules
        self.submitCommand = None
        self.jobListCommand = None
        self.jobTemplate = None
    
    def getJobStatus(self, job):
        jobAttr = self._readJobFile(job)
        # Check whether job exists
        if jobAttr == None:
            return None
        
        if "retcode" not in jobAttr:
            return "QUEUED" # could be also RUNNING, but without using the cluster-specific job list we can't know
        elif jobAttr["retcode"] == "0":
            return "FINISHED"
        else:
            return "FAILED"
    
    def submit(self, script=None, jobDir=None, jobName=None, stdout=None, stderr=None):
        prevStatus = self.getJobStatus(self._getJobPath(jobDir, jobName))
        if self.resubmitOnlyFinished and prevStatus in ["RUNNING", "QUEUED"]:
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
        if self.debug:
            print >> sys.stderr, "Submitting job", jobName, "with command", command
        else:
            print >> sys.stderr, "Submitting job", jobName
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.communicate(input=script)

    def getNumJobs(self):
        """
        Get number of queued (pending or running) jobs
        """
        stdoutLines = self.run(self.jobListCommand + " | grep " + self.getUserName() + " | wc -l")
        assert len(stdoutLines) == 1, stdoutLines
        assert stdoutLines[0].strip().isdigit(), stdoutLines
        return int(stdoutLines[0].strip())

    def getStreams(self, stdout, stderr, jobDir, jobName):
        if stderr == None:
            stderr = self._getJobPath(jobDir, jobName) + ".stderr"
        stderr = self.getRemotePath(stderr)
        if stdout == None:
            stdout = self._getJobPath(jobDir, jobName) + ".stdout"
        stdout = self.getRemotePath(stdout)
        return stdout, stderr

    def makeJobScript(self, script, jobDir=None, jobName=None, stdout=None, stderr=None, wallTime=None, modules=None, cores=None, memory=None):
        stdout, stderr = self.getStreams(stdout, stderr, jobDir, jobName)
        if memory == None: memory = self.memory
        if wallTime == None: wallTime = self.wallTime
        if cores == None: cores = self.cores
        
        template = self.jobTemplate
        template = template.replace("%job", jobName)
        template = template.replace("%stdoutDir", os.path.dirname(stdout))
        template = template.replace("%stderrDir", os.path.dirname(stderr))
        template = template.replace("%stdout", stdout)
        template = template.replace("%stderr", stderr)
        template = template.replace("%memory", str(memory))
        template = template.replace("%wallTime", str(wallTime))
        template = template.replace("%cores", str(cores))
        
        commands = ""
        if self.preamble != None:
            commands += self.preamble + "\n"
        if modules == None:
            modules = self.modules
        if modules != None:
            if isinstance(modules, basestring): # just one module to load
                modules = [modules]
            for module in modules:
                commands += "module load " + module + "\n"
        if self.remoteSettingsPath != None: # Use a specific configuration file
            commands += "export TEES_SETTINGS=" + self.remoteSettingsPath + "\n"
        if jobDir != None:
            commands += "mkdir -p " + self.getRemotePath(jobDir) + "\n" # ensure output directory exists
            commands += "cd " + self.getRemotePath(jobDir) + "\n\n" # move to output directory where the program will be run
        commands += script + "\n"
        # Store return value in job file
        commands += "echo retcode=$? >> " + self.getRemotePath(self._getJobPath(jobDir, jobName))
        
        template = template.replace("%commands", commands)
        assert "%" not in template, template
        return template
