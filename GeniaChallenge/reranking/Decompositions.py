

import sys

from numpy import *
import numpy.linalg as la

SMALLEST_EVAL = 0.0000000001

def decomposeDataMatrix(X):
	svecs, svals, U = la.svd(X.T, full_matrices = 0)
	svals, evecs = mat(svals), mat(svecs)
	evals = multiply(svals, svals)
	
	maxnz = min(X.shape[0], X.shape[1])
	nz = 0
	for l in range(maxnz):
		if evals[0, l] > SMALLEST_EVAL:
			nz += 1
	rang = range(0, nz)
	evecs = evecs[:, rang]
	svals = svals[:, rang]
	U = U[rang]
	return svals, evecs, U


def decomposeKernelMatrix(K):
	evals, evecs = la.eigh(K)
	evals, evecs = mat(evals), mat(evecs)
	nz = 0
	maxnz = K.shape[0]
	for l in range(maxnz):
		if evals[0, l] > SMALLEST_EVAL:
			nz += 1
	rang = range(maxnz - nz, maxnz)
	evecs = evecs[:, rang]
	evals = evals[:, rang]
	svals = sqrt(evals)
	return svals, evecs
	

