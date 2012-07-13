from ClusterConnection import ClusterConnection

LSFJobTemplate = """#!/bin/sh
##execution shell environment

##Memory limit
#BSUB -M %memory
##Max runtime
#BSUB -W %wallTime
#BSUB -o %stdout
#BSUB -e %stderr
#BSUB -n %cores

mkdir -p %stderrDir
mkdir -p %stdoutDir

%commands"""

class LSFConnection(ClusterConnection):
    """
    For using the Load Sharing Facility (LSF) of Platform Computing (www.platform.com).
    """
    def __init__(self, account=None, workdir=None, settings=None, wallTime=None, memory=None, cores=None, modules=None):
        if wallTime == None:
            wallTime = "48:00"
        if memory == None:
            memory = 4194304
        #if modules == None:
        #    modules = ["java", "python"]
        ClusterConnection.__init__(self, account=account, workdir=workdir, settings=settings, memory=memory, cores=cores, modules=modules, wallTime=wallTime)
        self.submitCommand = "bsub"
        self.jobListCommand = "bjobs"
        self.jobTemplate = LSFJobTemplate
