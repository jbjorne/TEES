from __future__ import division
from optparse import OptionParser
import sys

if __name__=="__main__":
    desc="A simple eval script for the svmmulticlass output. Assumes that the negative class is 1. Call it with \n\neval.py devel.log devel.classified. The log file contains the non-classifier decisions together with the GS classes.\n\n"
    parser = OptionParser(description=desc)
    (options, args) = parser.parse_args()

    correctClasses=[]
    predictedClasses=[]

    f=open(args[0],"rt")
    for line in f:
        line=line.strip()
        if not line:
            continue
        predicted,gs=line.split()
        if predicted=="CLASSIFIEROUT":
            predicted=None
        else:
            predicted=int(predicted)
        correctClasses.append(int(gs))
        predictedClasses.append(predicted)
    f.close()

    f=open(args[1],"rt")
    classifierPredictions=[]
    for line in f:
        line=line.strip()
        if not line:
            continue
        classifierPredictions.append(int(line.split()[0]))
    f.close()

    #Now inject the classifier predictions to the predictedClasses
    clsIdx=0
    for idx in range(len(predictedClasses)):
        if predictedClasses[idx]==None:
            predictedClasses[idx]=classifierPredictions[clsIdx]
            clsIdx+=1
    assert clsIdx==len(classifierPredictions)

    assert len(correctClasses)==len(predictedClasses)
    TP=0
    FP=0
    FN=0
    TN=0
    for gs,prediction in zip(correctClasses,predictedClasses):
        if prediction!=1:
            if gs!=prediction:
                FP+=1
            else:
                TP+=1
        else:
            if gs!=prediction:
                FN+=1
            else:
                TN+=1
    print "TP: %d  FP: %d  TN: %d  FN: %d"%(TP,FP,TN,FN)
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
    print "P: %.2f  R: %.2f  F: %.2f"%(P,R,F)
        
