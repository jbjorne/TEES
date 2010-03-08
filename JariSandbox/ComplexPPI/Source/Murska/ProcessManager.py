import sys, os
import subprocess
from optparse import OptionParser

def makeJobScript(jobName, inputFile, outDir, workDir):
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
    p = subprocess.Popen("bjobs | grep " + username + " | wc -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = p.stdout.readlines()
    assert len(lines) == 1
    return int(lines[0])

def queue(inFile, outDir, workDir):
    if numJobs() >= jobLimit:
        print >> sys.stderr, "Queue full, job not queued for", inFile
        return
    
    jobScript = os.path.join(outDir, + os.path.basename(inFile) + "-job")
    jobFile = open(jobScript, "wt" )
    jobFile.write(makeJobScript(jobScript, inFile, outDir, workDir))
    jobFile.close()
    
    #subprocess.call("bsub < " + jobScript, shell=True)
    print >> sys.stderr, "Queued job", jobScript
    
def removeFiles(files, path):
    for file in files:
        print >> sys.stderr, "Removing output file", file
        os.remove(os.path.join(path, file))

def update(inDir, outDir, workDir, jobLimit):
    """
    Main method
    """
    if numJobs() >= jobLimit:
        return
    
    inFiles = os.listdir(inDir)
    outFiles = os.listdir(outDir)
    
    outFilesByStem = {}
    for outFile in outFiles:
        fileStem = outFile.rsplit("-", 1)
        if not outFilesByStem.has_key(fileStem):
            outFilesByStem[fileStem] = set()
        outFilesByStem[fileStem].add(outFile)
    
    for inFile in inFiles:
        if inFile.find("~"): # temporary backup file
            continue
        elif not outFilesByStem.has_key(inFile): # input file not yet processed
            queue(os.path.join(inDir, inFile))
        elif inFile + "-job" not in outFilesByStem[inFile]: # input file needs to be reprocessed
            removeFiles(outFilesByStem[inFile], outDir)
            queue(os.path.join(inDir, inFile))

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
    
    update(options.input, options.output, options.workdir, 1)