import sys, os, codecs, time, signal
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter

class ProcessWrapper:
    def __init__(self, processes):
        self.processes = processes
    
    def kill(self):
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
        for process in self.processes:
            if process.poll() == None:
                return None
        return "FINISHED"

def waitForProcess(process, numCorpusSentences, measureByGap, outputFile, counterName, updateMessage, timeout=None):
    maxStartupTime = 600
    counter = ProgressCounter(numCorpusSentences, counterName)
    prevNumSentences = 0
    finalCheckLeft = True # Make one final check to update counters
    processStatus = None # When None, process not finished
    prevTime = time.time()
    startTime = time.time()
    while processStatus == None or finalCheckLeft:
        if processStatus != None: # Extra loop to let counters finish
            finalCheckLeft = False
        if os.path.exists(outputFile):
            numSentences = 0
            f = codecs.open(outputFile, "rt", "utf-8")
            for line in f:
                if measureByGap:
                    if line.strip() == "":
                        numSentences += 1
                else:
                    numSentences += 1
            f.close()
            if numSentences - prevNumSentences != 0:
                counter.update(numSentences - prevNumSentences, updateMessage + ": ")
            if finalCheckLeft:
                if time.time() - startTime < maxStartupTime or numSentences - prevNumSentences != 0:
                #if prevNumSentences == 0 or numSentences - prevNumSentences != 0:
                    prevTime = time.time()
                else:
                    elapsedTime = time.time() - prevTime
                    if timeout != None and elapsedTime > timeout:
                        print >> sys.stderr, "Process timed out (" + str(elapsedTime) + " vs. " + str(timeout) + ")"
                        print >> sys.stderr, "Killing process"
                        process.kill()
                prevNumSentences = numSentences
                time.sleep(1)
        else:
            prevTime = time.time() # reset counter if output file hasn't been created
        processStatus = process.poll()
    
    counter.markFinished() # If we get this far, don't show the error message
    return (numSentences, numCorpusSentences)

def makeSubset(input, workdir, fromLine):
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

def mergeOutput(dir, numCorpusSentences, measureByGap):
    filenames = os.listdir(dir)
    outputs = []
    for filename in filenames:
        if filename.find("output-from") != -1:
            outputs.append( (int(filename.rsplit("-", 1)[-1]), filename) )
    outputs.sort()
    print outputs
    
    mergedOutput = codecs.open(os.path.join(dir, "merged-output"), "wt", "utf-8")
    
    missingSentences = 0
    numSentences = 0
    for i in range(len(outputs)):
        f = codecs.open(os.path.join(dir, outputs[i][1]), "rt", "utf-8")
        for line in f:
            mergedOutput.write(line)
            if measureByGap:
                if line.strip() == "":
                    numSentences += 1
            else:
                numSentences += 1
        f.close()
        if i < len(outputs) - 1: # not last output
            while numSentences < outputs[i+1][0]:
                mergedOutput.write("\n")
                numSentences += 1
                missingSentences += 1
        else:
            while numSentences < numCorpusSentences:
                mergedOutput.write("\n")
                numSentences += 1
                missingSentences += 1
    mergedOutput.close()
    return missingSentences

def getSubsetEndPos(subsetFileName, measureByGap):
    if subsetFileName.find("-from-") == -1:
        return 0
    numSentences = getLines(subsetFileName, measureByGap)
    subsetPos = int(subsetFileName.rsplit("-", 1)[-1])
    return subsetPos + numSentences

def getLines(filename, measureByGap):
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

def runSentenceProcess(launchProcess, programDir, input, workdir, measureByGap, counterName, updateMessage, timeout=None):
    # Count input sentences
    input = os.path.abspath(input)
    origInput = input
    numCorpusSentences = 0
    inputFile = codecs.open(input, "rt", "utf-8")
    for line in inputFile:
        numCorpusSentences += 1
    inputFile.close()
    
    cwd = os.getcwd()
    os.chdir(programDir)
    finished = False
    startLine = 0
    while not finished:
        inputLines = 0
        inputFile = codecs.open(input, "rt", "utf-8")
        for line in inputFile:
            inputLines += 1
        inputFile.close()

        output = os.path.join(workdir, "output-from-" + str(startLine))
        process = launchProcess(input, output)
        result = waitForProcess(process, inputLines, measureByGap, output, counterName, updateMessage, timeout)
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
    
    numMissedSentences = mergeOutput(workdir, numCorpusSentences, measureByGap)
    if numMissedSentences == 0:
        print >> sys.stderr, "Processed succesfully all sentences"
    else:
        print >> sys.stderr, "Warning, processing failed for", numMissedSentences, "out of", numCorpusSentences, "sentences"
    return os.path.abspath(os.path.join(workdir, "merged-output"))

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