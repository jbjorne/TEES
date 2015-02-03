import sys, os
import requests #pip install requests if you don't have it already
import STFormat.STTools as STTools
import tempfile
import copy

URL = {
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

def submit(task, filename, email):
    global URL, DATA
    url = URL[task]
    filename = removeX(filename)
    
    files = {'file':open(filename)}
    data = copy.copy(DATA[task])
    for key in data:
        value = data[key]
        if value == "%email":
            data[key] = email
    r = requests.post(url, files=files, data=data)

if False:
    url = 'http://bionlp-st.dbcls.jp/GE/2011/eval-development/eval.cgi'
    filename = "/home/jari/experiments/TEES-upload/test-events.tar.gz"
    
    files = {'file':open(filename)} #'file' => name of html input field
    data = {'email': 'jari.bjorne@utu.fi'}
    r = requests.post(url, files=files, data=data)

if True:
    url = 'http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/EPI/eval/devel-submit.cgi'
    filename = "/home/jari/experiments/TEES-upload/EPI11-empty-events.tar.gz"
    filename = removeX(filename)
    
    files = {'file':open(filename)} #'file' => name of html input field
    data = {'email': 'jari.bjorne@utu.fi'}
    r = requests.post(url, files=files, data=data)
    
print r
print r.text