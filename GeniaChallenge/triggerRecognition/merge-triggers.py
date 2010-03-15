try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import math
from optparse import OptionParser
import sys

def removeTriggers(sNode):
    toKill=[]
    for eNode in sNode.getiterator("entity"):
        if eNode.get("isName")=="False":
            toKill.append(eNode)
    for eNode in toKill:
        sNode.remove(eNode)
    
def copySNode(sNode):
    newSNode=ET.Element("sentence")
    for k in sNode.attrib.keys():
        newSNode.attrib[k]=sNode.attrib[k]
    for x in sNode:
        newSNode.append(x)
    return newSNode


def entitiesInSentence(sNode,predictions):
    removeTriggers(sNode)
    for tokenizationNode in sNode.getiterator("tokenization"):
        if tokenizationNode.get("tokenizer")=="split-Charniak-Lease":
            break
    else:
        assert False, "The tokenization is not present?"
    #OK, so now I have the tokens, and I can also have the classes for them.
    entities=[]
    currentClass="neg"
    currentEntity=None
    assert len(predictions)==len(tokenizationNode)
    for tokIdx,tokNode in enumerate(tokenizationNode):
        prediction=predictions[tokIdx]
#         if prediction==currentClass:
#             #The current class continues, so do we
#             continue
        #Must close the current entity -> the class has changed!
        if currentClass!="neg":
            assert currentEntity!=None
            assert currentEntity.get("charOffset").endswith("-")
            assert tokIdx>0
            currentEntity.set("charOffset",currentEntity.get("charOffset")+tokenizationNode[tokIdx-1].get("charOffset").split("-")[1])
            currentEntity=None
        #Current entity closed,
        currentClass=prediction
        if currentClass!="neg": #new entity needs to be started
            assert currentEntity==None
            #We should start a new entity
            tokenStart=tokNode.get("charOffset").split("-")[0]
            currentEntity=ET.Element("entity")
            currentEntity.set("charOffset",tokenStart+"-")
            currentEntity.set("isName","False")
            currentEntity.set("type",currentClass)
            entities.append(currentEntity)
    else:
        if currentEntity!=None: #end of sentence with open entity. Must close it
            assert currentEntity.get("charOffset").endswith("-")
            currentEntity.set("charOffset",currentEntity.get("charOffset")+tokenizationNode[tokIdx-1].get("charOffset").split("-")[1])
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


def sNodeIterator(f):
    for event,elem in ET.iterparse(f,events=("end",)):
        if elem.tag=="sentence":
            yield elem
            elem.clear()


def merge2dicts(d1,d2,w):
    classSet=set(d1.keys())
    classSet.update(d2.keys())
    newD={}
    for cls in classSet:
        pred=w*d1.get(cls,0.0)+(1-w)*d2.get(cls,0.0)
        newD[cls]=pred
    return newD

def winningClass(d):
    wCls=None
    maxW=None
    for cls,w in d.items():
        if maxW==None or maxW<w:
            wCls=cls
            maxW=w
    mC=sum(1 for w in d.values() if w==maxW)
    if mC>1:
        print >> sys.stderr, "!",
    return wCls

def merge2sents(sNode1,sNode2,w,b1,b2):
    d1s=tokenClasses(sNode1,boost=b1)
    d2s=tokenClasses(sNode2,boost=b2)
    assert len(d1s)==len(d2s)
    ds=[merge2dicts(d1,d2,w) for d1,d2 in zip(d1s,d2s)]
    classes=[winningClass(d) for d in ds]
    newSNode=copySNode(sNode1)
    removeTriggers(newSNode)
    entitiesInSentence(newSNode,classes)
    return newSNode

def tokenClasses(sNode,tokenizer="split-Charniak-Lease",N=5,boost=1.0):
    """Returns a list of dictionaries. Tokens X classWeights"""
    for tokzNode in sNode.getiterator("tokenization"):
        if tokzNode.get("tokenizer")==tokenizer:
            break
    else:
        assert False
    result=[{} for x in tokzNode]
    for idx,tokNode in enumerate(tokzNode):
        b,e=tokNode.get("charOffset").split("-")
        b,e=int(b),int(e)
        for eNode in sNode.getiterator("entity"):
            eb,ee=eNode.get("charOffset").split("-")
            eb,ee=int(eb),int(ee)
            if eNode.get("isName")=="False" and (eb>=b and eb<=e or ee>=b and ee<=e):
                break
        else:
            #No entity covers this token
            result[idx]["neg"]=1.0
            continue #just make a negative here
        #Pick the N most likely classes
        predictions=eNode.get("predictions")
        assert predictions, ">>"+predictions+"<<"
        predictions=predictions.split(",")
        prds=[]
        for p in predictions:
            cls,pW=p.split(":")
            pW=float(pW)
            prds.append([pW,cls])
        prds.sort(reverse=True)
        prds=prds[:N]
        #So now I have a list of N best [weight,class] pairs
        #make sure all are positive
        if prds[-1][0]<0:
            for i in range(len(prds)):
                prds[i][0]-=prds[-1][0]
        total=sum(x[0] for x in prds) #sum of the weights
        #Now I can build the dictionary
        for pW,cls in prds:
            result[idx][cls]=pW/float(total)
            assert result[idx][cls]<=1.0 and result[idx][cls]>=0.0,"%f/%f=%f"%(pW,total,result[idx][cls])
    for d in result:
        d["neg"]=d.get("neg",0.0)*boost
    return result

if __name__=="__main__":
    desc="Weighted combination of several trigger word recognizers"
    parser = OptionParser(description=desc)
    parser.add_option("--lambda",dest="l",action="store",default=None,type="float",help="The mixing weight of predictions1 with predictions2. A number between 0 and 1. No default.")
    parser.add_option("--b1",dest="b1",action="store",default=None,type="float",help="Recall boost of file1")
    parser.add_option("--b2",dest="b2",action="store",default=None,type="float",help="Recall boost of file2")
    

    (options, args) = parser.parse_args()

    if options.l==None:
        print >> sys.stderr, "You need to give a lambda"
        sys.exit(1)

    tree1=ET.parse(args[0]).getroot()
    tree2=ET.parse(args[1]).getroot()
    assert len(tree1)==len(tree2)
    for docIdx in range(len(tree1)):
        assert len(tree1[docIdx])==len(tree2[docIdx])
        for sIdx in range(len(tree1[docIdx])):
            newSNode=merge2sents(tree1[docIdx][sIdx],tree2[docIdx][sIdx],options.l,options.b1,options.b2)
            tree1[docIdx][sIdx]=newSNode
    ETUtils.write(tree1,sys.stdout)
