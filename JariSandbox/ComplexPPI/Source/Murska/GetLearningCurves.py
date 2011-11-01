import sys, os, shutil
import subprocess
import time
from optparse import OptionParser
from collections import defaultdict

def getSample(lines):
    docs = None
    sentences = None
    for line in lines:
        if "Subset doc:" in line:
            values = line.strip().split()
            docs = int(values[3]) - int(values[5])
            sentences = int(values[7]) - int(values[9])
            break
    if docs == None:
        for i in range(len(lines)):
            if "Loading corpus file" in lines[i] and "train-nodup" in lines[i]:
                values = lines[i+1].strip().split()
                docs = int(values[1])
                sentences = int(values[3])
                break
    return (docs, sentences)

def getResults(task, seed, point, inDir, results):
    logFile = open(os.path.join(inDir, "log.txt"), "rt")
    lines = logFile.readlines()
    logFile.close()
    resultLine = None
    markerLine = None
    if task in ["GE", "GE.1", "GE.2"]:
        resultTag = "ALL-TOTAL"
        markerTag = "======== Evaluating empty devel set (task 3) ========"
    elif task in ["OLD", "OLD.1", "OLD.2"]:
        resultTag = "==[ALL-TOTAL]==       1789"
        markerTag = "======== Evaluating empty devel set (task 3) ========"
    elif task in ["EPI", "ID"]:
        resultTag = "TOTAL"
        markerTag = "======== Evaluating empty devel set (task 3) ========"
    elif task == "BI":
        resultTag = "Global scores:"
        markerTag = "------------ Empty devel classification ------------"
    elif task == "BB":
        resultTag = "F-score ="
        markerTag = "======== Evaluating empty devel set ========"
    elif task == "REL":
        resultTag = "micro"
        markerTag = "======== Evaluating empty devel set ========"
    elif task == "REN":
        resultTag = "Relaxed F-score"
        markerTag = "Writing output to empty-devel-geniaformat"
    for line in reversed(lines):
        if resultLine == None and resultTag in line:
            resultLine = line
        if markerLine == None and markerTag in line:
            markerLine = line
            assert resultLine != None
            break
    if markerLine != None:
        if resultTag == "micro":
            result = resultLine.strip().split("/")[-1]
        else:
            result = resultLine.strip().split()[-1]
    else:
        result = None
    if task in ["BI", "BB", "REL", "REN"]:
        if result != "NaN" and result != None:
            result = str(100.0 * float(result))
        else:
            result = 0.0
    results[task][point][seed] = (result, getSample(lines))

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-t", "--tasks", default="GE", dest="tasks", help="")
    optparser.add_option("-i", "--input", default="/wrk/jakrbj/BioNLP11Tests/curves", dest="input", help="output directory")
    optparser.add_option("-s", "--seeds", default="1", dest="seeds", help="")
    optparser.add_option("-p", "--points", default="0.02,0.04,0.08,0.16,0.32,0.64,1.00", dest="points", help="")
    #optparser.add_option("-d", "--dummy", default=False, action="store_true", dest="dummy", help="")
    (options, args) = optparser.parse_args()
    
    options.tasks = options.tasks.split(",")
    options.seeds = options.seeds.split(",")
    options.points = options.points.split(",")
    results = defaultdict(lambda : defaultdict(lambda : defaultdict(int)))
    for task in options.tasks:
        for point in options.points:
            for seed in options.seeds:
                inDir = options.input + "/seed" + seed + "/" + task + "-" + point
                getResults(task, seed, point, inDir, results)
    print "results = defaultdict(lambda : defaultdict(lambda : defaultdict(int)))"
    for task in options.tasks:
        for point in options.points:
            for seed in options.seeds:
                r = results[task][point][seed]
                print "results[\"" + task + "\"][" + point + "][" + seed + "] = (" + str(r[0]) + ", " + str(r[1][0]) + ", " + str(r[1][1]) + ")"
            #print point, sorted(results[task][point].values())
