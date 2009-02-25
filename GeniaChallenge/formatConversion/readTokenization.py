try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET

import cElementTreeUtils as ETUtils
import sys
from optparse import OptionParser
import TokenizationAlignment as TA #this one comes from CommonUtils
import re

unescapeDict={'-LRB-':'(',
              '-RRB-':')',
              '-LSB-':'[',
              '-RSB-':']',
              '-LCB-':'{',
              '-RCB-':'}'
              }

depRe=re.compile("^(.*?)\((.*)-([0-9]+)'?, (.*)-([0-9]+)'?\)$")

def readDepTrees(reportNumber,options):
    """Returns a list of lists of dependencies."""
    f=open(options.dir+"/%s.dep"%reportNumber,"rt")
    sents=[]
    currSent=[]
    emptyLineCounter=0
    for line in f:
        line=line.strip()
        if not line:
            #emptyline!
            emptyLineCounter+=1
            if emptyLineCounter%2!=0:
                sents.append(currSent)
                currSent=[]
            continue
        else:
            emptyLineCounter=0
        match=depRe.match(line)
        if not match:
            print >> sys.stderr, "WARNING:",line
            continue
        depType,t1,t1idx,t2,t2idx=match.group(1),match.group(2),match.group(3),match.group(4),match.group(5)
        t1=unescapeDict.get(t1,t1)
        t2=unescapeDict.get(t2,t2)        
        if t1idx!=t2idx:
            currSent.append((depType,t1,int(t1idx),t2,int(t2idx)))
    else:
        assert emptyLineCounter%2!=0
    f.close()
    return sents

posRe=re.compile(r"\(([^\(\) ]+) ([^\(\) ]+)\)")

def readPOSTags(reportNumber,options):
    """Returns a list of lists of postags"""
    f=open(options.dir+"/%s.pstree"%reportNumber,"rt")
    sents=[]
    currSent=[]
    for line in f:
        line=line.strip()
        for match in posRe.finditer(line):
            POS=match.group(1)
            POS=unescapeDict.get(POS,POS)
            WRD=match.group(2)
            WRD=unescapeDict.get(WRD,WRD)
            currSent.append((POS,WRD))
        else:
            sents.append(currSent)
            currSent=[]
    f.close()
    return sents

def computeTokens(reportNumber,options):
    """Returns the raw text string plus a list of (beg,end) character offsets of tokens + a set of indices of last tokens in a sentence."""
    f=open(options.dir+"/%s.txt"%reportNumber,"rt")
    rawTxt=f.read()
    f.close()

    f=open(options.dir+"/%s.tokenized"%reportNumber,"rt")
    tokTxt=[unescapeDict.get(token,token) for token in f.read().split()] #read & unescape tokens
    f.close()

    aligned=TA.align(list(rawTxt),tokTxt) #returns a list of len(tokTxt). Each item is a list of character offsets
    charOffsets=[(x[0],x[-1]) for x in aligned] #just pick the first and last
    #so now charOffsets is a list of pairs (Beg,End) with as many items as there are tokens

    #but better do at least some sanity checks:
    for b,e in charOffsets:
        txt=rawTxt[b:e+1]
        assert txt[0]!=" " and txt[-1]!=" ", "Token with a whitespace in it???"

    #now we should yet gather the set of sentence-final token indices
    f=open(options.dir+"/%s.tokenized"%reportNumber,"rt")
    tokCounter=0
    sFinal=set()
    for line in f:
        line=line.strip()
        tokCounter+=len(line.split())
        sFinal.add(tokCounter-1)
    f.close()
    #now sFinal is a set of indices of tokens that end a sentence
    return rawTxt,charOffsets,sFinal

def getOffsetV(offsetStr):
    b,e=offsetStr.split("-")
    return int(b),int(e)

def getOffsetS(b,e):
    return "%d-%d"%(b,e)

def reorderDocNode(dNode,rawTxt,charOffsets,sFinal,depTree,posTags):
    """receives an interaction XML document node and creates a new node with sentences/parses/tokens, etc"""
    #Build a list of character offsets of the sentences
    sentEnds=list(sFinal)
    sentEnds.sort() #list of token indices (into charOffsets) marking sentence ends
    
    sentOffsets=[]
    for sentNum,idx in enumerate(sentEnds):
        if sentNum==0:
            bOff=0
        else:
            bOff=charOffsets[sentEnds[sentNum-1]+1][0] #first character of last token of previous sentence+1
        eOff=charOffsets[idx][1]
        sentOffsets.append((bOff,eOff))
    #now sentOffsets lists (b,e) offsets of the sentences in the raw text
    #len(sentOffsets) tells how many sentences we have
    assert len(sentOffsets)==len(depTree), dNode.get("id")
    assert len(sentOffsets)==len(posTags), dNode.get("id")

    newDocNode=ET.Element("document")
    #create sentence nodes
    for idx,(b,e) in enumerate(sentOffsets):
        newSNode=ET.SubElement(newDocNode,"sentence")
        newSNode.set("text",rawTxt[b:e+1])
        newSNode.set("id",dNode.get("id")+".s"+str(idx))
        newSNode.set("origId",dNode.get("id")+".s"+str(idx))
        newSNode.set("charOffset",getOffsetS(b,e))
        #a stupid N^2 algorithm, but who cares...
        #which entities are mine?
        myEntities=set()
        for eNode in dNode.getiterator("entity"):
            eb,ee=getOffsetV(eNode.get("charOffset"))
            if eb>=b and ee<=e: #this entity is mine!
                newSNode.append(eNode)
                myEntities.add(eNode.get("id"))
                eNode.set("charOffset",getOffsetS(eb-b,ee-b)) #correct the character offset to match the sentence
                assert eNode.get("text")==newSNode.get("text")[eb-b:ee-b+1]
            elif eb>e or ee<b: #this entity is not mine
                pass
            else:
                assert False, "Entity crossing sentence boundary!!!"
        #which pairs are mine?
        for pNode in dNode.getiterator("interaction"):
            if pNode.get("e1") in myEntities:
                newSNode.append(pNode)

        #Build the analyses
        sa=ET.SubElement(newSNode,"sentenceanalyses")
        toks=ET.SubElement(sa,"tokenizations")
        tokenization=ET.SubElement(toks,"tokenization")
        tokenization.set("tokenizer","Charniak-Lease")
        #again, a stupid N^2 alg, but I don't care :)

        
        
        counter=1
        for tokenIdx,(tb,te) in enumerate(charOffsets):
            if tb>=b and te<=e: #the token is mine!
                tokNode=ET.SubElement(tokenization,"token")
                tokNode.set("charOffset",getOffsetS(tb-b,te-b)) #correct the character offset to match the sentence
                tokNode.set("id","clt_%d"%counter)
                tokNode.set("text",rawTxt[tb:te+1])
                if len(posTags[idx])==1 and posTags[idx][0][1]=="PARSE-FAILED":
                    print >> sys.stderr, "Parse failed in %s, no POS transferred for %s"%(dNode.get("id"),rawTxt[tb:te+1])
                    tokNode.set("POS","XXX")
                else:
                    assert rawTxt[tb:te+1]==posTags[idx][counter-1][1],"%s: %s   vs.   %s"%(dNode.get("id"),rawTxt[tb:te+1],posTags[idx][counter-1][1]) #check that POS of the correct word is being transferred
                    tokNode.set("POS",posTags[idx][counter-1][0])
                counter+=1
        #idx is the index of the sentence
        parses=ET.SubElement(sa,"parses")
        parse=ET.SubElement(parses,"parse")
        parse.set("parser","Charniak-Lease")
        parse.set("tokenizer","Charniak-Lease")
        for depCounter,(depType,t1,t1idx,t2,t2idx) in enumerate(depTree[idx]):
            depNode=ET.SubElement(parse,"dependency")
            depNode.set("id","clp_%d"%(depCounter+1))
            depNode.set("t1","clt_%d"%t1idx)
            depNode.set("t2","clt_%d"%t2idx)
            depNode.set("type",depType)
            assert t1.replace(" ","")==tokenization[t1idx-1].get("text").replace(" ",""), "%s: '%s' vs '%s'"%(dNode.get("id"),t1,tokenization[t1idx-1].get("text"))
            assert t2.replace(" ","")==tokenization[t2idx-1].get("text").replace(" ",""), "%s: '%s' vs '%s'"%(dNode.get("id"),t2,tokenization[t2idx-1].get("text"))

    #Sanity
    numPairsOld=sum(1 for x in dNode.getiterator("interaction"))
    numPairsNew=sum(1 for x in newDocNode.getiterator("interaction"))
    assert numPairsOld==numPairsNew

    numEntsOld=sum(1 for x in dNode.getiterator("entity"))
    numEntsNew=sum(1 for x in newDocNode.getiterator("entity"))
    assert numEntsOld==numEntsNew

    
    #Done
    return newDocNode
        
def reorderCorpus(cNode,options):
    newCorpus=ET.Element("corpus")
    newCorpus.set("source",cNode.get("source"))
    for dNode in cNode:
        assert dNode.tag=="document"
        assert len(dNode)==1 #exactly one sentence there
        reportID=dNode.get("id")
        rawTxt,charOffsets,sFinal=computeTokens(reportID,options)
        depTree=readDepTrees(reportID,options)
        posTags=readPOSTags(reportID,options)
        newD=reorderDocNode(dNode,rawTxt,charOffsets,sFinal,depTree,posTags)
        newCorpus.append(newD)
    return newCorpus
        
            
    


def printSeqClassData(reportNumber,charOffsets,rawTxt,sFinal,options):
    """Prints out the sequence-alignment data in a sort of reasonable form. charOffsets should be calculated using computeTokens"""

    triggers=[] #list of (beg,end,triggerType)
    
    f=open(options.dir+"/%s.a2"%reportNumber,"rt")
    for line in f:
        line=line.strip()
        if not line:
            continue
        fields=line.split(None,4)
        if fields[0][0]!="T" or fields[1]=="Entity": #only interested in T* entries that are not entities
            continue
        triggerType,beg,end,txt=fields[1],int(fields[2]),int(fields[3])-1,fields[4]
        assert rawTxt[beg:end+1]==txt, "%s: %s vs %s"%(reportNumber,rawTxt[beg:end+1],txt)
        triggers.append((beg,end,triggerType))

    triggers.sort()
    #Wanna make sure I understand the data:
    for idx in range(len(triggers)-1):
        assert triggers[idx][1]<triggers[idx+1][0], "Overlapping triggers?: %s: %s - %s"%(reportNumber,str(triggers[idx]),str(triggers[idx+1]))

    #OK, we are ready to go
    trigIdx=0
    if len(triggers)!=0:
        trigB,trigE,trigType=triggers[0]
    currentType=None
    
    for tokIdx,(b,e) in enumerate(charOffsets):
        #does this token end before the current trigger starts?
        if trigIdx==len(triggers) or e<trigB:
            print rawTxt[b:e+1], "O"
            currentType=None
        else:
            #does this token have at least a partial overlap with the trigger?
            if trigB<=b and b<=trigE or trigB<=e and e<=trigE:
                if currentType==None:
                    currentType=trigType
                    print rawTxt[b:e+1], "B_"+currentType
                else:
                    print rawTxt[b:e+1], "I_"+currentType
            #did we consume the current trigger?
            if e>=trigE: #yes!
                trigIdx+=1
                currentType=None
                if trigIdx<len(triggers):
                    trigB,trigE,trigType=triggers[trigIdx]
        if tokIdx in sFinal:
            print #empty line to divide sentences
    
        
if __name__=="__main__":
    desc="Reads from stdin an interaction XML produced by geniaToGifxml.py and plugs in the tokenization and parses from .tokenized and .dep files in the the directory specified by -d. Writes to stdout."
    usage="python readTokenization.py [options] < in > out"
    parser = OptionParser(description=desc,usage=usage)
    parser.add_option("-d", "--dir", dest="dir", action="store", default=".", help="The directory in which the .dep .tokenized files can be found.", metavar="DIR")

    (options, args) = parser.parse_args()

    corpus=ET.parse(sys.stdin).getroot()
    newCorpus=reorderCorpus(corpus,options)
    ETUtils.write(newCorpus,sys.stdout)
    
                        
