import sys, os, codecs, time
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter

def waitForProcess(process, numCorpusSentences, measureByGap, outputFile, counterName, updateMessage):
    counter = ProgressCounter(numCorpusSentences, counterName)
    prevNumSentences = 0
    finalCheck = True # Make one final check to update counters
    processStatus = None # When None, process not finished
    while processStatus == None or finalCheck == True:
        if processStatus != None: # Extra loop to let counters finish
            finalCheck = False
        if os.path.exists(outputFile):
            numSentences = 0
            for line in codecs.open(outputFile, "rt", "utf-8"):
                if measureByGap:
                    if line.strip() == "":
                        numSentences += 1
                else:
                    numSentences += 1
            if numSentences - prevNumSentences != 0:
                counter.update(numSentences - prevNumSentences, updateMessage + ": ")
            prevNumSentences = numSentences
            time.sleep(1)
        processStatus = process.poll()
