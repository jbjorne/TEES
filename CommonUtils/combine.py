"""
Combinations from multiple sequences

Source: ASPN: Python Cookbook
Title: Generating combinations of objects from multiple sequences
Submitter: David Klaffenbach (other recipes)
Last Updated: 2004/08/29
Version no: 1.0
Category: Algorithms

Description:

The function combine takes multiple sequences and creates a list in which
each item is constructed from items from each input sequence, and all possible
combinations are created. If that description is confusing, look at the 
example in the docstring. It's a pretty simple transformation. The function 
xcombine is similar, but returns a generator rather than creating the output 
all at once.
"""

def combine(*seqin):
    '''returns a list of all combinations of argument sequences.
    for example: combine((1,2),(3,4)) returns
    [[1, 3], [1, 4], [2, 3], [2, 4]]'''
    def rloop(seqin,listout,comb):
        '''recursive looping function'''
        if seqin:                       # any more sequences to process?
            for item in seqin[0]:
                newcomb=comb+[item]     # add next item to current comb
                # call rloop w/ rem seqs, newcomb
                rloop(seqin[1:],listout,newcomb)
        else:                           # processing last sequence
            listout.append(comb)        # comb finished, add to list
    listout=[]                      # listout initialization
    rloop(seqin,listout,[])         # start recursive process
    return listout

def xcombine(*seqin):
    '''returns a generator which returns combinations of argument sequences
    for example xcombine((1,2),(3,4)) returns a generator; calling the next()
    method on the generator will return [1,3], [1,4], [2,3], [2,4] and
    StopIteration exception.  This will not create the whole list of 
    combinations in memory at once.'''
    def rloop(seqin,comb):
        '''recursive looping function'''
        if seqin:                   # any more sequences to process?
            for item in seqin[0]:
                newcomb=comb+[item]     # add next item to current combination
                # call rloop w/ remaining seqs, newcomb
                for item in rloop(seqin[1:],newcomb):   
                    yield item          # seqs and newcomb
        else:                           # processing last sequence
            yield comb                  # comb finished, add to list
    return rloop(seqin,[])