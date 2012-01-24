import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils") # new CommonUtils
import JariSandbox.ComplexPPI.Source.Murska.MakeJobScript as MakeJobScript
import subprocess
from subprocess import Popen, PIPE, STDOUT
import time
import re

def numJobs(username="jakrbj"):
    """
    Get number of queued (pending or running) jobs
    """
    if MakeJobScript.isVuori():
        p = subprocess.Popen("squeue | grep " + username + " | wc -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen("bjobs | grep " + username + " | wc -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = p.stdout.readlines()
    assert len(lines) == 1
    return int(lines[0])

def getMaxJobsSetting(controlFilename):
    f = open(controlFilename, "rt")
    lines = f.readlines()
    f.close()
    assert len(lines) == 1
    value = int(lines[0])
    if value == 0:
        print >> sys.stderr, "Exit by control file request"
        sys.exit() 
    return value

def getSources(triple, regex=None):
    sources = []
    for filename in sorted(triple[2]):
        if "files_" not in triple[0]:
            continue
        if filename.endswith(".txt"): # process directories with txt-files
            if regex == None or regex.match(triple[0]) != None:
                sources.append(triple[0])
        if regex == None:
            if filename.endswith(".tar.gz") and not "events" in filename: # process compressed st-format directories
                sources.append(os.path.join(triple[0], filename))
        elif regex.match(filename) != None:
            sources.append(os.path.join(triple[0], filename))
    if triple[0] in sources:
        assert len(sources) == 0, sources
    return sources

def getSkip(input, tags):
    missing = []
    for tag in tags:
        if not os.path.exists(input + tag):
            missing.append(tag)
    if len(missing) > 0:
        print >> sys.stderr, "Tags", missing, "missing for input", input
        return True
    else:
        return False

def getJobs(username="jakrbj"):
    jobNames = []
    queueCommand = "squeue -o \"%.7i %.64j %.8u %.8T %.9M %.6D %R\" | grep " + username
    p = subprocess.Popen(queueCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = p.stdout.readlines()
    for line in lines:
        jobNames.append(line.strip().split()[1])
    return jobNames

def submitJob(input, model, dummy=False, saveWorkDirs=False, rerun=False, skipTags=[".QUEUED"], hideFinished=False, eventTag=None, program=None):
    # Check for output files
    if not (rerun or getSkip(input, skipTags)): # this input has already been submitted
        if not hideFinished:
            print >> sys.stderr, "Processing", input
            print >> sys.stderr, "input already processed"
        return False
    print >> sys.stderr, "Processing", input
    # Check if the job is still running
    queuedAndRunningJobNames = getJobs()
    stemDir, finalDir = os.path.normpath(input).rsplit("/", 1)
    if finalDir in queuedAndRunningJobNames:
        print >> sys.stderr, "Job", finalDir, "is currently queued/running"
        return False
    # We can queue the job
    if program != None:
        args = ["python", program, "-i", input]
    else:
        args = ["python", "PredictTask.py", "-i", input]
        if model != None:
            args += ["-m", model]
        if saveWorkDirs:
            args += ["-w", input + ".workdir"]
        if eventTag != None:
            args += ["--eventTag", eventTag]
    script = MakeJobScript.makeJob(finalDir, "48:00", stemDir, args) # make job script
    if not dummy:
        print >> sys.stderr, "Submitting job"
        if MakeJobScript.isVuori():
            #f = open(input + ".jobscript", "wt")
            #f.write(script)
            #f.close
            #subprocess.call("sbatch", shell=True, stdin=script) # submit job
            p = Popen(['sbatch'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            pstdout = p.communicate(input=script)[0]
            print(pstdout)
        else: # assume Murska
            subprocess.call(script + " | bsub", shell=True) # submit job
        open(input + ".QUEUED", "w").close() # mark job as submitted
    else:
        print >> sys.stderr, "Dummy mode"
        #print >> sys.stderr, "Script", finalDir
        #print >> sys.stderr, script
    return True

def queue(input, model, controlFilename=None, maxJobs=10, sleepTime=10, loop=False, dummy=False, 
          saveWorkDirs=False, rerun=False, skipTags=[".QUEUED"], hideFinished=False, limit=None,
          eventTag=None, regex=None, program=None):
    firstLoop = True
    submitCount = 0
    if os.path.exists(input) and os.path.isfile(input): # single file
        if submitJob(input, model, dummy, saveWorkDirs, rerun, skipTags=skipTags, hideFinished=hideFinished, eventTag=eventTag, program=program):
            submitCount += 1
    else: # walk directory tree
        while firstLoop or loop:
            for triple in os.walk(input):
                print "Processing directory", triple[0]
                for source in getSources(triple, regex):
                    currentJobs = numJobs()
                    if maxJobs == None and controlFilename != None:
                        currentMaxJobs = getMaxJobsSetting(controlFilename)
                    else:
                        currentMaxJobs = maxJobs
                    while(currentJobs > currentMaxJobs):
                        print >> sys.stderr, currentJobs, "jobs in queue/running, sleeping for", sleepTime, "seconds"
                        time.sleep(sleepTime)
                        currentJobs = numJobs()
                        if maxJobs == None and controlFilename != None:
                            currentMaxJobs = getMaxJobsSetting(controlFilename)
                        else:
                            currentMaxJobs = maxJobs
                        print >> sys.stderr, "Current jobs:", currentJobs, "max jobs", currentMaxJobs
                    if submitJob(source, model, dummy, saveWorkDirs, rerun, skipTags=skipTags, hideFinished=hideFinished, eventTag=eventTag, program=program):
                        submitCount += 1
                        print >> sys.stderr, "Current jobs:", currentJobs, "max jobs", currentMaxJobs, "submitted jobs", submitCount
                firstLoop = False

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-i", "--input", default=None, dest="input", help="input data")
optparser.add_option("-m", "--model", default=None, dest="model", help="")
optparser.add_option("-c", "--control", default="/v/users/jakrbj/ProcessBatchesControl.txt", dest="control", help="")
optparser.add_option("-l", "--limit", default=None, dest="limit", help="")
optparser.add_option("-r", "--regex", default=None, dest="regex", help="")
optparser.add_option("--eventTag", default=None, dest="eventTag", help="")
optparser.add_option("--program", default=None, dest="program", help="")
optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
optparser.add_option("--dummy", default=False, action="store_true", dest="dummy", help="Print jobs on screen, don't submit them")
optparser.add_option("--saveWorkDirs", default=False, action="store_true", dest="saveWorkDirs", help="Create working directories at input file location")
optparser.add_option("--rerun", default=False, action="store_true", dest="rerun", help="Rerun jobs which have already been queued")
optparser.add_option("--maxJobs", default=None, type="int", dest="maxJobs", help="Maximum number of jobs in queue/running")
optparser.add_option("--skipTags", default=".QUEUED", dest="skipTags", help="")
optparser.add_option("--hideFinished", default=False, action="store_true", dest="hideFinished", help="")
(options, args) = optparser.parse_args()

if options.limit != None: options.limit = int(options.limit)
if options.regex != None: options.regex = re.compile(options.regex)
options.skipTags = options.skipTags.split(",")
print "Skip tags", options.skipTags
queue(options.input, options.model, options.control, options.maxJobs, dummy=options.dummy, 
      saveWorkDirs=options.saveWorkDirs, rerun=options.rerun, eventTag=options.eventTag,
      skipTags=options.skipTags, hideFinished=options.hideFinished, limit=options.limit,
      regex = options.regex, program=options.program)


