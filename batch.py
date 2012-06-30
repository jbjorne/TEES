import sys, os
import time
import re
from Utils.Connection.Unix import getConnection

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
            return None
    else:
        return maxJobs

def prepareCommand(template, input, jobTag=None):
    template = template.replace("%i", input)
    template = template.replace("%a", os.path.abspath(input))
    template = template.replace("%b", os.path.basename(input))
    if jobTag == None:
        jobTag = ""
    template = template.replace("%j", jobTag)
    return template

def submitJob(command, input, connection, jobTag=None, regex=None, dummy=False, rerun=False, hideFinished=False):
    if input.endswith(".job"):
        if connection.debug:
            print >> sys.stderr, "Skipped job control file", input
        return
    if connection.debug:
        print >> sys.stderr, "Preparing to submit a job for input", input
    if regex != None and regex.match(input) == None:
        if connection.debug:
            print >> sys.stderr, "Regular expression did not match input, no job submitted"
        return
    elif connection.debug:
        print >> sys.stderr, "Regular expression matched the input"
    
    jobDir = os.path.abspath(os.path.dirname(input))
    jobName = os.path.basename(input)
    if jobName == "": # input is a directory
        jobName = jobDir.rstrip("/").split("/")[-1] # use directory name as job name
        jobDir = jobDir.rstrip("/").split("/")[0] # save job control file on the same level as the directory
    if jobTag != None:
        jobName += "-" + jobTag
    
    print >> sys.stderr, "Processing", input
    jobStatus = connection.getJobStatusByName(jobDir, jobName)
    if jobStatus != None:
        print >> sys.stderr, "input already processed, job status =", jobStatus
        if jobStatus == "RUNNING":
            print >> sys.stderr, "Skipping currently running job"
            return False
        elif rerun == False:
            if not hideFinished:
                print >> sys.stderr, "Skipping already processed job"
            return False
    
    command = prepareCommand(command, input, jobTag)
    
    if not dummy:
        connection.submit(command, jobDir, jobName)
    else:
        print >> sys.stderr, "Dummy mode"
        if connection.debug:
            print >> sys.stderr, "------- Job command -------"
            print >> sys.stderr, command
            print >> sys.stderr, "--------------------------"
    return True

def waitForJobs(maxJobs, submitCount, connection, controlFilename=None, sleepTime=15):
    currentJobs = connection.getNumJobs()
    currentMaxJobs = getMaxJobs(maxJobs, controlFilename)
    print >> sys.stderr, "Current jobs", str(currentJobs) + ", max jobs", str(currentMaxJobs) + ", submitted jobs", submitCount
    if currentMaxJobs != None:
        while(currentJobs > currentMaxJobs):
            time.sleep(sleepTime)
            currentJobs = connection.getNumJobs()
            currentMaxJobs = getMaxJobs(maxJobs, controlFilename)
            print >> sys.stderr, "Current jobs", str(currentJobs) + ", max jobs", str(currentMaxJobs) + ", submitted jobs", submitCount

def batch(command, input, connection=None, jobTag=None, regex=None, regexSkipDir=None, dummy=False, rerun=False, 
          hideFinished=False, controlFilename=None, sleepTime=15, debug=False, limit=None, loop=False):
    connection = getConnection(connection)
    connection.debug = debug
    if os.path.exists(input) and os.path.isfile(input): # single file
        waitForJobs(limit, 0, connection, controlFilename, sleepTime)
        submitJob(command, input, connection, jobTag, regex, dummy, rerun, hideFinished)
    else: # walk directory tree
        firstLoop = True
        submitCount = 0
        while firstLoop or loop:
            waitForJobs(limit, submitCount, connection, controlFilename, sleepTime)
            for triple in os.walk(input):
                if regexSkipDir != None and regexSkipDir.match(os.path.join(triple[0])) != None:
                    print >> sys.stderr, "Skipping directory", triple[0]
                    continue
                else:
                    print >> sys.stderr, "Processing directory", triple[0]
                for item in sorted(triple[1]) + sorted(triple[2]): # process both directories and files
                    #print item, triple, os.path.join(triple[0], item)
                    if submitJob(command, os.path.join(triple[0], item), connection, jobTag, regex, dummy, rerun, hideFinished):
                        submitCount += 1
                        # number of submitted jobs has increased, so check if we need to wait
                        waitForJobs(limit, submitCount, connection, controlFilename, sleepTime)
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
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input file or directory. A directory will be processed recursively")
    optparser.add_option("-c", "--command", default=None, dest="command", help="")
    optparser.add_option("-n", "--connection", default=None, dest="connection", help="")
    optparser.add_option("-r", "--regex", default=None, dest="regex", help="")
    optparser.add_option("-d", "--regexSkipDir", default=None, dest="regexSkipDir", help="")
    optparser.add_option("-j", "--jobTag", default=None, dest="jobTag", help="")
    optparser.add_option("-l", "--limit", default=None, dest="limit", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Print jobs on screen")
    optparser.add_option("--controlFile", default=None, dest="controlFile", help="")
    optparser.add_option("--sleepTime", default=None, dest="sleepTime", help="")
    optparser.add_option("--dummy", default=False, action="store_true", dest="dummy", help="Don't submit jobs")
    optparser.add_option("--rerun", default=False, action="store_true", dest="rerun", help="Rerun jobs which have already been queued")
    optparser.add_option("--maxJobs", default=None, type="int", dest="maxJobs", help="Maximum number of jobs in queue/running")
    optparser.add_option("--hideFinished", default=False, action="store_true", dest="hideFinished", help="")
    optparser.add_option("--loop", default=False, action="store_true", dest="loop", help="Continuously loop through the input directory")
    (options, args) = optparser.parse_args()
    
    if options.limit != None: options.limit = int(options.limit)
    if options.sleepTime != None: options.sleepTime = int(options.sleepTime)
    if options.regex != None: options.regex = re.compile(options.regex)
    if options.regexSkipDir != None: options.regexSkipDir = re.compile(options.regexSkipDir)
    batch(command=options.command, input=options.input, connection=options.connection, jobTag=options.jobTag, 
          regex=options.regex, regexSkipDir=options.regexSkipDir, dummy=options.dummy, rerun=options.rerun, 
          hideFinished=options.hideFinished, controlFilename=options.controlFile, sleepTime=options.sleepTime, 
          debug=options.debug, limit=options.limit, loop=options.loop)