from __future__ import division
from optparse import OptionParser
import sys

def confidences(predictions):
    return ",".join("%d:%f"%(clsIdx+1,float(p)) for clsIdx,p in enumerate(predictions))

if __name__=="__main__":
    desc="A simple script that merges the .log and .classified files. Call it with \n\merge-prediction.py devel.log devel.classified. The log file contains the non-classifier decisions together with the GS classes.\n\n"
    parser = OptionParser(description=desc)
    (options, args) = parser.parse_args()

    predictedClasses=[]

    f=open(args[0],"rt")
    for line in f:
        line=line.strip()
        if not line:
            continue
        predicted=line.split()[0]
        if predicted=="CLASSIFIEROUT":
            predicted=None
        else:
            predicted=[int(predicted)]+[0.0 for x in range(int(predicted)-1)]+[1.0]
        predictedClasses.append(predicted)#A list with the selected class first, and then the predictions
    f.close()

    f=open(args[1],"rt")
    classifierPredictions=[]
    for line in f:
        line=line.strip()
        if not line:
            continue
        classifierPredictions.append(line.split())
    f.close()

    #Now inject the classifier predictions to the predictedClasses
    clsIdx=0
    for idx in range(len(predictedClasses)):
        if predictedClasses[idx]==None:
            predictedClasses[idx]=classifierPredictions[clsIdx]
            clsIdx+=1
    assert clsIdx==len(classifierPredictions)

    for prediction in predictedClasses:
        print int(prediction[0]),confidences(prediction[1:])
        
