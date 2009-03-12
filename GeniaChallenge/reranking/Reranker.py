import LinearKernel
import KernelDependency
import FileReader
import SparseModule
from numpy import mat
from numpy import zeros
from numpy import float64
from math import exp

trainfile = "train_inputs"
testfile = "devel_inputs"
bvecfile = "bvectors"
regparam = 1

def dotProduct(dict1, dict2):
    summa = 0
    for key in dict1.keys():
        if key in dict2:
            summa += dict1[key]*dict2[key]
    return summa

def gaussian(dict1, dict2, gamma):
    total = 0
    common = set(dict1.keys()).intersection(set(dict2.keys()))
    for key in dict1:
        if key in common:
            total -= (dict1[key]-dict2[key])**2
        else:
            total -= (dict1[key])**2
    for key in dict2:
        if not key in common:
            total -= dict2[key]**2
    return exp(gamma*total)

class KDLearner(object):

    def __init__(self, trainfile, testfile, bvecfile, train_outputs):
        kernel = LinearKernel.Kernel()
        kernel.setVerbose(True)
        f = open(trainfile)
        print "Reading in training examples"
        kernel.readTrainingInstances(f)
        bvectors = FileReader.readBvectors(bvecfile)
        print "Building kernel matrix"
        kernel.buildSparseTrainingKernelMatrix(bvectors, "foo")
        f.close()
        f = open(testfile)
        print "Building test kernel matrix"
        kernel.readTestInstances(f)
        kernel.buildSparseTestKernelMatrix(bvectors, "foo")
        f.close()
        K_r = kernel.getSparseTrainingKernelMatrix()
        K_test = kernel.getSparseTestKernelMatrix()
        print "Decomposing kernel matrix"
        svals, evecs, U, Z = SparseModule.decomposeSubsetKM(K_r, bvectors)
        print "Solving kernel dependency estimation"
        KD = KernelDependency.KernelDependency(svals, evecs, U)
        self.KD = KD
        self.H = Z.T*K_test
        self.train_outputs = train_outputs

    def solve(self, regparam):
        self.KD.solve(regparam)

    def score(self, candidates, i):
        scores = []
        self.KD.initializationForNewInput(self.H[:,i])
        for candidate in candidates:
            kyy = gaussian(candidate, candidate, 100)
            #kyy = dotProduct(candidate, candidate)
            kyy = 1.
            pdm = mat(zeros((len(self.train_outputs), 1), dtype = float64))
            for i in range(len(self.train_outputs)):
                pdm[i,0] = gaussian(candidate, self.train_outputs[i],100)
                #pdm[i,0] = dotProduct(candidate, self.train_outputs[i])
            scores.append(self.KD.computeErrorForOutputCandidate(pdm, kyy))
        return scores
