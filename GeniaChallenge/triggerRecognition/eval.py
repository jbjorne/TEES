from __future__ import division
from optparse import OptionParser
import sys

if __name__=="__main__":
    desc="A simple eval script. Call it with eval.py GS SYS where GS and SYS are one-per-line class files. Negative class is 'neg'"
    parser = OptionParser(description=desc)
    (options, args) = parser.parse_args()

    correctClasses=[]
    predictedClasses=[]

    f=open(args[0],"rt")
    for line in f:
        line=line.strip()
        if not line:
            continue
        correctClasses.append(line)
    f.close()

    f=open(args[1],"rt")
    for line in f:
        line=line.strip()
        if not line:
            continue
        predictedClasses.append(line)
    f.close()

    assert len(correctClasses)==len(predictedClasses)
    perClass={} #key: className value: [TP,FP,FN]
    for gs,prediction in zip(correctClasses,predictedClasses):
        if gs==prediction:
            #it is a TP for that class
            cStats=perClass.setdefault(prediction,[0,0,0])
            cStats[0]+=1
        else:
            #FP for prediction
            cStats=perClass.setdefault(prediction,[0,0,0])
            cStats[1]+=1
            #FN for GS
            cStats=perClass.setdefault(gs,[0,0,0])
            cStats[2]+=1

    for cls,cStats in perClass.items():
        TP,FP,FN=cStats
        try:
            P=TP/(TP+FP)
        except:
            P=0.0
        try:
            R=TP/(TP+FN)
        except:
            R=0.0
        try:
            F=2*P*R/(P+R)
        except:
            F=0.0
        print cls, "%.2f"%(F*100)

        
