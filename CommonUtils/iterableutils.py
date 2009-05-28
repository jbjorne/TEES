def argmax(iterable,cmp=cmp,reverse=False):
    if reverse:
        multiplier=-1
    else:
        multiplier=1
    currMax=None
    currMaxIdx=None
    for idx,v in enumerate(iterable):
        if idx==0:
            currMax=v
            currMaxIdx=0
        elif multiplier*cmp(currMax,v)<0:
            currMax=v
            currMaxIdx=idx
    if currMaxIdx==None:
        raise ValueError("Empty iterable doesn't have argmax")
    return currMax,currMaxIdx

if __name__=="__main__":
    print argmax([1,2,-1,1,2],reverse=True)
    print argmax([])
        
