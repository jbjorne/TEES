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

def readDepTrees(txtDepFName,options):
    """Returns a list of lists of dependencies."""
    f=open(txtDepFName,"rt")
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
        t1=unescTok(t1)
        t2=unescTok(t2)        
        if t1idx!=t2idx:
            currSent.append((depType,t1,int(t1idx),t2,int(t2idx)))
    else:
        assert emptyLineCounter%2!=0
    f.close()
    return sents

posRe=re.compile(r"\(([^\(\) ]+) ([^\(\) ]+)\)")


def readPOSTags(txtPennFName,options):
    """Returns a list of lists of postags"""
    f=open(txtPennFName,"rt")
    sents=[]
    currSent=[]
    for line in f:
        line=line.strip()
        for match in posRe.finditer(line):
            POS=match.group(1)
            POS=unescTok(POS)
            WRD=match.group(2)
            currSent.append((POS,unescTok(WRD).replace("``",'"').replace("''",'"')))
        else:
            sents.append(currSent)
            currSent=[]
    f.close()
    return sents

def unescTok(s):
    return s.replace("-LRB-","(").replace("-LCB-","{").replace("-LSB-","[").replace("-RRB-",")").replace("-RCB-","}").replace("-RSB-","]")

def inject(cNode,deps,postags,offsets,tokens,options):
    #cNode is the corpus node in the XML
    #deps is a list of lists of (dType,tok1,tok1Idx,tok2,tok2Idx)
    #postags is a list of lists of posTag
    assert len(deps)==len(postags)
    assert len(deps)==len(offsets)
    assert len(deps)==len(tokens)
    assert len(deps)==sum(1 for x in cNode.getiterator("sentence"))
    for sDeps,sTags,sOffsets,sTokens,sNode in zip(deps,postags,offsets,tokens,cNode.getiterator("sentence")):
        assert len(sTags)==len(sOffsets), str(sTags)+"\n\n"+str(sTokens)
        assert len(sTags)==len(sTokens)
        tokenization=ET.Element("tokenization")
        tokenization.set("tokenizer",options.tokenization)
        for tokenIdx,(tb,te) in enumerate(sOffsets):
            tokNode=ET.SubElement(tokenization,"token")
            tokNode.set("charOffset",getOffsetS(tb,te))
            tokNode.set("id","clt_%d"%(tokenIdx+1))
            tokNode.set("text",sNode.get("text")[tb:te+1])
            assert tokNode.get("text")==sTokens[tokenIdx]
            #                 if len(posTags[idx])==1 and posTags[idx][0][1]=="PARSE-FAILED":
            #                     print >> sys.stderr, "Parse failed in %s, no POS transferred for %s"%(dNode.get("id"),rawTxt[tb:te+1])
            #                     tokNode.set("POS","XXX")
            #                 else:
            assert tokNode.get("text")==sTags[tokenIdx][1], tokNode.get("text")+" vs "+sTags[tokenIdx][1]
            tokNode.set("POS",sTags[tokenIdx][0])
        parse=ET.Element("parse")
        parse.set("parser",options.parse)
        parse.set("tokenizer",options.tokenization)
        for depCounter,(depType,t1,t1idx,t2,t2idx) in enumerate(sDeps):
            depNode=ET.SubElement(parse,"dependency")
            depNode.set("id","clp_%d"%(depCounter+1))
            depNode.set("t1","clt_%d"%t1idx)
            depNode.set("t2","clt_%d"%t2idx)
            depNode.set("type",depType)
            assert unescTok(t1.replace(" ","")).replace("``",'"').replace("''",'"')==tokenization[t1idx-1].get("text").replace(" ",""), "%s: '%s' vs '%s'"%(depNode.get("id"),t1,tokenization[t1idx-1].get("text"))
            assert unescTok(t2.replace(" ","")).replace("``",'"').replace("''",'"')==tokenization[t2idx-1].get("text").replace(" ",""), "%s: '%s' vs '%s'"%(depNode.get("id"),t2,tokenization[t2idx-1].get("text"))
        #Now find the place where to inject the new parse and new tokenization
        #1) find the tokenizations node
        tokenizations=sNode.find("./sentenceanalyses/tokenizations")
        assert tokenizations!=None
        for tokNode in tokenizations:
            if tokNode.get("tokenizer")==options.tokenization:
                raise ValueError("There already exists a tokenization called %s"%options.tokenization)
        tokenizations.append(tokenization)
        #2) find the parses node
        parses=sNode.find("./sentenceanalyses/parses")
        assert parses!=None
        for parseNode in parses:
            if parseNode.get("tokenizer")==options.tokenization and parseNode.get("parser")==options.parse:
                raise ValueError("There already exists a parse node called %s with tokenization %s"%(options.parse,options.tokenization))
        parses.append(parse)
    return

def computeTokens(txtFName,cNode,options,postags=None):
    """For each sentences, returns a list of (beg,end) character offsets of tokens + a list of tokens. If postags are given, use the tokens from there rather than reading the tokenized file"""
    tokenLists=[]
    if postags!=None:
        print >> sys.stderr, "Warning: Taking the tokenization from the .penn file!"
        for taglist in postags:
            tokenList=[tmp[1] for tmp in taglist]
            tokenLists.append(tokenList)
    else:
        f=open(txtFName,"rt")
        for line in f:
            line=line.strip()
            if not line:
                continue
            sTokens=line.split()
            if sTokens[0]=="<s>":
                assert sTokens[-1]=="</s>"
                sTokens=sTokens[1:-1]
            tokenLists.append([unescTok(x) for x in sTokens])
        f.close()

    #tokenLists now has a list of lists of tokens
    #what we really need are the character offsets, though
    print tokenLists
    assert len(tokenLists)==sum(1 for x in cNode.getiterator("sentence"))

    tokenOffsets=[]
    
    for sTokens,sNode in zip(tokenLists,cNode.getiterator("sentence")):
        #print sNode.get("text"), sTokens
        aligned=TA.align(list(sNode.get("text")),sTokens) #returns a list of len(sTokens). Each item is a list of character offsets
        charOffsets=[(x[0],x[-1]) for x in aligned] #just pick the first and last
        #so now charOffsets is a list of pairs (Beg,End) with as many items as there are tokens

        #but better do at least some sanity checks:
        for b,e in charOffsets:
            txt=sNode.get("text")[b:e+1]
            assert txt[0]!=" " and txt[-1]!=" ", "Token with a whitespace in it???"
        tokenOffsets.append(charOffsets)
    return tokenOffsets,tokenLists

#     #now we should yet gather the set of sentence-final token indices
#     f=open(options.dir+"/%s.tokenized"%reportNumber,"rt")
#     tokCounter=0
#     sFinal=set()
#     for line in f:
#         line=line.strip()
#         tokCounter+=len(line.split())
#         sFinal.add(tokCounter-1)
#     f.close()
#     #now sFinal is a set of indices of tokens that end a sentence
#     return rawTxt,charOffsets,sFinal

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
    desc="Given an interaction XML, and the corresponding .txt .txt.penn and .txt.dep files, produces a new XML with the parse injected. You only need to specify the .txt file; .txt.dep and .txt.penn will be taken from the same directory. Writes to stdout."
    usage="python readMcClosky.py [options] > out.xml"
    parser = OptionParser(description=desc,usage=usage)
    parser.add_option("-x", "--xml", dest="xml", action="store", default=None, help="The XML file to which the parse is injected", metavar="XML")
    parser.add_option("-t", "--txt", dest="txt", action="store", default=None, help="The TXT file with tokenization", metavar="TXT")
    parser.add_option("--ignoretokenization", dest="ignoretokenization", action="store_true", default=False, help="The TXT file is not tokenized, so the tokens are taken from the penn file")
    parser.add_option("--nosentences", dest="nosentences", action="store_true", default=False, help="The XML file does not contain sentences; must create them.")
    parser.add_option("--tokenization", dest="tokenization", action="store", default=None, help="Tokenization name to be used.", metavar="name")
    parser.add_option("--parse", dest="parse", action="store", default=None, help="The name under which the parse is injected. No default.", metavar="name")

    (options, args) = parser.parse_args()

    if not options.parse or not options.tokenization:
        raise ValueError("You must specify both parse and tokenization")


    corpus=ET.parse(options.xml).getroot()
    deps=readDepTrees(options.txt+".dep",options)
    postags=readPOSTags(options.txt+".penn",options)
    if options.ignoretokenization:
        offsets,tokens=computeTokens(options.txt,corpus,options,postags)
    else:
        offsets,tokens=computeTokens(options.txt,corpus,options,None)
    inject(corpus,deps,postags,offsets,tokens,options)
    ETUtils.write(corpus,sys.stdout)
    
                        
