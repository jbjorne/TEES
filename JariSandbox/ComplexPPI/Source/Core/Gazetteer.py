try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import sys
from optparse import OptionParser

def charOffStr2tuple(cStr):
    b,e=cStr.split("-")
    b,e=int(b),int(e)
    return b,e

def tokenType(b,e,eOffs):
    """b,e is the token's charOff, eOffs is the list of entity offsets and types. Returns None if no overlap found"""
    for eb,ee,eType in eOffs:
        if eb<=b and b<=ee or eb<=e and e<=ee:
            return eType
    else:
        return None

def tokTxt(b,e,sNode):
    return sNode.get("text")[b:e+1]

def toknodeTxt(tokNode,sNode):
    b,e=charOffStr2tuple(tokNode.get("charOffset"))
    return tokTxt(b,e,sNode)


def tokClasses(tokenizationNode,sNode,ibo=False):
    """Returns a list of the correct classes for each token in tokenizationNode
    if ibo is given, classes are BEGIN-INSIDE-OUTSIDE, otherwise they are just INSIDE-OUTSIDE"""
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
    #I have a list with the classes, now I turn it into the IBO coding or IO coding
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

def gazetteer(fileIn,fileOut=None,tokenization="split-Charniak-Lease"):
    """Builds the master gazzeteer.
    fileIn: a string (ending with .xml or .xml.gz), an open input stream, an ElementTree or an Element
    fileOut: a string or None. If given, the resulting gazzetteer will be written out
    tokenization: name of the tokenization to be used

    Produces a dictionary with...
    """

    
    gztr={} #key: token value: dictionary (key: className, value count)
    root=ETUtils.ETFromObj(fileIn)
    if not ET.iselement(root):
        assert isinstance(root,ET.ElementTree)
        root=root.getroot()
    for sNode in root.getiterator("sentence"):
        for tokenizationNode in sNode.getiterator("tokenization"):
            if tokenizationNode.get("tokenizer")==tokenization:
                break
        else:
            assert False, "Did not find %s tokenization"%tokenization
        tClasses=tokClasses(tokenizationNode,sNode)
        assert len(tClasses)==len(tokenizationNode)
        for tokIdx,tokNode in enumerate(tokenizationNode):
            gsClass=tClasses[tokIdx]
            b,e=charOffStr2tuple(tokNode.get("charOffset"))
            tokNodeTxt=tokTxt(b,e,sNode).lower()
            tokDict=gztr.setdefault(tokNodeTxt,{})
            tokDict[gsClass]=tokDict.get(gsClass,0)+1
    if fileOut:
        saveGztr(gztr,fileOut)
    return gztr

def saveGztr(gztr,fileName):
    """Saves the gztr produced by buildgztr"""
    if isinstance(fileName,str):
        f=open(fileName,"wt")
    else:
        f=fileName #assume it is an open write stream since it's not a string
    for txt,clsDct in gztr.items():
        total=sum(v for v in clsDct.values())
        if clsDct.get("neg",-1)==total:
            #tokens that are only negative are not saved
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
    desc="Given a GS XML, builds a gazetteer with all tokens seen in a positive label context, and the label/count information. Reads stdin, writes stdout"""
    parser = OptionParser(description=desc)
    parser.add_option("-t","--tokenization",default="split-Charniak-Lease",dest="tokenization",help="Tokenization to be used. Defaults to split-Charniak-Lease")
    (options, args) = parser.parse_args()
    gazetteer(sys.stdin,sys.stdout,options.tokenization)
