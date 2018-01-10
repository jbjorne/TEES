from __future__ import print_function
"""

#Load 10K vectors into memory and 500K vectors total
#both of the following work
wv=lwvlib.load("somefile.bin",10000,500000)
wv=lwvlib.WV.load("somefile.bin",10000,500000)

wv.max_rank_mem
wv.max_rank

#Normalized vector for "koira", gives None if word unknown
wv.w_to_normv(u"koira")

#Index of "koira"
wv[u"koira"] #throws exception if koira not present
wv.get(u"koira") #returns None if koira not present
wv.w_to_dim(u"koira")

#Do I have "koira"?
u"koira" in wv
wv.get(u"koira") is not None
u"koira" in wv.w_to_dim

#7 nearest words as a list [(similarity,word),(similarity,word)]
wv.nearest(u"koira",7)

#The raw vectors in numpy array
wv.vectors

#List of words
wv.words


#Lengths of all vectors in the array (ie wv.max_rank_mem many of them)
wv.norm_constants


"""

import numpy
import mmap
import os
#import StringIO


#so we can write lwvlib.load(...)
def load(*args,**kwargs):
    return WV.load(*args,**kwargs)


class WV(object):

    @staticmethod
    def read_word(inp):
        """
        Reads a single word from the input file
        """
        chars=[]
        while True:
            c = inp.read(1)
            if c == b' ':
                break
            if not c:
                raise ValueError("preliminary end of file")
            chars.append(c)
        wrd=b''.join(chars).strip()
        try:
            return wrd.decode("utf-8")
        except UnicodeDecodeError:
            #Not a utf-8, shoots, what now?
            #maybe I should warn here TODO
            return wrd.decode("utf-8","replace")
        
    
    @classmethod
    def load(cls,file_name,max_rank_mem=None,max_rank=None,float_type=numpy.float32):
        """
        Loads a w2v bin file. 
        `inp` an open file or a file name
        `max_rank_mem` read up to this many vectors into an internal matrix, the rest is memory-mapped
        `max_rank` read up to this many vectors, memory-mapping whatever above max_rank_mem
        `float_type` the type of the vector matrix
        """
        f=open(file_name,"r+b")
        #Read the size line
        try:
            l=f.readline().strip()
            wcount,vsize=l.split()
            wcount,vsize=int(wcount),int(vsize)
        except ValueError:
            raise ValueError("Size line in the file is malformed: '%s'. Maybe this is not a w2v binary file?"%l)

        if max_rank is None or max_rank>wcount:
            max_rank=wcount

        if max_rank_mem is None or max_rank_mem>max_rank:
            max_rank_mem=max_rank

        #offsets: byte offsets at which the vectors start
        offsets=[]
        #words: the words themselves
        words=[]
        #data: the vector matrix for the first max_rank vectors
        data=numpy.zeros((max_rank_mem,vsize),float_type)
        #Now read one word at a time, fill into the matrix
        for idx in range(max_rank_mem):
            words.append(cls.read_word(f))
            offsets.append(f.tell())
            data[idx,:]=numpy.fromfile(f,numpy.float32,vsize)
        #Keep reading, but only remember the offsets
        for idx in range(max_rank_mem,max_rank):
            words.append(cls.read_word(f))
            offsets.append(f.tell())
            f.seek(vsize*4,os.SEEK_CUR) #seek over the vector (4 is the size of float32)
        fm=mmap.mmap(f.fileno(),0)
        return cls(words,data,fm,offsets)
    
    def __init__(self,words,vector_matrix,mm_file,offsets):
        """
        `words`: list of words
        `vector_matrix`: numpy matrix
        `mm_file`: memory-mapped .bin file with the vectors
        `offsets`: for every word, the offset at which its vector starts
        """
        self.vectors=vector_matrix #Numpy matrix
        self.words=words #The words to go with them
        self.w_to_dim=dict((w,i) for i,w in enumerate(self.words))
        self.mm_file=mm_file
        self.offsets=offsets
        self.max_rank_mem,self.vsize=self.vectors.shape
        #normalization constants for every row
        self.norm_constants=numpy.linalg.norm(x=self.vectors,ord=None,axis=1)#.reshape(self.max_rank,1) #Column vector of norms
        self.size = self.vectors[0].size
    
    def __contains__(self,wrd):
        return wrd in self.w_to_dim

    def get(self,wrd,default=None):
        """Returns the vocabulary index of wrd or default"""
        return self.w_to_dim.get(wrd,default)

    def __getitem__(self,wrd):
        return self.w_to_dim[wrd]
        
    def w_to_normv(self,wrd):
        #Return a normalized vector for wrd if you can, None if you cannot
        wrd_dim=self.w_to_dim.get(wrd)
        if wrd_dim is None:
            return None #We know nothing of this word, sorry
        if wrd_dim<self.max_rank_mem: #We have the vector loaded in memory
            return self.vectors[wrd_dim]/self.norm_constants[wrd_dim]
        else: #We don't have the vector loaded in memory, grab it from the file
            vec=numpy.fromstring(self.mm_file[self.offsets[wrd_dim]:self.offsets[wrd_dim]+self.vsize*4],numpy.float32,self.vsize).astype(self.vectors.dtype)
            vec/=numpy.linalg.norm(x=vec,ord=None)
            return vec
        
    def nearest(self,wrd,N=10):
        wrd_vec_norm=self.w_to_normv(wrd)
        if wrd_vec_norm is None:
            return
        sims=self.vectors.dot(wrd_vec_norm)/self.norm_constants #cosine similarity to all other vecs
        #http://stackoverflow.com/questions/6910641/how-to-get-indices-of-n-maximum-values-in-a-numpy-array
        return sorted(((sims[idx],self.words[idx]) for idx in numpy.argpartition(sims,-N-1)[-N-1:]), reverse=True)[1:]

    def similarity(self,w1,w2):
        """
        Return similarity of two words
        """
        w1_norm=self.w_to_normv(w1)
        w2_norm=self.w_to_normv(w2)
        if w1_norm is None or w2_norm is None:
            return
        return numpy.dot(w1_norm,w2_norm)

    def analogy(self,src1,target1,src2,N=10):
        """
        src1 is to target1 as src2 is to ____
        """
        src1nv=self.w_to_normv(src1)
        target1nv=self.w_to_normv(target1)
        src2nv=self.w_to_normv(src2)
        if None in (src1nv,target1nv,src2nv):
            return None
        target2=src2nv+target1nv-src1nv
        target2/=numpy.linalg.norm(target2,ord=None)
        sims=self.vectors.dot(target2)/self.norm_constants #cosine similarity to all other vecs
        return sorted(((sims[idx],self.words[idx]) for idx in numpy.argpartition(sims,-N-1)[-N-1:]), reverse=True)[1:]
