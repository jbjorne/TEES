import sys, os, shutil
import subprocess
import time
from optparse import OptionParser

def runWithTimeout(command, inputFile, timeoutSeconds=60*60):
    s = ""
    s += command + " &\n" # run in background
    s += "PID=$!"
    s += "TIMEOUT=$(" + str(timeoutSeconds) + ")" + "\n"
    
    s += "while true; do " + "\n"
    s += "  if [[ `ps x | grep $PID | grep -v grep` == \"\" ]] ; then\n"
    s += "    kill $PID" + "\n"
    s += "    sleep 5" + "\n"
    s += "    kill -9 $PID" + "\n"
    s += "    echo Process $PID for file " + inputFile + " killed \n"
    s += "    break" + "\n" 
    s += "  fi" + "\n"
    s += "  sleep 10" + "\n"
    s += "done" + "\n\n"
    return s

def getScriptName(scriptDir, nameBase=""):
    if nameBase != "":
        nameBase += "-"
    name = "job-" + nameBase + time.strftime("%Y_%m_%d-%H_%M_%S-")
    jobScriptCount = 0
    while os.path.exists(scriptDir + "/" + name + str(jobScriptCount) + ".sh"):
        jobScriptCount += 1
    name += str(jobScriptCount) + ".sh"
    return name

def makeJobScript(jobName, inputFiles, outDir, workDir, timeOut=False):
    """
    Make a Murska job submission script
    """
    s = "#!/bin/sh \n"
    s += "##execution shell environment \n\n"
    
    s += "##OUTDIR: " + outDir + " \n\n"

    s += "##Memory limit \n"
    s += "#BSUB -M 4200000 \n"
    s += "##Max runtime \n"
    s += "#BSUB -W 10:00 \n"
    s += "#BSUB -J " + jobName[4:14] + "\n"
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    s += "#BSUB -o " + outDir + "/" + jobName + ".stdout \n"
    s += "#BSUB -e " + outDir + "/" + jobName + ".stderr \n"
    s += "#BSUB -n 1 \n\n"
    
    s += "echo $PWD \n"
    s += "mkdir -p " + outDir + "\n" # ensure output directory exists
    s += "#module load python/2.5.1-gcc \n\n"
    
    s += "export PATH=$PATH:/v/users/jakrbj/cvs_checkout \n"
    s += "export PYTHONPATH=$PYTHONPATH:/v/users/jakrbj/cvs_checkout/CommonUtils \n"
    s += "cd /v/users/jakrbj/cvs_checkout/JariSandbox/ComplexPPI/Source/Pipelines \n\n"
    
    for inputFile in inputFiles:
        command = "/v/users/jakrbj/Python-2.5/bin/python MurskaPubMed100p.py -i " + inputFile + " -o " + outDir + " -w " + workDir
        if timeOut:
            s += runWithTimeout(s, command, inputFile)
        else:
            s += command + "\n"
    
    return s

def update(inDir, outDir, workDir, queueDir, submitFilename=None):
    """
    Main method, adds files to job scripts
    """
    if submitFilename != None:
        submitFile = open(submitFilename, "at")
    
    for triple in os.walk(inDir):
        inputFiles = []
        for filename in triple[2]:
            if filename[-7:] == ".xml.gz" or filename[-4:] == ".xml":
                inputFiles.append(os.path.abspath(os.path.join(os.path.join(triple[0], filename))))
        if len(inputFiles) == 0:
            continue
        nameBase = triple[0].replace("/", "_")
        jobName = getScriptName(queueDir, nameBase)
        print "Making job", jobName, "with", len(inputFiles), "input files."
        s = makeJobScript(jobName, inputFiles, os.path.abspath(os.path.join(outDir, triple[0])), os.path.abspath(workDir + "/" + jobName), timeOut=True)
        f = open(os.path.abspath(queueDir + "/" + jobName), "wt")
        f.write(s)
        f.close()
        
        if submitFilename != None:
            submitFile.write("cat " + os.path.abspath(queueDir + "/" + jobName) + " | bsub\n")
    
    if submitFilename != None:
        submitFile.close()

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-w", "--workdir", default="/wrk/jakrbj/shared-task-test", dest="workdir", help="working directory")
    optparser.add_option("-q", "--queue", default="/wrk/jakrbj/jobqueue", dest="queue", help="job queue directory")
    optparser.add_option("-s", "--submitFile", default=None, dest="submitFile", help="A file with bsub commands")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    assert options.output != None
    assert os.path.exists(options.output)
    assert options.queue != None
    assert os.path.exists(options.queue)
    
    update(options.input, options.output, options.workdir, options.queue, options.submitFile)