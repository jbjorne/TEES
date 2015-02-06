import sys, os
import requests #pip install requests if you don't have it already
import STFormat.STTools as STTools
import tempfile
import copy

# Online evaluation status

# GE11
# EPI11
# ID11
# BB11
# BI11
# CO11

URL = {}
URL["devel"] = {
"GE11":"http://bionlp-st.dbcls.jp/GE/2011/eval-development/eval.cgi",
"EPI11":'http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/EPI/eval/devel-submit.cgi',
"ID11":'http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/ID/eval/devel-submit.cgi',
# BB11 not available
# BI11 not available
"CO11":"http://bionlp-st.dbcls.jp/CO/eval-development/eval.cgi",
"REL11":"http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/REL/eval/devel-submit.cgi",
# REN11 not available
}
URL["test"] = {
"EPI11":'http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/EPI/test-eval/submit.cgi',
}

DEFAULT_DATA_DEVEL = {"email":"%email"}
DATA = {}
DATA["devel"] = {
"GE11":DEFAULT_DATA_DEVEL,
"EPI11":DEFAULT_DATA_DEVEL,
"ID11":DEFAULT_DATA_DEVEL,
"CO11":DEFAULT_DATA_DEVEL,
"REL11":DEFAULT_DATA_DEVEL
}
DATA["test"] = {
"EPI11":{"email":"%email", "password":"calmodulin"},
}

def getResultLine(logPath, tagPaths):
    f = open(logPath, "rt")
    lines = f.readlines()
    f.close()
    
    for tagPath in tagPaths:
        currentTagIndex = 0
        for line in lines:
            if tagPath[currentTagIndex] in line:
                if currentTagIndex < len(tagPath) - 1:
                    currentTagIndex += 1
                else:
                    return line.split("\t", 1)[-1].strip()
    return "No result"

def removeX(filename, resultFileTag="a2"):
    documents = STTools.loadSet(filename)
    newFilename = os.path.join(tempfile.tempdir, filename.rsplit(".", 2)[0] + "-no-X.tar.gz")
    STTools.writeSet(documents, newFilename, resultFileTag=resultFileTag, writeExtra=False, files=["a2","rel"])
    return newFilename

def submit(task, dataset, filename, email):
    global URL, DATA
    if task not in URL[dataset]:
        print "Upload settings not defined for task", task
        return None
    url = URL[dataset][task]
    print url
    #filename = removeX(filename)
    
    files = {'file':open(filename)}
    data = copy.copy(DATA[dataset][task])
    for key in data:
        value = data[key]
        if value == "%email":
            data[key] = email
    return requests.post(url, files=files, data=data)

def process(tasks, inDir, outDir=None, sendTest=False, sendDevel=True):
    if outDir == None:
        outDir = os.path.join(input, "results")
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    
    for task in tasks:
        print "Processing task", task
        for dataset in ["devel", "test"]:
            if dataset == "devel" and not sendDevel:
                continue
            if dataset == "test" and not sendTest:
                continue
            
            inputFile = os.path.join(inDir, task + "-" + dataset + "-submit.tar.gz")
            email = 'jari.bjorne@utu.fi'
            r = submit(task, dataset, inputFile, email)
            if r != None: 
                print r
                outputFile = os.path.join(outDir, task + "-" + dataset + "-results.html")
                f = open(outputFile, "wt")
                f.write(r.text)
                f.close()

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(description="")
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("-t", "--tasks", default="COMPLETE", dest="tasks", help="")
    optparser.add_option("-d", "--dataset", default="DEVEL", dest="dataset", help="")
    (options, args) = optparser.parse_args()
    
    assert options.dataset in ["DEVEL", "TEST", "BOTH"]
    sendDevel = (options.dataset == "DEVEL") or (options.dataset == "BOTH")
    sendTest = (options.dataset == "TEST") or (options.dataset == "BOTH") 

    options.tasks = options.tasks.replace("COMPLETE", "GE09,ALL11,ALL13")
    options.tasks = options.tasks.replace("ALL11", "GE11,EPI11,ID11,BB11,BI11,BI11-FULL,CO11,REL11,REN11")
    options.tasks = options.tasks.replace("ALL13", "GE13,CG13,PC13,GRO13,GRN13,BB13T2,BB13T3")
    options.tasks = options.tasks.split(",")
    
    process(options.tasks, options.input, options.output, sendTest, sendDevel)