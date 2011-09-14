import sys, os, shutil, atexit
import subprocess
import time
from optparse import OptionParser

def runWithTimeout(command, inputFile, timeoutSeconds=60*60):
    s = ""
    s += command + " &\n" # run in background
    s += "PID=$!" + "\n"
    s += "TIMEOUT=" + str(timeoutSeconds) + "\n"
    s += "SLEEPTIME=0" + "\n"
    s += "while true; do" + "\n"
    s += "  if [[ `ps x | grep $PID | grep -v grep` == \"\" ]] ; then" + "\n"
    s += "    echo \"Process\" $PID \"for file " + inputFile + " finished ok\"" + "\n" 
    s += "    break" + "\n"
    s += "  fi" + "\n"
    s += "  sleep 10" + "\n"
    s += "  let SLEEPTIME=SLEEPTIME+10" + "\n"
    s += "  if [ \"$SLEEPTIME\" -gt \"$TIMEOUT\" ]; then" + "\n"
    s += "    kill $PID" + "\n"
    s += "    sleep 5" + "\n"
    s += "    kill -9 $PID" + "\n"
    s += "    echo \"Process\" $PID \"for file " + inputFile + " killed\"" + "\n" 
    s += "    break" + "\n"
    s += "  fi" + "\n"
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

def makeJobScript(jobName, inputFiles, outDir, workDir, timeOut=False, s=""):
    """
    Make a Murska job submission script
    """
    s += "#!/bin/sh \n"
    if os.environ.has_key("METAWRK"): # CSC
        s += "##execution shell environment \n\n"
        
        s += "##OUTDIR: " + outDir + " \n\n"
    
        s += "##Memory limit \n"
        s += "#BSUB -M 4200000 \n"
        s += "##Max runtime \n"
        #timeMin = 20 * len(inputFiles)
        #timeHours = timeMin / 60
        #timeMin = timeMin % 60
        #s += "#BSUB -W 10:00 \n"
        s += "#BSUB -W 48:00 \n"
        #s += "#BSUB -W " + str(timeHours) + ":" + str(timeMin) + " \n"
        s += "#BSUB -J " + jobName[4:14] + "\n"
        s += "#BSUB -o " + outDir + "/" + jobName + ".stdout \n"
        s += "#BSUB -e " + outDir + "/" + jobName + ".stderr \n"
        s += "#BSUB -n 1 \n\n"
    
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    s += "echo $PWD \n"
    s += "mkdir -p " + outDir + "\n" # ensure output directory exists
    
    if os.environ.has_key("METAWRK"): # CSC
        s += "#module load python/2.5.1-gcc \n\n"
        s += "export PATH=$PATH:/v/users/jakrbj/cvs_checkout \n"
        s += "export PYTHONPATH=$PYTHONPATH:/v/users/jakrbj/cvs_checkout/CommonUtils \n"
        s += "cd /v/users/jakrbj/cvs_checkout/JariSandbox/ComplexPPI/Source/Pipelines \n\n"
    else:
        s += "cd /home/jari/cvs_checkout/JariSandbox/ComplexPPI/Source/Pipelines \n\n"
    
    for inputFile in inputFiles:
        if os.environ.has_key("METAWRK"): # CSC
            command = "/v/users/jakrbj/Python-2.5/bin/python MurskaPubMed100pTask3.py -i " + inputFile + " -o " + outDir + " -w " + workDir
        else:
            command = "python MurskaPubMed100p.py -i " + inputFile + " -o " + outDir + " -w " + workDir
        if timeOut:
            s += runWithTimeout(command, inputFile)
        else:
            s += command + "\n"
    
    return s

def update(inDir, outDir, workDir, queueDir, submitFilename=None, listFile=False, oneJob=False):
    """
    Main method, adds files to job scripts
    """
    origDir = os.getcwd()
    os.chdir(inDir)
    atexit.register(os.chdir, origDir)

    remainingInputs = 1
    prevRemainingInputs = 0
    round = 1
    while remainingInputs > 0:
        remainingInputs = prepareJobs(inDir, outDir, workDir, queueDir, submitFilename+"-round"+str(round))
        print "Input files to be processed", remainingInputs
        if remainingInputs > 0:
            submitJobs(submitFilename+"-round"+str(round))
        if prevRemainingInputs == remainingInputs:
            print "Exiting, remaining jobs", remainingInputs
        prevRemainingInputs = remainingInputs
        round += 1

def prepareJobs(inDir, outDir, workDir, queueDir, submitFilename=None, listFile=False, oneJob=False):
    print "Preparing jobs"
    if submitFilename != None:
        submitFile = open(submitFilename, "at")
    
    if listFile:
        sourceList = []
        maxJobs = 40
        listFile = open(options.input, "rt")
        d = {}        
        for filename in listFile.readlines():
            filename = filename.strip()
            dirname = os.path.dirname(filename) 
            basename = os.path.basename(filename)
            if not d.has_key(dirname):
                d[dirname] = []
            d[dirname].append(basename)
        for k in sorted(d.keys()):
            sourceList.append([k, None, d[k]])
    else:
        sourceList = os.walk(inDir)
    
    remainingInputs = 0
    s = ""
    for triple in sourceList:
        inputFiles = []
        for filename in triple[2]:
            if filename.find == "events_unflattened.xml.gz" or filename[-4:] == ".xml":
                skip = False
                if filename[-7:] == ".xml.gz":
                    if not os.path.exists(os.path.join(triple[0], filename[:-7], "-finished")):
                        skip = True
                elif filename[-4:] == ".xml":
                    if not os.path.exists(os.path.join(triple[0], filename[:-4], "-finished")):
                        skip = True
                if skip:
                    continue
                inputFiles.append(os.path.abspath(os.path.join(os.path.join(triple[0], filename))))
                remainingInputs += 1
        if len(inputFiles) == 0:
            continue
        nameBase = triple[0].replace("/", "_")
        jobName = getScriptName(queueDir, nameBase)
        if not oneJob:
            print "Making job", jobName, "with", len(inputFiles), "input files."
            s = makeJobScript(jobName, inputFiles, os.path.abspath(os.path.join(outDir, triple[0])), os.path.abspath(workDir + "/" + jobName), timeOut=False)
            f = open(os.path.abspath(queueDir + "/" + jobName), "wt")
            f.write(s)
            f.close()
        else:
            s = makeJobScript(jobName, inputFiles, os.path.abspath(os.path.join(outDir, triple[0])), os.path.abspath(workDir + "/" + jobName), timeOut=False, s=s)
        
        if submitFilename != None:
            submitFile.write("cat " + os.path.abspath(queueDir + "/" + jobName) + " | bsub\n")
    
    if oneJob:
        f = open(os.path.abspath(queueDir + "/" + jobName), "wt")
        f.write(s)
        f.close()
    
    if submitFilename != None:
        submitFile.close()
    
    return remainingInputs

def submitJobs(jobFilename):
    print "Submitting jobs"
    jobs = readJobs([jobFilename])
    while True:        
        x=currentJobs()
        
        if os.path.exists("autosubmit.lim"):
            f=open("autosubmit.lim","rt")
            CCJOBS=int(f.readlines()[0])
            f.close()
        else:
            CCJOBS=80
        
        if x>=CCJOBS:
            os.system("sleep 60")
            continue
        while x<CCJOBS and jobs:
            job=jobs.pop(0).strip()
            os.system("echo `date` "+job.replace("|","PIPE").replace(">","FWD")+"  >> autosubmit.log")
            os.system(job)
            x+=1
        if not jobs:
            os.system("echo `date` done >> autosubmit.log")
            break

def currentJobs():
    os.system("bjobs | wc -l > currentQ")
    f=open("currentQ","rt")
    jobs=int(f.readlines()[0])
    f.close()
    return jobs

def readJobs(jobFilenames):
    jobs=[]
    for fName in jobFilenames:
        f=open(fName,"rt")
        for line in f:
            line=line.strip()
            if not line or line[0]=="#":
                continue
            jobs.append(line)
        f.close()
    return jobs
    
if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default="/wrk/jakrbj/PubMedEvents/100p", dest="input", help="input directory")
    optparser.add_option("-f", "--files", default=False, action="store_true", dest="files", help="-i switch defines a file with a list of individual files to process")
    optparser.add_option("-o", "--output", default="/wrk/jakrbj/PubMedEvents/100p", dest="output", help="output directory")
    optparser.add_option("-w", "--workdir", default="/wrk/jakrbj/shared-task-test", dest="workdir", help="working directory")
    optparser.add_option("-q", "--queue", default="/wrk/jakrbj/PubMedTask3Rerun", dest="queue", help="job queue directory")
    optparser.add_option("-s", "--submitFile", default=None, dest="submitFile", help="A file with bsub commands")
    optparser.add_option("-j", "--oneJob", default=False, action="store_true", dest="oneJob", help="Make one job script")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    assert options.output != None
    assert os.path.exists(options.output)
    assert options.queue != None
    assert os.path.exists(options.queue)
    
    if options.submitFile == None:
       options.submitFile = options.queue + "/submitfile"
    update(options.input, options.output, options.workdir, options.queue, options.submitFile, options.files, oneJob=options.oneJob)
