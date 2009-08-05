import sys, os
import subprocess
sys.path.append(os.path.dirname(__file__)+"/..")
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier as classifier

class CSCConnection:
    def __init__(self, workSubDir):
        self.account = "jakrbj@louhi.csc.fi"
        self.workDir = "/wrk/jakrbj/" + workSubDir
    
    def exists(self, filename):
        p = subprocess.Popen("ssh " + self.account + " 'ls " + self.workDir + "/" + filename + "'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if len(p.stdout.readlines()) > 0:
            return True
        else:
            return False
    
    def upload(self, src, dst=None, replace=True):
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and self.exists(dst):
            return False
        else:
            print "scp " + src + " " + self.account + ":" + self.workDir + "/" + dst
            subprocess.call("scp " + src + " " + self.account + ":" + self.workDir + "/" + dst, shell=True)
            return True
        
    def download(self, src, dst=None, replace=True):
        if dst == None:
            dst = os.path.split(src)[-1]
        if replace == False and os.path.exists(dst):
            return False
        else:
            subprocess.call("scp " + self.account + ":" + self.workDir + "/" + src + " " + dst, shell=True)
            return True
    
    def run(self, script):
        subprocess.call("ssh " + self.account + " '" + script + "'", shell=True)
    
    def test(self):
        print "testing"
        subprocess.call("ssh jakrbj@louhi.csc.fi 'ls; exit'", shell=True)
        subprocess.call("scp scp-test-file.txt jakrbj@louhi.csc.fi:/home/u1/jakrbj/scp-test-file.txt", shell=True)
        #p = subprocess.Popen("ls", stdout=subprocess.PIPE)
        #print p.stdout.readlines()
        

if __name__=="__main__":
    c = CSCConnection("remoteTest")
    #c.test()
    #c.exists("merg-info.py")
    classifier.trainAndTestOnLouhi("trigger-train-examples", "trigger-test-examples", {"c":1000}, c)
    print c.exists("trigger-test-examples")