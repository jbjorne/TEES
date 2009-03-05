from __future__ import division
import sys
try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET

def docStats(docNode):
    return len(docNode) #number of sentences in the document

def sentStats(sNode):
    #1) number of tokens
    for toksNode in sNode.getiterator("tokenization"):
        if toksNode.get("tokenizer","split-Charniak-Lease"):
            break
    else:
        assert False
    tokenCount=len(toksNode)
    otherEntCount=0
    nameEntCount=0
    eTypeCounts={} #key: type  val: count of entities
    for eNode in sNode.getiterator("entity"):
        if eNode.get("isName")=="True":
            nameEntCount+=1
        elif eNode.get("type")!="neg":
            otherEntCount+=1
            eType=eNode.get("type")
            eTypeCounts[eType]=eTypeCounts.get(eType,0)+1

    iTypeCounts={} #key: type  val: count of interactions
    for iNode in sNode.getiterator("interaction"):
        iType=iNode.get("type")
        iTypeCounts[iType]=iTypeCounts.get(iType,0)+1
    return tokenCount,nameEntCount,otherEntCount,eTypeCounts,iTypeCounts

def countDictUpdate(masterDict,smallDict):
    for k,v in smallDict.items():
        masterDict[k]=masterDict.get(k,0)+v

def prettyPrintDict(d):
    keys=d.keys()
    keys.sort()
    total=sum(v for v in d.values())
    return " ".join("%s: %.1f%%"%(k,d[k]/total*100) for k in keys)

def allSentStats(treeNode):
    mastereTypeCounts={}
    masteriTypeCounts={}
    masterTokCount=0
    masterNameEntCount=0
    masterTrigEntCount=0
    sCount=0
    for sNode in treeNode.getiterator("sentence"):
        sCount+=1
        tokCount,nameEntCount,trigEntCount,eTypeCounts,iTypeCounts=sentStats(sNode)
        masterTokCount+=tokCount
        masterNameEntCount+=nameEntCount
        masterTrigEntCount+=trigEntCount
        countDictUpdate(mastereTypeCounts,eTypeCounts)
        countDictUpdate(masteriTypeCounts,iTypeCounts)
    print "Tokens/sentence","%.0f"%(masterTokCount/sCount)
    print "Entities/tokens:","%.3f"%((masterNameEntCount+masterTrigEntCount)/masterTokCount)
    print "Entity distribution: %.0f%% name %.0f%% trigger"%(masterNameEntCount/(masterNameEntCount+masterTrigEntCount)*100,masterTrigEntCount/(masterNameEntCount+masterTrigEntCount)*100)
    print
    print "ETypes",prettyPrintDict(mastereTypeCounts)
    print
    print "ITypes",prettyPrintDict(masteriTypeCounts)
        
        

if __name__=="__main__":
    desc="Basic stats. Feed an interaction XML to stdin"
#    (options, args) = parser.parse_args()
    tree=ET.parse(sys.stdin).getroot()
    allSentStats(tree)
