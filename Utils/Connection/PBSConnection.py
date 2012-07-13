from ClusterConnection import ClusterConnection

PBSJobTemplate = """#!/bin/sh
##execution shell environment

#PBS -N %job
##Memory limit
##Max runtime
#PBS -l walltime=%wallTime
#PBS -o %stdout
#PBS -e %stderr

mkdir -p %stderrDir
mkdir -p %stdoutDir

%commands"""

class PBSConnection(ClusterConnection):
    """
    For using Portable Batch System Professional (PBS Pro) of Altair Engineering (http://www.altair.com).
    """
    def __init__(self, account=None, workdir=None, settings=None, wallTime=None, memory=None, cores=None, modules=None):
        if wallTime == None:
            wallTime = "48:00:00"
        if memory == None:
            memory = 4194304
        ClusterConnection.__init__(self, account=account, workdir=workdir, settings=settings, memory=memory, cores=cores, modules=modules, wallTime=wallTime)
        self.submitCommand = "qsub"
        self.jobListCommand = "qstat"
        self.jobTemplate = PBSJobTemplate
    
    def addCommand(self, string):
        self.commands.append("aprun -n 1 " + string)
