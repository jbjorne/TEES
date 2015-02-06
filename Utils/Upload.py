import sys, os
import requests #pip install requests if you don't have it already
import STFormat.STTools as STTools
import tempfile
import copy

URL = {}
URL["devel"] = {
"EPI11":'http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/EPI/eval/devel-submit.cgi',
"ID11":'http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/ID/eval/devel-submit.cgi',
}

DATA = {
"EPI11":{"email":"%email"},
"ID11":{"email":"%email"},
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

def removeX(filename):
    documents = STTools.loadSet(filename)
    newFilename = os.path.join(tempfile.tempdir, filename.rsplit(".", 2)[0] + "-no-X.tar.gz")
    STTools.writeSet(documents, newFilename)
    return newFilename

def submit(task, dataset, filename, email):
    global URL, DATA
    url = URL[task][dataset]
    filename = removeX(filename)
    
    files = {'file':open(filename)}
    data = copy.copy(DATA[task])
    for key in data:
        value = data[key]
        if value == "%email":
            data[key] = email
    return requests.post(url, files=files, data=data)

def process(tasks, input, output=None):
    if output == None:
        output == os.path.join(input, "results")
    if not os.path.exists(output):
        os.makedirs(output)
    for task in tasks:
        
        outfile = os.path.join(outdir, os.path.basename(filename) + "-results.html")
        email = 'jari.bjorne@utu.fi'
        r = submit("EPI11", filename, email) 
        print r
        print r.text
        f = open(outfile, "wt")
        f.write(r.text)
        f.close()
    
process()

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
    (options, args) = optparser.parse_args()

    options.tasks = options.tasks.replace("COMPLETE", "GE09,ALL11,ALL13")
    options.tasks = options.tasks.replace("ALL11", "GE11,EPI11,ID11,BB11,BI11,BI11-FULL,CO11,REL11,REN11")
    options.tasks = options.tasks.replace("ALL13", "GE13,CG13,PC13,GRO13,GRN13,BB13T2,BB13T3")
    options.tasks = options.tasks.split(",")
    