import sys, os
import types
import uuid
from Unix import UnixConnection
import subprocess

class ClusterConnection(UnixConnection):
    def __init__(self, account=None, workDirBase=None, remoteSettingsPath=None, memory=4194304, cores=1):
        UnixConnection.__init__(self, account, workDirBase, remoteSettingsPath)
        self.wallTime = None
        self.cores = 1
        self.modules = []
        self.submitCommand = None
    
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
        return stdout

    def getStreams(self, stdout, stderr, jobDir, jobName):
        if stderr == None:
            stderr = self._getJobPath(jobDir, jobName) + ".stderr"
        stderr = self.getRemotePath(stderr)
        if stdout == None:
            stdout = self._getJobPath(jobDir, jobName) + ".stdout"
        stdout = self.getRemotePath(stdout)
        return stdout, stderr