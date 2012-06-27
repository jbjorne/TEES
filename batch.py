import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils") # new CommonUtils
import subprocess
from subprocess import Popen, PIPE, STDOUT
import time
import re

def getMaxJobsFromFile(controlFilename):
    f = open(controlFilename, "rt")
    lines = f.readlines()
    f.close()
    assert len(lines) == 1
    value = int(lines[0])
    if value == 0:
        print >> sys.stderr, "Exit by control file request"
        sys.exit() 
    return value

def getMaxJobs(maxJobs, controlFilename=None):
    if maxJobs == None:
        if controlFilename != None:
            return getMaxJobsSetting(controlFilename)
        else:
            return 1
    else:
        return maxJobs

def prepareCommand(template, input):
    return template.replace("%i", input)

def submitJob(command, input, inputDir, dummy=False, rerun=False, hideFinished=False):
    if regex.match(input) == None:
        return
    waitForJobs(maxJobs, submitCount, controlFilename=None, sleepTime=15)
    
    print >> sys.stderr, "Processing", input
    jobStatus = connection.getJobStatus(connection._getJobPath(inputDir, input))
    if jobStatus != None:
        print >> sys.stderr, "input already processed, job status =", jobStatus
        if jobStatus == "RUNNING":
            print >> sys.stderr, "Skipping currently running job"
            return False
        elif rerun == False:
            if not hideFinished:
                print >> sys.stderr, "Skipping already processed job"
            return False
    
    if not dummy:
        print >> sys.stderr, "Submitting job"
        job = connection.submit(command, inputDir, input)
        open(input + ".QUEUED", "w").close() # mark job as submitted
    else:
        print >> sys.stderr, "Dummy mode"
    return True

def waitForJobs(maxJobs, submitCount, controlFilename=None, sleepTime=15):
    currentJobs = connection.getNumJobs()
    currentMaxJobs = getMaxJobs(maxJobs, controlFilename)
    while(currentJobs > currentMaxJobs):
        print >> sys.stderr, currentJobs, "jobs in queue/running, sleeping for", sleepTime, "seconds"
        time.sleep(sleepTime)
        currentJobs = connection.getNumJobs()
        currentMaxJobs = getMaxJobs(maxJobs, controlFilename)
        print >> sys.stderr, "Current jobs:", currentJobs, "max jobs", currentMaxJobs, "submitted jobs", submitCount

def batch():
    connection = getConnection(connection)
    submitCount = 0
    if os.path.exists(input) and os.path.isfile(input): # single file
        if submitJob(input, model, dummy, saveWorkDirs, rerun, skipTags=skipTags, hideFinished=hideFinished, eventTag=eventTag, program=program):
            submitCount += 1
    else: # walk directory tree
        firstLoop = True
        while firstLoop or loop:
            for triple in os.walk(input):
                if regexFullPath != None and regex.match(os.path.join(triple[0])) != None:
                    print "Skipping directory", triple[0]
                    continue
                else:
                    print "Processing directory", triple[0]
                for filename in triple[2]:                   
                    if submitJob(source, model, dummy, saveWorkDirs, rerun, skipTags=skipTags, hideFinished=hideFinished, eventTag=eventTag, program=program):
                        submitCount += 1
                firstLoop = False

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input data")
    optparser.add_option("-m", "--model", default=None, dest="model", help="")
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option("--control", default="/v/users/jakrbj/ProcessBatchesControl.txt", dest="control", help="")
    optparser.add_option("-l", "--limit", default=None, dest="limit", help="")
    optparser.add_option("-r", "--regex", default=None, dest="regex", help="")
    optparser.add_option("--regexFullPath", default=None, dest="regexFullPath", help="")
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
    if options.regexFullPath != None: options.regexFullPath = re.compile(options.regexFullPath)
    options.skipTags = options.skipTags.split(",")
    print "Skip tags", options.skipTags
    queue(options.input, options.model, options.control, options.maxJobs, dummy=options.dummy, 
          saveWorkDirs=options.saveWorkDirs, rerun=options.rerun, eventTag=options.eventTag,
          skipTags=options.skipTags, hideFinished=options.hideFinished, limit=options.limit,
          regex = options.regex, regexFullPath=options.regexFullPath, program=options.program, connection=options.connection)


