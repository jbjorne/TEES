from optparse import OptionParser
import TokenizationAlignment as TA #this one comes from CommonUtils

unescapeDict={'-LRB-':'(',
              '-RRB-':')',
              '-LSB-':'[',
              '-RSB-':']',
              '-LCB-':'{',
              '-RCB-':'}'
              }
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
    desc="Reads the tokenization and parses from a bunch of shared task files in a given directory."
    usage="python readTokenization.py [options] documentNumber1 documentNumber2 documentNumber3 ..."
    parser = OptionParser(description=desc,usage=usage)
    parser.add_option("-d", "--dir", dest="dir", action="store", default=".", help="The directory in which the .dep .tokenized .a1 .a2 files can be found.", metavar="DIR")

    (options, args) = parser.parse_args()

    
    for num in args:
        rawTxt,charOffsets,sFinal=computeTokens(num,options)
        printSeqClassData(num,charOffsets,rawTxt,sFinal,options)

                        
