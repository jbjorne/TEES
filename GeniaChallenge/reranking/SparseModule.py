from numpy.linalg import cholesky
from numpy.linalg import inv
import Decompositions
from numpy.linalg.linalg import LinAlgError
#Module for sparse learning with the empirical feature map

def decomposeSubsetKM(K_r, bvectors):
    K_rr = getBVKM(K_r, bvectors)
    try:
        C = cholesky(K_rr)
    except LinAlgError:
        print "Warning: chosen basis vectors not linearly independent"
        print "Shifting the diagonal of kernel matrix"
        shiftKmatrix(K_r, bvectors)
        K_rr = getBVKM(K_r, bvectors)
        C = cholesky(K_rr)
    C_T_inv = inv(C.T)
    H = (K_r).T*C_T_inv
    svals, evecs, U = Decompositions.decomposeDataMatrix(H.T)
    #Z = C_T_inv*U
    return svals, evecs, U, C_T_inv
    
def getBVKM(K_r, bvectors):
    #returns the kernel matrix for the basis vectors
    return K_r[:,bvectors]

def shiftKmatrix(K_r, bvectors, shift = 0.000000001):
    #If the chosen subset is not linearly independent, we
    #enforce this with shifting the kernel matrix
    for i, j in enumerate(bvectors):
        K_r[i,j] += shift

