from __future__ import division
from optparse import OptionParser
try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET

import cElementTreeUtils as ETUtils
import sys

def translatePrediction(prediction,classNames):
    cls=classNames[int(prediction[0])]
    weights=prediction[1].split(",")
    weightsStr=[]
    for w in weights:
        clsNum,weight=w.split(":")
        clsName=classNames[int(clsNum)]
        weightsStr.append("%s:%s"%(clsName,weight))
    return cls,",".join(weightsStr)


def entitiesInSentence(sNode,classNames):
    global predictions
    global predictionIdx
    for tokenizationNode in sNode.getiterator("tokenization"):
        if tokenizationNode.get("tokenizer")=="split-Charniak-Lease":
            break
    else:
        assert False, "The tokenization is not present?"
    #OK, so now I have the tokens, and I can also have the classes for them.
    entities=[]
    for tokIdx,tokNode in enumerate(tokenizationNode):
        prediction,weights=translatePrediction(predictions[predictionIdx],classNames)
        predictionIdx+=1
        newEnt=ET.Element("entity")
        newEnt.set("isName","False")
        newEnt.set("type",prediction)
        newEnt.set("predictions",weights)
        newEnt.set("charOffset",tokNode.get("charOffset"))
        entities.append(newEnt)
    #Okay, now all the entities are in the entities list: they're missing ID and text and need to be inserted into the sNode
    #Find the entities that already are present so we can continue in the ID scheme
    #I also need to know where they are in the sNode so we don't have entities scattered
    insertAfter=-1 #this will be the index after which the newly generated entities will be plugged
    eIDs=[] #list of current entity numbers
    for elementIdx,element in enumerate(sNode):
        if element.tag=="entity":
            eIDs.append(int(element.get("id").split(".")[-1][1:]))
            insertAfter+=1
    eIDs.sort()
    if len(eIDs)==0:
        newEntId=0
    else:
        newEntId=eIDs[-1]+1
    for eNode in entities:
        eNode.set("id",sNode.get("id")+".e"+str(newEntId))
        b,e=eNode.get("charOffset").split("-")
        b,e=int(b),int(e)
        eNode.set("text",sNode.get("text")[b:e+1])
        assert len(eNode.get("text"))==e-b+1
        newEntId+=1
    sNode[insertAfter+1:insertAfter+1]=entities
        
            
    

if __name__=="__main__":
    desc="Given predictions for each and every token, and the class names, the correct entities will be created. The XML file to which the entities should be injected is read from stdin, the result is written to stdout."
    parser = OptionParser(description=desc)
    parser.add_option("--classNames",dest="classNames",action="store",default=None,help="Name of the classNames file.")
    parser.add_option("--predictionFile",dest="predictionFile",action="store",default=None,help="File that contains the predictions for each and every token, one per line.") 
    (options, args) = parser.parse_args()

    if options.classNames:
        classNames={}
        f=open(options.classNames,"rt")
        for line in f:
            line=line.strip()
            if not line:
                continue
            classNum,className=line.split()
            classNum=int(classNum)
            classNames[classNum]=className
        f.close()
    else:
        print >> sys.stderr, "You need a classNames file."
        sys.exit()

    f=open(options.predictionFile,"rt")
    predictions=[]
    predictionIdx=0
    for line in f:
        line=line.strip()
        if not line:
            continue
        predictions.append(line.split()) #predicted class strengths

    tree=ET.parse(sys.stdin).getroot()
    for sNode in tree.getiterator("sentence"):
        entitiesInSentence(sNode,classNames)
    ETUtils.write(tree,sys.stdout)
    
    
