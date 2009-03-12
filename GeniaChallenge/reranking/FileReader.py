#Utilities for reading in the files used by the
#RLS software package

from optparse import OptionParser
import sys
import re
from scipy import sparse
from numpy import float64
from numpy import zeros
from numpy import mat

def error(message):
    """Prints a error message to stderr"""
    sys.stderr.write("Error when reading in data file\n")
    sys.stderr.write(message)
    
#error = sys.stderr.write

def split_instance_line(line):
    """Splits an instance line to attributes and comment."""
    comment = ""
    #The #-character begins the optional comment section of a line
    cstart = line.find("#")
    if cstart != -1:
        comment = line[cstart:]
        line = line[:cstart]
    line = line.strip().split()
    if len(line) == 0:
        error("Error: empty line in the data file")
        sys.exit(-1)
    #Rest of the line contains attribute:value pairs
    return line, comment

def readQids(source):
    qids = []
    for line in source:
        qid = line.strip()
        qids.append(qid)
    return qids

def readLabelFile(source):
    outspace_dim = 0
    linecounter = 0
    nonzeros = 0
    all_outputs = []
    for line in source:
        linecounter+=1
        line = line.strip()
        comment = ""
        cstart = line.find("#")
        if cstart != -1:
            comment = line[cstart:]
            line = line[:cstart]
        line = line.split()
        previous = 0
        outputs = []
        for att_val in line:
            if len(att_val.split(":")) != 2:
                error("Error: output:value pair %s on line %d is not well-formed in the output file\n" %(att_val, linecounter))
                sys.exit(-1)
            index, value = att_val.split(":")
            try:
                index = int(index)
                value = float(value)
                outputs.append((index, value))
            except ValueError:
                error("Error: output:value pair %s on line %d is not well-formed\n" %(att_val, linecounter))
                sys.exit(-1)
            if not index > previous:
                error("Error: line %d output indices must be in ascending order\n" %(linecounter))
                sys.exit(-1)
            previous = index
            if index > outspace_dim:
                outspace_dim = index
            if value != 0.:
                nonzeros += 1
        all_outputs.append(outputs)
    return all_outputs, outspace_dim

def readNewStyleInstanceFile(source, subset=None):
    """Reads in the data and checks that the input file is correctly formatted. Additionally
    1. Calculates the number of examples
    2. Calculates the dimensionality of the feature space
    3. Calculates the number of outputs used
    4. Checks whether the data is sparse
    This information is returned to the caller.
    All of the data is read into memory"""
    #Regular expressions could be used also, but it is not any faster, main
    #overhead is from iterating through lines.

    #some interesting statistics are calculated
    labelcount = None
    linecounter = 0
    instancecounter = 0
    feaspace_dim = 0
    nonzeros = 0
    #Features and comments are returned to the caller 
    #The indexing, with respect to the instances, is the same in all the lists.
    all_features = []
    all_comments = []
    #Each line in the source represents an instance
    for line in source:
        linecounter += 1
        #Empty lines and commented lines are passed over
        if len(line.strip()) == 0 or line[0] == '#':
            continue
        elif subset!= None and instancecounter not in subset:
            instancecounter += 1
            continue
        instancecounter += 1
        attributes, comment = split_instance_line(line)
        #Either all instances must have a qid, or none of them
        #We gather the comments, in case caller is interested in them
        all_comments.append(comment)
        previous = 0
        features = []
        #Attributes indices must be positive integers in an ascending order,
        #and the values must be real numbers.
        for att_val in attributes:
            if len(att_val.split(":")) != 2:
                error("Error: feature:value pair %s on line %d is not well-formed\n" %(att_val, linecounter))
                sys.exit(-1)
            index, value = att_val.split(":")
            try:
                index = int(index)
                value = float(value)
                features.append((index, value))
            except ValueError:
                error("Error: feature:value pair %s on line %d is not well-formed\n" %(att_val, linecounter))
                sys.exit(-1)
            if not index > previous:
                error("Error: line %d features must be in ascending order\n" %(linecounter))
                sys.exit(-1)
            previous = index
            if index > feaspace_dim:
                feaspace_dim = index
            if value != 0.:
                nonzeros += 1
        all_features.append(features)
    #That's all folks
    return all_features, all_comments, feaspace_dim, nonzeros      


    
def buildSparseDataMatrix(features, feaspace_dim, bias=False):
    """Builds a sparse matrix representation of the read data"""
    if bias:
        X = sparse.lil_matrix((feaspace_dim+1, len(features)), dtype=float64)
    else:
        X = sparse.lil_matrix((feaspace_dim, len(features)), dtype=float64)
    for i, instance in enumerate(features):
        if bias:
            X[feaspace_dim, i] = 1.
        for index, value in instance:
            #Indices range from 1..n in the data file, and from 0...n-1 in
            #the matrix representation
            if index <= feaspace_dim:
                index -= 1
                X[index, i] = value
    return X


def buildLabelMatrix(labels, dimensionality):
    """Builds a label matrix from the read data"""
    Y = mat(zeros((len(labels), dimensionality), dtype = float64))
    for i, labelset in enumerate(labels):
        for j, label in labelset:
            Y[i,j-1] = label
    return Y

def getLabels(source, dim = None):
    outputs, dimensionality = readLabelFile(source)
    if dim:
        assert dim>0
        dimensionality = dim
    Y = buildLabelMatrix(outputs, dimensionality)
    return Y, dimensionality
    

def buildDictionary(features, bias=False):
    """A dictionary representation of the data. Usually the sparse matrices
    should be rather favored for performance reasons."""
    instances = []
    for fset in features:
        dictionary = {}
        if bias:
            dictionary["$$BIAS$$"] = 1.
        for index, value in fset:
            dictionary[index] = value
        instances.append(dictionary)
    return instances

def buildDenseDataMatrix(features, feaspace_dim, bias=False):
    """A dense data matrix representation of the data is built."""
    if bias:
        X = mat(zeros((feaspace_dim+1, len(features)), dtype=float64))
    else:
        X = mat(zeros((feaspace_dim, len(features)), dtype=float64))
    for i, instance in enumerate(features):
        if bias:
            X[feaspace_dim, i] = 1.
        for index, value in instance:
            #Indices range from 1..n in the data file, and from 0...n-1 in
            #the matrix representation
            if index <= feaspace_dim:
                index -= 1
                X[index, i] = value
    return X


def readSparseMatrix(source, subset = None, dimensionality = None,bias=False):
    """Read a sparse matrix representation of the data from an
    open file-like object that is provided"""
    features, comments, feaspace_dim, nonzeros = readNewStyleInstanceFile(source, subset)
    if dimensionality:
        feaspace_dim = dimensionality
    assert len(features) == len(comments)
    X = buildSparseDataMatrix(features, feaspace_dim,bias)
    return X, comments, feaspace_dim

def readDenseMatrix(source, subset = None, dimensionality = None, bias = False):
    features, comments, feaspace_dim, nonzeros = readNewStyleInstanceFile(source, subset)
    if dimensionality:
        feaspace_dim = dimensionality
    assert len(features)==len(comments)
    X = buildDenseDataMatrix(features, feaspace_dim, bias)
    return X, comments, feaspace_dim


def readModelFile(path):
    """Reads a model file that represents a trained RLS"""
    f = open(path)
    kernel = f.readline().strip().split()[-1]
    kparams = f.readline().strip().split()[-1]
    form = f.readline().strip().split()[-1]
    dim1 = int(f.readline().strip().split()[-1])
    dim0 = int(f.readline().strip().split()[-1])
    bvectors = None
    bvline = f.readline().strip().split()
    if bvline[1] != "all":
        bvline.pop(0)
        bvectors = [int(x) for x in bvline]
    A = mat(zeros((dim0,dim1),dtype=float64))
    for line in f:
        line = line.strip().split()
        column = int(line.pop(0))
        for row_val in line:
            row_val = row_val.split(":")
            row = int(row_val[0])
            value = float(row_val[1])
            A[row,column]=value
    return kernel, kparams, form, A, bvectors

def readBvectors(path):
    """Reads in the basis-vectors file"""
    f = open(path)
    bvectors = f.readline().strip().split()
    bvectors = [int(x) for x in bvectors]
    return bvectors

def readFolds(path, trainsetsize):
    """Reads the fold splits from a file"""
    f = open(path)
    #values = set([])
    folds = []
    for i, line in enumerate(f):
        #We allow comments starting with #
        cstart = line.find("#")
        if cstart != -1:
            comment = line[cstart:]
            line = line[:cstart]
        fold = []
        foldset = set([])
        line = line.strip().split()
        for x in line:
            try:
                index = int(x)
            except ValueError:
                sys.stderr.write("ERROR: malformed index on line %d in the fold file: %s\n" %(i+1, x))
                sys.exit(0)
            if index <= 0:
                sys.stderr.write("ERROR: non-positive index on line %d in the fold file: %d\n" %(i+1, index))
                sys.exit(0)
            #if index-1 in values:
            #    sys.stderr.write("ERROR: duplicate index on line %d in the fold file: %d\n" %(i+1, index))
            #    sys.exit(0)
            elif index > trainsetsize:
                sys.stderr.write("ERROR: index larger than number of training examples in the fold file: %d\n" %index)
                sys.exit(0)
            index = index-1
            if index in foldset:
                sys.stderr.write("ERROR: duplicate index on line %d in the fold file: %d\n" %(i+1, index+1))
                sys.exit(0)
            #values.add(index)
            fold.append(index)
            foldset.add(index)
        folds.append(fold)
    #index_set = set(range(0,len(values)))
    #If some indices are missing from the folds
    #if index_set != values:
    #    sys.stderr.write("Error: malformed fold file. Each row in the fold file corresponds to a fold, where the indices of the training instances belonging to the fold are seperated by a whitespace. Each training instance must belong to one of the folds.\n")
    #    sys.exit(0)
    f.close()
    return folds
    
        
