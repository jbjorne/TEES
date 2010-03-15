#import tre #fuzzy text match

import re
import codecs
try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET

import cElementTreeUtils as ETUtils
import sys

from optparse import OptionParser

class FeatureNumbers:
    """A persistent feature dictionary. Key: feature name Value: feature dimension (int)"""
    
    def __init__(self,fileName=None):
        self.dict={}
        self.fCounter=0 #the highest assigned feature number so-far
        self.fileName=fileName

        if fileName:
            f=codecs.open(fileName,"rt","utf-8")
            for line in f:
                line=line.strip()
                if not line or line.startswith("#"):
                    continue
                fTxt,fNumber=line.split("\t")
                fNumber=int(fNumber)
                if self.fCounter<=fNumber:
                    self.fCounter=fNumber
                assert fTxt not in self.dict
                self.dict[fTxt]=fNumber
            f.close()

    def f2num(self,featName):
        """Translates feature name to feature number"""
        featNum=self.dict.setdefault(featName,self.fCounter+1)
        if self.fCounter<featNum:
            self.fCounter=featNum
        return featNum

    def save(self,fileName=None):
        """Saves the dict under the given name. If None is given, then
        under the name from which it was read"""
        if fileName==None:
            fileName=self.fileName
        f=codecs.open(fileName,"wt","utf-8")
        for fName,fNumber in self.dict.items():
            print >> f, fName+"\t"+str(fNumber)
        f.close()


def charOffStr2tuple(cStr):
    b,e=cStr.split("-")
    b,e=int(b),int(e)
    return b,e

def tokTxt(b,e,sNode):
    return sNode.get("text")[b:e+1]

def toknodeTxt(tokNode,sNode):
    b,e=charOffStr2tuple(tokNode.get("charOffset"))
    return tokTxt(b,e,sNode)

def tokenType(b,e,eOffs):
    """b,e is the token's charOff, eOffs is the list of entity offsets and types. Returns None if no overlap found"""
    for eb,ee,eType in eOffs:
        if eb<=b and b<=ee or eb<=e and e<=ee:
            return eType
    else:
        return None

def tokClasses(tokenizationNode,sNode,ibo=False):
    """Returns a list of the correct IBO classes for each token in tokenizationNode"""
    #1) get a list of entities, their char offsets, and classes
    eOffs=[] #(b,e,type),...
    for eNode in sNode.getiterator("entity"):
        if eNode.get("isName")=="True":
            continue
        #we have a trigger word
        b,e=charOffStr2tuple(eNode.get("charOffset"))
        eOffs.append((b,e,eNode.get("type")))
    tokClasses=[]
    for tNode in tokenizationNode:
        b,e=charOffStr2tuple(tNode.get("charOffset"))
        tType=tokenType(b,e,eOffs)
        tokClasses.append(tType)
    #Now I have a list with the classes, now I turn it into the IBO coding
    tokClassesIBO=[]
    for idx,tType in enumerate(tokClasses):
        if tType==None:
            tokClassesIBO.append("neg")
        elif idx==0:
            if ibo:
                tokClassesIBO.append(tType+"B")
            else:
                tokClassesIBO.append(tType)
        else:
            if tokClasses[idx-1]==tType:
                if ibo:
                    tokClassesIBO.append(tType+"I")
                else:
                    tokClassesIBO.append(tType)
            else:
                if ibo:
                    tokClassesIBO.append(tType+"B")
                else:
                    tokClassesIBO.append(tType)
    return tokClassesIBO

def addF(fName,fDict):
    fDict[fName]=fDict.get(fName,0)+1

def defF(fName,fVal,fDict):
    fDict[fName]=fVal

def tokFeatures(tIdx,tokenizationNode,sNode,fDict):
    b,e=charOffStr2tuple(tokenizationNode[tIdx].get("charOffset"))
    addF("toktxt:"+tokTxt(b,e,sNode).lower().replace(" ","_"),fDict)
    return fDict

    
def entityFeatures(tIdx,tokenizationNode,sNode,fDict):
    eOffs=[] #(b,e,type),...
    for eNode in sNode.getiterator("entity"):
        if eNode.get("isName")=="False":
            continue
        #we have a name
        b,e=charOffStr2tuple(eNode.get("charOffset"))
        eOffs.append((b,e,eNode.get("type")))
    tb,te=charOffStr2tuple(tokenizationNode[tIdx].get("charOffset"))
    #before/after
    before=sum(1 for b,e,eType in eOffs if e<tb)
    after=sum(1 for b,e,eType in eOffs if b>te)
    defF("ebefore",before,fDict)
    defF("eafter",after,fDict)
    

    

def majorityClass(tokIdx,tokenizationNode,sNode,gztr):
    b,e=charOffStr2tuple(tokenizationNode[tokIdx].get("charOffset"))
    txt=tokTxt(b,e,sNode).lower()
    clsDct=gztr.get(txt,{})
    if len(clsDct)==0:
        return "neg"
    if len(clsDct)==1:
        return clsDct.keys()[0]
    #Is there any class with >0.98 weight?
    for cls,w in clsDct.items():
        if w>0.97:
            return cls
    #Cannot decide
    return None

def gztrMember(tokIdx,tokenizationNode,sNode,gztr):
    txt=toknodeTxt(tokenizationNode[tokIdx],sNode).lower()
    clsDct=gztr.get(txt,{})
    if len(clsDct)==0:
        return set([("neg",1.0)])
    else:
        return set(clsDct.items())



def contextTokens(tokIdx,tokenizationNode,sNode,gztr):
    #collocation neighbors
    NC=4 #number of left neighbor collocations
    lc=range(max(tokIdx-NC,0),tokIdx)
    rc=range(tokIdx+1,min(tokIdx+NC+1,len(tokenizationNode)))
    #context neighbors
    CC=7 #context BoW
    ln=range(max(tokIdx-CC,0),tokIdx)
    rn=range(tokIdx+1,min(tokIdx+CC+1,len(tokenizationNode)))
    #parse-based context
    for parseNode in sNode.getiterator("parse"):
        if parseNode.get("parser")=="split-Charniak-Lease":
            break
    else:
        assert False, "Cannot find the parse"
    #So now I have the parse
    #Let's get some features
    depIn=[] #list of (tokIdx,dType) pairs
    depOut=[] #same here
    for depNode in parseNode:
        gov=int(depNode.get("t1").split("_")[1])-1
        dep=int(depNode.get("t2").split("_")[1])-1
        if gov==tokIdx:
            depOut.append((dep,depNode.get("type")))
        elif dep==tokIdx:
            depIn.append((dep,depNode.get("type")))
    return lc,rc,ln,rn,depIn,depOut


#def entityCountInContext(tokIdx,tokenizationNode,s

def contextFeatures(tokIdx,tokenizationNode,sNode,gztr,fDict):
    lc,rc,ln,rn,depIn,depOut=contextTokens(tokIdx,tokenizationNode,sNode,gztr)
    tokTexts=[toknodeTxt(tNode,sNode).lower() for tNode in tokenizationNode]
    tokPOSs=[tNode.get("POS") for tNode in tokenizationNode]
    #1) collocations
#     for idx in lc+rc:
#         addF("C%dTXT%s"%(idx-tokIdx,tokTexts[idx]),fDict)
#         addF("C%dPOS%s"%(idx-tokIdx,tokPOSs[idx]),fDict)
    for idx in ln:
        addF("LNTXT%s"%tokTexts[idx],fDict)
    for idx in rn:
        addF("RNTXT%s"%tokTexts[idx],fDict)
    #2)nearby gazzetteer hits
    for idx in ln:
        for gztrName,gztrW in gztrMember(idx,tokenizationNode,sNode,gztr):
            defF("GZTRL:%s"%(gztrName),gztrW,fDict)
    for idx in rn:
        for gztrName,gztrW in gztrMember(idx,tokenizationNode,sNode,gztr):
            defF("GZTRR:%s"%(gztrName),gztrW,fDict)
    #3) dependency tree collocations
    for idx,dType in depIn:
        addF("SCIN:TXT%sDType%s"%(tokTexts[idx],dType),fDict)
        addF("SCIN:POS%sDType%s"%(tokTexts[idx],dType),fDict)
        addF("SCIN:TXT%s"%tokTexts[idx],fDict)
        addF("SCIN:dType%s"%dType,fDict)
        for gztrName,gztrW in gztrMember(idx,tokenizationNode,sNode,gztr):
            defF("SCIN:GZTR%s"%(gztrName),gztrW,fDict)
            defF("SCIN:GZTR%s:DType:%s"%(gztrName,dType),gztrW,fDict)
    for idx,dType in depOut:
        addF("SCOUT:TXT%sDType%s"%(tokTexts[idx],dType),fDict)
        addF("SCOUT:POS%sDType%s"%(tokTexts[idx],dType),fDict)
        addF("SCOUT:TXT%s"%tokTexts[idx],fDict)
        addF("SCOUT:dType%s"%dType,fDict)
        for gztrName,gztrW in gztrMember(idx,tokenizationNode,sNode,gztr):
            defF("SCOUT:GZTR%s"%(gztrName),gztrW,fDict)
            defF("SCOUT:GZTR%s:DType:%s"%(gztrName,dType),gztrW,fDict)
        




def gztrFeatures(tokIdx,tokenizationNode,sNode,gztr,fDict):
    """Adds the gztr features. Returns False if this token's class is obvious."""
    b,e=charOffStr2tuple(tokenizationNode[tokIdx].get("charOffset"))
    txt=tokTxt(b,e,sNode).lower()
    clsDct=gztr.get(txt,{})
    gztrSet=set(clsDct.keys())
    if clsDct=={}: #only O -> most of the cases
        fDict["CLS_Neg"]=1.0
    else:
        for cls,v in clsDct.items():
            fDict["CLS_"+cls]=v


def sentenceFeatures(sNode,fDict):
    #Count the entities
    entCount=sum(1 for e in sNode.getiterator("entity") if e.get("isName")=="True")
    defF("eCount",entCount,fDict)
    addF("eCount%d"%entCount,fDict)
    

def sentence2example(sNode,options,gztr,classNames,featureNames,seqNum,logFile):
    #Find the correct tokenization
    for tokenizationNode in sNode.getiterator("tokenization"):
        if tokenizationNode.get("tokenizer")=="split-Charniak-Lease":
            break
    else:
        assert False, "Did not find split-Charniak-Lease tokenization"
    if options.train:
        tClasses=tokClasses(tokenizationNode,sNode)
        assert len(tClasses)==len(tokenizationNode)
    for tokIdx,tokNode in enumerate(tokenizationNode):
        if options.train:
            gsClass=tClasses[tokIdx]
        else:
            gsClass=None
        majClass=majorityClass(tokIdx,tokenizationNode,sNode,gztr)
        if majClass!=None: #there is a majority class
            if logFile:
                print >> logFile, classNames[majClass], classNames[gsClass]
            continue
        tokFDict={}#key: feature name, val: count        
        tokFeatures(tokIdx,tokenizationNode,sNode,tokFDict)
        gztrFeatures(tokIdx,tokenizationNode,sNode,gztr,tokFDict)
        contextFeatures(tokIdx,tokenizationNode,sNode,gztr,tokFDict)
        #bowFeatures(tokIdx,tokenizationNode,sNode,tokFDict)
        entityFeatures(tokIdx,tokenizationNode,sNode,tokFDict)
        #parseFeatures(tokIdx,tokenizationNode,sNode,tokFDict)
        sentenceFeatures(sNode,tokFDict)
        SVMline(tokFDict,classNames,featureNames,gsClass,seqNum,"")
        if logFile:
            print >> logFile, "CLASSIFIEROUT", classNames[gsClass]



def SVMline(tokFDict,classNames,featureNames,gsClass,seqNum,comment):
    fVals=[(featureNames.f2num(f),v) for f,v in tokFDict.items()]
    fVals.sort()
    fString=" ".join(str(f)+":"+str(v) for f,v in fVals)
    if gsClass==None:
        gsClassStr=""
    else:
        gsClassStr=classNames[gsClass]
    print str(gsClassStr)+" "+fString+" # "+comment

def buildGztr(fileIn):
    """Builds the master gazzeteer. Produces a dictionary that should be saved with saveGztr and loaded with loadGztr."""
    gztr={} #key: token value: dictionary (key: className, value count)
    tree=ET.parse(fileIn).getroot()
    for sNode in tree.getiterator("sentence"):
        for tokenizationNode in sNode.getiterator("tokenization"):
            if tokenizationNode.get("tokenizer")=="split-Charniak-Lease":
                break
        else:
            assert False, "Did not find split-Charniak-Lease tokenization"
        tClasses=tokClasses(tokenizationNode,sNode)
        assert len(tClasses)==len(tokenizationNode)
        for tokIdx,tokNode in enumerate(tokenizationNode):
            gsClass=tClasses[tokIdx]
            b,e=charOffStr2tuple(tokNode.get("charOffset"))
            tokNodeTxt=tokTxt(b,e,sNode).lower()
            tokDict=gztr.setdefault(tokNodeTxt,{})
            tokDict[gsClass]=tokDict.get(gsClass,0)+1
    return gztr

def saveGztr(gztr,fileName):
    """Saves the gztr produced by buildgztr"""
    f=open(fileName,"wt")
    for txt,clsDct in gztr.items():
        total=sum(v for v in clsDct.values())
        if clsDct.get("neg",-1)==total:
            continue
        print >> f, txt+"\t",
        for cls,count in clsDct.items():
            print >> f, cls+":"+str(float(count)/total),
        print >> f
    f.close()

def loadGztr(fileName):
    """Loads the gztr produced by saveGztr"""
    gztr={}
    f=open(fileName,"rt")
    for line in f:
        line=line.strip()
        if not line:
            continue
        txt,clsVals=line.split("\t")
        clsDct=gztr.setdefault(txt,{})
        for clsVal in clsVals.split():
            cls,v=clsVal.split(":")
            v=float(v)
            assert cls not in clsDct
            clsDct[cls]=v
    f.close()
    return gztr
    

if __name__=="__main__":
    desc="Feature builder for a CRF-based entity recognizer"
    parser = OptionParser()
    parser.add_option("--maxsent", dest="maxsent",action="store",type="int",default=-1,help="limit the generation to max this many sentences. Unlimited by default.")
    parser.add_option("--train", dest="train",action="store_true",default=False,help="Train. Outputs the correct classes.")
    parser.add_option("--buildgztr",dest="buildgztr",action="store",default=None,help="Name of the gztr to create from interaction XML on stdin")
    parser.add_option("--loadgztr",dest="loadgztr",action="store",default=None,help="Name of the gztr to load.")
    parser.add_option("--classNames",dest="classNames",action="store",default=None,help="Name of the classNames file.")
    parser.add_option("--featureNames",dest="featureNames",action="store",default=None,help="Name of the featureNames file. Gets created if missing.")
    parser.add_option("--noSaveFNames",dest="saveFeatureNames",action="store_false",default=True,help="Do not save the feature name dictionary once done.")
    parser.add_option("--declog",dest="declog",action="store",default=None,help="File to which all decisions that are not ran through the classifier are written.")
    parser.add_option("--justlist",dest="justlist",action="store_true",default=False,help="Simply list the classes for each token in the file.")
#    parser.add_option("--list", dest="list",action="store",default=None,help="file with the list of strings to recognize")
#     parser.add_option("-q", "--quiet",
#                       action="store_false", dest="verbose", default=True,
#                       help="don't print status messages to stdout")

    (options, args) = parser.parse_args()

    if options.justlist:
        for event,element in ET.iterparse(sys.stdin,events=("end",)):
            if element.tag=="sentence":
                for tokenizationNode in element.getiterator("tokenization"):
                    if tokenizationNode.get("tokenizer")=="split-Charniak-Lease":
                        break
                else:
                    assert False
                cls=tokClasses(tokenizationNode,element,ibo=False)
                for c in cls:
                    print c
                element.clear()
        sys.exit(0)

    if options.buildgztr:
        gztr=buildGztr(sys.stdin)
        saveGztr(gztr,options.buildgztr)
        sys.exit()


    if options.classNames:
        classNames={}
        f=open(options.classNames,"rt")
        for line in f:
            line=line.strip()
            if not line:
                continue
            classNum,className=line.split()
            classNum=int(classNum)
            classNames[className]=classNum
        f.close()
    else:
        print >> sys.stderr, "You need a classNames file."
        sys.exit()

    if options.featureNames:
        try:
            f=open(options.featureNames,"rt")
            f.close()
        except:
            print >> sys.stderr, options.featureNames, "not found. Creating new."
            f=open(options.featureNames,"wt")
            f.close()
        featureNames=FeatureNumbers(options.featureNames)
    else:
        print >> sys.stderr, "You need a featureNames file."
        sys.exit()


    if not options.loadgztr:
        print >> sys.stderr, "Get yourself a gztr using --buildgztr"
        sys.exit()

    if options.declog:
        logFile=open(options.declog,"wt")
    else:
        logFile=None

    if options.maxsent>-1:
        print >> sys.stderr, "Warning: only first %d sentences used in training!"%(options.maxsent)
    gztr=loadGztr(options.loadgztr)
    sCounter=0
    for event,element in ET.iterparse(sys.stdin,events=("end",)):
        if element.tag=="sentence":
            if options.maxsent>-1 and sCounter>options.maxsent:
                break
            sentence2example(element,options,gztr,classNames,featureNames,sCounter+1,logFile)
            sCounter+=1
            if sCounter%10==0:
                print >> sys.stderr, ".",
            element.clear()
    print >> sys.stderr

        
        
    if options.saveFeatureNames:
        print >> sys.stderr, "Saving feature names"
        featureNames.save()
