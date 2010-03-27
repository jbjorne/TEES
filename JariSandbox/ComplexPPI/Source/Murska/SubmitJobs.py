import sys, os, shutil
import subprocess
import time
from optparse import OptionParser

def numJobs(username="jakrbj"):
    """
    Get number of queued (pending or running) jobs
    """
    p = subprocess.Popen("bjobs | grep " + username + " | wc -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = p.stdout.readlines()
    assert len(lines) == 1
    return int(lines[0])

def submit(jobFile):
    """
    Inserts a job into the queue
    """
    f = open(jobFile, "rt")
    dirline = f.readlines()[3]
    f.close()
    assert dirline.find("OUTDIR")
    outDir = dirline.split()[-1]
    
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    
    jobName = os.path.basename(jobFile)
    shutil.move(jobFile, outDir + "/" + jobName)
    
    #subprocess.call("bsub < " + outDir + "/" + jobName, shell=True)
    print "Queued job", outDir + "/" + jobName

def update(queueDir, jobLimit):
    """
    Main method, adds jobs to queue
    """
    while(True):
        # Check number of submitted jobs
        currNumJobs = numJobs()
        if currNumJobs >= jobLimit:
            print >> sys.stderr, "Queue full, waiting"
            sleep(60*20) # wait twenty minutes
        
        # Look for waiting jobs
        inFiles = os.listdir(queueDir)
        if len(inFiles) == 0:
            print >> sys.stderr, "No jobs to be submitted, waiting"
            sleep(60*60) # wait an hour            
        
        # Submit jobs
        submitCount = 0
        for inFile in inFiles:
            if inFile.find("~") != -1: # temporary backup file
                continue
            
            submitCount += 1
            if submitCount + currNumJobs >= jobLimit:
                break
            
if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-q", "--queue", default="/wrk/jakrbj/jobqueue", dest="queue", help="job queue directory")
    optparser.add_option("-l", "--limit", default=10, type="int", dest="limit", help="max jobs submitted or running at once")
    (options, args) = optparser.parse_args()
    assert options.queue != None
    assert os.path.exists(options.queue)
    
    update(options.workdir, options.limit)
