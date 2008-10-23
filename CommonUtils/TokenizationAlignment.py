# WARNING: NOT COMPLETE - MISMATCHES ARE NOT HANDLED!!!

# Here is a function that receives two sequences of texts
# and produces a mapping from the second to the first sequence
# ignoring whitespace
#
# s1:   0   1   2     3    4
#      abcd e   fgh   ijk  lmno
# s2:   0  1  2  3     4   5   6
#      ab  cd e  fghi  jk  lmn o
#
# gives
#
# [[0],[0],[1],[2,3],[3],[4],[4]]
# so you get as many items as there are in s2
# and each item is a list of items from s1 that are overlaping with the particular item from s2
#
# you can further specify a misalignFunc(s1idx,s1charOff,s1,s2idx,s2charOff,s2) which returns:
#
# 1 advance s1
# 2 advance s2
# 3 advance both s1 and s2
# None - report error and bail out
#
# the default misalignFunc bails out on misalignments

import sys

def defaultMisalign(s1idx,s1charOff,s1,s2idx,s2charOff,s2):
    return None

def indexIterator(seq):
    seqIdx=0
    while seqIdx<len(seq):
        txtIdx=0
        while txtIdx<len(seq[seqIdx]):
            yield seqIdx,txtIdx
            txtIdx+=1
        seqIdx+=1

    
def align(s1,s2,skipSpace=True,misalignFunc=defaultMisalign):
    result=[[] for i in range(len(s2))]
    loaded=False
    s1Iter=indexIterator(s1)
    s2Iter=indexIterator(s2)
    while True:
        try: #This one guards for end-of-sequence
            #Get the next index to compare
            if not loaded:
                if skipSpace:
                    while True:
                        s1idx,s1charOff=s1Iter.next()
                        if not s1[s1idx][s1charOff].isspace():
                            break
                    while True:
                        s2idx,s2charOff=s2Iter.next()
                        if not s2[s2idx][s2charOff].isspace():
                            break
                else: #no space skipping, just get the next item
                    s1idx,s1charOff=s1Iter.next()
                    s2idx,s2charOff=s2Iter.next()
                loaded=True
            #now we have two characters to compare
            if s1[s1idx][s1charOff]==s2[s2idx][s2charOff]: #all is fine
                #do I need to add s1idx to the result?
                if len(result[s2idx])==0 or result[s2idx][-1]!=s1idx:
                    result[s2idx].append(s1idx)
                loaded=False #This character pair was consumed
            else: #oops, a mismatch!
                action=misalignFunc(s1idx,s1charOff,s1,s2idx,s2charOff,s2)
                if action==1 or action==3:
                    s1idx,s1charOff=s1Iter.next()
                if action==2 or action==3:
                    s2idx,s2charOff=s2Iter.next()
                if action==None:
                    print >> sys.stderr, "Mismatch: '%s'<>'%s'  in (%s)<>(%s)"%(s1[s1idx][s1charOff:],s2[s2idx][s2charOff:],s1[s1idx],s2[s2idx])
                    raise ValueError("Mismatch")
        except StopIteration:
            #now need to figure out whether it was s1 or s2 who fired
            break
    return result
                

if __name__=="__main__":
    print >> sys.stderr, "This module defines the function align(). Import it and use it in your code."
    print align("abcd e   fgh   ijk  lmno".split(),"ab  cd e  fghi  jk  lmn o".split())
