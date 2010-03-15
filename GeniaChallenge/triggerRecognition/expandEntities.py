try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET

try:
    import psyco
    psyco.full()
except:
    pass
from optparse import OptionParser
import cElementTreeUtils as ETUtils
import sys
import re

def buildTriggerList(treeNode):
    s=set()
    for eNode in treeNode.getiterator("entity"):
        if eNode.get("isName")=="False":
            s.add(eNode.get("text"))
    l=list(s)
    l.sort()
    for x in l:
        print x

def readTriggerList(f):
    txts=[] #texts of the triggers
    for line in f:
        line=line.strip()
        if not line:
            continue
        txts.append(line)
    return txts

def extend(eNode,gztrTxts,sText):
    trigTxt=eNode.get("text")
    trigTxtRe=re.compile(re.escape(trigTxt),re.I)
    b,e=eNode.get("charOffset").split("-")
    b,e=int(b),int(e)+1
    assert sText[b:e]==trigTxt, sText[b:e]+"     "+trigTxt

    extensions=[] #list of newB,newE pairs
    #1) find the triggers that could match here
    for trigCand in gztrTxts:
        if len(trigCand)<=len(trigTxt):
            continue #cannot subsume
        match=trigTxtRe.search(trigCand)
        if match:
            #The trigger candidate subsumes trigTxt
            #does it also match the surrounding text?
            prefix=trigCand[:match.start()]
            suffix=trigCand[match.end():]
            assert suffix or prefix
            assert (prefix+trigTxt+suffix).lower()==trigCand.lower()
            if len(prefix)>0:
                prefixMatch=re.match(re.escape(prefix)+"$",sText[:b],re.I)
                if not prefixMatch:
                    continue #did not match
            if len(suffix)>0:
                suffixMatch=re.match("^"+re.escape(suffix),sText[e:],re.I)
                if not suffixMatch:
                    continue
            #Okay, we have a possible extension!
            print >> sys.stderr, trigTxt+"--->"+trigCand+"   "+sText
            newB=b-len(prefix)
            newE=e+len(suffix)
            assert sText[newB:newE].lower()==trigCand.lower()
            extensions.append((newB,newE))
    #Now pick the longest extension
    extensions.sort(reverse=True,cmp=lambda a,b:cmp(a[1]-a[0],b[1]-b[0]))
    if len(extensions)>1:
        assert extensions[0][1]-extensions[0][0] >= extensions[-1][1]-extensions[-1][0]
    if len(extensions)>0:
        eNode.set("charOffset","%d-%d"%(extensions[0][0],extensions[0][1]-1)) #set the new offset
        eNode.set("text",sText[extensions[0][0]:extensions[0][1]])

def subsumes(e1,e2):
    """e1 is subsumed by e2?"""
    e1b,e1e=e1.get("charOffset").split("-")
    e1b,e1e=int(e1b),int(e1e)
    e2b,e2e=e2.get("charOffset").split("-")
    e2b,e2e=int(e2b),int(e2e)
    if e1b>=e2b and e1e<=e2e:
        return True
    else:
        return False
    
def removeSubsumedEntities(sNode):
    toKillIds=[]
    entities=[eNode for eNode in sNode.getiterator("entity")]
    for e1Idx in range(len(entities)):
        for e2Idx in range(e1Idx+1,len(entities)):
            if subsumes(entities[e1Idx],entities[e2Idx]):
                toKillIds.append(e1Idx)
                print >> sys.stderr, "Removing '%s' subsumed by '%s'"%(entities[e1Idx].get("text"),entities[e2Idx].get("text"))
            elif subsumes(entities[e2Idx],entities[e1Idx]):
                toKillIds.append(e2Idx)
                print >> sys.stderr, "Removing '%s' subsumed by '%s'"%(entities[e2Idx].get("text"),entities[e1Idx].get("text"))
    for idx in toKillIds:
        sNode.remove(entities[idx])
    
if __name__=="__main__":
    desc="Extends trigger entities using a dictionary of previously seen trigger texts"
    parser = OptionParser(description=desc)
    parser.add_option("--buildgztr",dest="buildgztr",action="store_true",default=False,help="Output to stdout the list of all seen triggers")
    parser.add_option("--gztr",dest="gztr",action="store",default=None,help="Use this trigger list to expand the entities")

    (options, args) = parser.parse_args()

    tree=ET.parse(sys.stdin).getroot()

    if options.buildgztr:
        buildTriggerList(tree)
        sys.exit()

    if options.gztr:
        f=open(options.gztr,"rt")
        gztrTxts=readTriggerList(f)
        f.close()

        for sNode in tree.getiterator("sentence"):
            for eNode in sNode.getiterator("entity"):
                extend(eNode,gztrTxts,sNode.get("text"))
            removeSubsumedEntities(sNode)
        
        ETUtils.write(tree,sys.stdout)
