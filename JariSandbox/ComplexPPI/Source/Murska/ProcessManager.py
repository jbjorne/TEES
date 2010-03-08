import sys, os
import subprocess
import time
from optparse import OptionParser

logFile = None

def makeJobScript(jobName, inputFile, outDir, workDir):
    """
    Make a Murska job submission script
    """
    s = "#!/bin/sh \n"
    s += "##execution shell environment \n\n"

    s += "##Memory limit \n"
    s += "#BSUB -M 4200000 \n"
    s += "##Max runtime \n"
    s += "#BSUB -W 48:00 \n"
    s += "#BSUB -o " + jobName + ".stdout \n"
    s += "#BSUB -e " + jobName + ".stderr \n"
    s += "#BSUB -n 1 \n\n"
    
    s += "echo $PWD \n"
    s += "#module load python/2.5.1-gcc \n\n"
    
    s += "export PATH=$PATH:/v/users/jakrbj/cvs_checkout \n"
    s += "export PYTHONPATH=$PYTHONPATH:/v/users/jakrbj/cvs_checkout/CommonUtils \n"
    s += "cd /v/users/jakrbj/cvs_checkout/JariSandbox/ComplexPPI/Source/Pipelines \n\n"
    
    s += "/v/users/jakrbj/Python-2.5/bin/python MurskaSharedTask.py -i " + inputFile + " -o " + outDir + " -w " + workDir + "\n"
    
    return s

def numJobs(username="jakrbj"):
    """
    Get number of queued (pending or running) jobs
    """
    p = subprocess.Popen("bjobs | grep " + username + " | wc -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = p.stdout.readlines()
    assert len(lines) == 1
    return int(lines[0])

def queue(inFile, outDir, workDir, jobLimit):
    """
    Inserts a job into the queue if there is room
    """
    if numJobs() >= jobLimit:
        print >> sys.stderr, "Queue full, job not queued for", inFile
        return False
    
    jobScript = os.path.join(outDir, os.path.basename(inFile) + "-job")
    jobFile = open(jobScript, "wt" )
    # a unique workdir is needed, because the processes execute in parallel
    workDir = os.path.join(workDir, os.path.basename(inFile) + "-job")
    jobFile.write(makeJobScript(jobScript, inFile, outDir, workDir))
    jobFile.close()
    
    subprocess.call("bsub < " + jobScript, shell=True)
    log( "Queued job " + str(jobScript) )
    return True
    
def removeFiles(files, path):
    """
    Removes the selected files, used when reprocessing an input file
    """
    for file in files:
        log( "Removing output file " + str(file) )
        os.remove(os.path.join(path, file))

def update(inDir, outDir, workDir, jobLimit):
    """
    Main method, checks if new input files need to be processed
    """
    if numJobs() >= jobLimit:
        print >> sys.stderr, "Queue full, no jobs processed"
        return
    
    inFiles = os.listdir(inDir)
    outFiles = os.listdir(outDir)
    
    outFilesByStem = {}
    print outFiles
    for outFile in outFiles:
        fileStem = outFile.rsplit("-", 1)[0]
        if not outFilesByStem.has_key(fileStem):
            outFilesByStem[fileStem] = set()
        outFilesByStem[fileStem].add(outFile)
    
    submitCount = 0
    print inFiles
    for inFile in inFiles:
        if inFile.find("~") != -1: # temporary backup file
            continue
        elif not outFilesByStem.has_key(inFile): # input file not yet processed
            submitCount += int( queue(os.path.join(inDir, inFile), outDir, workDir, jobLimit) )
        elif inFile + "-job" not in outFilesByStem[inFile]: # input file needs to be reprocessed
            removeFiles(outFilesByStem[inFile], outDir)
            submitCount += int( queue(os.path.join(inDir, inFile), outDir, workDir, jobLimit) )
    if submitCount == 0:
        print >> sys.stderr, "Queued", submitCount, "jobs"
    else:
        log("Queued " + str(submitCount) + " jobs for this update")

def log(string):
    global logFile
    print >> sys.stderr, string
    if logFile != None:
        logFile.write( time.strftime("[%d.%m.%y-%H:%M:%S] ") + string + "\n")

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-w", "--workdir", default="/wrk/jakrbj/shared-task-test", dest="workdir", help="working directory")
    optparser.add_option("-l", "--log", default=None, dest="log", help="Process Manager log file")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    assert options.output != None
    assert os.path.exists(options.output)
    
    if options.log != None:
        logFile = open(options.log, "at")
    update(options.input, options.output, options.workdir, 10)
    if options.log != None:
        logFile.close()