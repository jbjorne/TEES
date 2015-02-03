import requests #pip install requests if you don't have it already
import STFormat.STTools as STTools

def removeX(filename):
    documents = STTools.loadSet(filename)
    newFilename = filename.rsplit(".", 2)[0] + "-no-X.tar.gz"
    STTools.writeSet(documents, newFilename)
    return newFilename

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