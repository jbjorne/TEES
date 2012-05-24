import sys, os, codecs, time, signal
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class ProcessWrapper:
    """
    Killing a process spawned by a shell is not really possible (at least in Python).
    This becomes a problem, if a tool requires multiple (e.g. piped) processes to be
    ran. With ProcessWrapper, all processes can be called directly from Python so
    that their ids are known and they can be killed if they hang. A ProcessWrapper can
    be passed as a parameter to ProcessUtils functions in place of a subprocess.Popen
    object. 
    """
    def __init__(self, processes):
        self.processes = processes # subprocesses
    
    def kill(self):
        """
        Kill all subprocesses
        """
        for process in self.processes:
            try:
                process.kill()
            except:
                pass
        for process in self.processes:
            poll = process.poll()
            #print poll
            while poll == None:
                poll = process.poll()
                time.sleep(1)
            #print poll
    
    def poll(self):
        """
        If any subprocess is running, returns None (not finished).
        """
        for process in self.processes:
            if process.poll() == None:
                return None
        return "FINISHED"

def waitForProcess(process, numCorpusSentences, measureByGap, outputFile, counterName, updateMessage, timeout=None):
    """
    Waits for a process to finish, and tracks the number of entities it writes
    to it's outputfile. If writing a sentence takes longer than the timeout, 
    the process is considered stalled and is killed.
    """
    maxStartupTime = 600 # Give extra time for the process to start up (even if it creates immediately an empty output file)
    counter = ProgressCounter(numCorpusSentences, counterName)
    counter.showMilliseconds = True
    prevNumSentences = 0 # Number of output sentences on previous check
    finalCheckLeft = True # Make one final check to update counters
    processStatus = None # When None, process not finished
    prevTime = time.time()
    startTime = time.time()
    # Wait until process is finished and periodically check it's progress.
    while processStatus == None or finalCheckLeft:
        if processStatus != None: # Extra loop to let counters finish
            finalCheckLeft = False # Done only once
        if os.path.exists(outputFile[0]): # Output file has already appeared on disk
            # Measure number of sentences in output file
            numSentences = 0
            f = codecs.open(outputFile[0], "rt", **outputFile[1])
            for line in f:
                if measureByGap:
                    if line.strip() == "":
                        numSentences += 1
                else:
                    numSentences += 1
            f.close()
            # Update status
            if numSentences - prevNumSentences != 0: # Process has progressed
                counter.update(numSentences - prevNumSentences, updateMessage + ": ")
            if finalCheckLeft: # This is a normal loop, not the final check
                # Startuptime hasn't yet passed or process has made progress
                if time.time() - startTime < maxStartupTime or numSentences - prevNumSentences != 0:
                #if prevNumSentences == 0 or numSentences - prevNumSentences != 0:
                    prevTime = time.time() # reset timeout
                else: # Nothing happened on this update, check whether process hung
                    elapsedTime = time.time() - prevTime
                    if timeout != None and elapsedTime > timeout:
                        print >> sys.stderr, "Process timed out (" + str(elapsedTime) + " vs. " + str(timeout) + ")"
                        print >> sys.stderr, "Killing process"
                        process.kill()
                prevNumSentences = numSentences
                time.sleep(1)
        else: # Output file doesn't exist yet
            prevTime = time.time() # reset counter if output file hasn't been created
        processStatus = process.poll() # Get process status, None == still running
    
    counter.markFinished() # If we get this far, don't show the error message even if process didn't finish
    return (numSentences, numCorpusSentences)

def makeSubset(input, workdir, fromLine):
    """
    Make a subset of the input data from "fromLine" to end of input file.
    """
    newInput = os.path.join(workdir, "input-from-" + str(fromLine))
    newInputFile = codecs.open(newInput, "wt", "utf-8")

    inputFile = codecs.open(input, "rt", "utf-8")
    lineCount = -1
    for line in inputFile:
        lineCount += 1
        if lineCount < fromLine:
            continue
        newInputFile.write(line)  
    inputFile.close()
    newInputFile.close()
    return newInput

def mergeOutput(dir, numCorpusSentences, measureByGap, outputArgs={}):
    """
    Merge output files (multiple files may have been created if program failed on a sentence)
    """
    filenames = os.listdir(dir)
    outputs = []
    for filename in filenames:
        if filename.find("output-from") != -1:
            outputs.append( (int(filename.rsplit("-", 1)[-1]), filename) )
    outputs.sort() # Order output sets by their first sentence index
    #print outputs
    
    mergedOutput = codecs.open(os.path.join(dir, "merged-output"), "wt", **outputArgs)
    
    missingSentences = 0
    numSentences = 0
    # Go through output subsets in order
    for i in range(len(outputs)):
        f = codecs.open(os.path.join(dir, outputs[i][1]), "rt", **outputArgs)
        for line in f: # Copy to merged file
            mergedOutput.write(line)
            if measureByGap:
                if line.strip() == "":
                    numSentences += 1
            else:
                numSentences += 1
        f.close()
        # If sentences are missing from output, write empty lines in merged output
        if i < len(outputs) - 1: # not last output
            while numSentences < outputs[i+1][0]: # Start of next subset not reached yet
                mergedOutput.write("\n")
                numSentences += 1
                missingSentences += 1
        else: # last of the output subsets
            while numSentences < numCorpusSentences: # End of whole data not reached yet
                mergedOutput.write("\n")
                numSentences += 1
                missingSentences += 1
    mergedOutput.close()
    return missingSentences

def getSubsetEndPos(subsetFileName, measureByGap):
    """
    Return the sentence count to which this process reached by counting
    the sentences in the output file.
    """
    if subsetFileName.find("-from-") == -1:
        return 0
    numSentences = getLines(subsetFileName, measureByGap)
    subsetPos = int(subsetFileName.rsplit("-", 1)[-1])
    return subsetPos + numSentences

def getLines(filename, measureByGap):
    """
    Number of sentences in the file, measured either in lines, or by empty "gap" lines
    """
    numSentences = 0
    f = codecs.open(filename, "rt", "utf-8")
    for line in f:
        if measureByGap:
            if line.strip() == "":
                numSentences += 1
        else:
            numSentences += 1
    f.close()
    return numSentences

def runSentenceProcess(launchProcess, programDir, input, workdir, measureByGap, counterName, updateMessage, timeout=None, processArgs={}, outputArgs={}):
    """
    Runs a process on input sentences, and in case of problems skips one sentence and 
    reruns the process on the remaining ones.
    """
    # Count input sentences
    input = os.path.abspath(input)
    origInput = input
    numCorpusSentences = 0
    inputFile = codecs.open(input, "rt", "utf-8")
    for line in inputFile:
        numCorpusSentences += 1
    inputFile.close()
    
    if "encoding" not in outputArgs:
        outputArgs["encoding"] = "utf-8"
    
    cwd = os.getcwd()
    os.chdir(programDir)
    finished = False
    startLine = 0
    while not finished:
        # Count lines in input file (input data must be in a one sentence per line -format)
        inputLines = 0
        inputFile = codecs.open(input, "rt", "utf-8")
        for line in inputFile:
            inputLines += 1
        inputFile.close()

        output = os.path.join(workdir, "output-from-" + str(startLine))
        process = launchProcess(input, output, **processArgs)
        result = waitForProcess(process, inputLines, measureByGap, (output, outputArgs), counterName, updateMessage, timeout)
        if result[0] != result[1]:
            gap = 1
            startLine = getSubsetEndPos(output, measureByGap) + gap 
            if startLine >= numCorpusSentences:
                finished = True
            else:
                print >> sys.stderr, "Process failed for sentence " + str(startLine-gap) + ", rerunning from sentence", startLine
                input = makeSubset(origInput, workdir, startLine)
        else:
            finished = True
    os.chdir(cwd)
    
    numMissedSentences = mergeOutput(workdir, numCorpusSentences, measureByGap, outputArgs=outputArgs)
    if numMissedSentences == 0:
        print >> sys.stderr, "Processed succesfully all sentences"
    else:
        print >> sys.stderr, "Warning, processing failed for", numMissedSentences, "out of", numCorpusSentences, "sentences"
    return os.path.abspath(os.path.join(workdir, "merged-output"))

def getElementIndex(parent, element):
    index = 0
    for e in parent:
        if e == element:
            return index
        index += 1
    return -1

def getPrevElementIndex(parent, eTag):
    index = 0
    elemIndex = -1
    for element in parent:
        if element.tag == eTag:
            elemIndex = index
        index += 1
    return elemIndex

def getElementByAttrib(parent, tag, attDict):
    for element in parent.getiterator():
        if element.tag == tag:
            found = True
            for k, v in attDict.iteritems():
                if element.get(k) != v:
                    found = False
            if found:
                return element
    return None

def setDefaultElement(parent, name):
    element = parent.find(name)
    if element == None:
        element = ET.Element(name)
        parent.append(element)
    return element