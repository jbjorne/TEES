
import sys

from numpy import *
import numpy.linalg as la
import numpy.random as mlab


class KernelDependency(object):
	
	
	def __init__(self, svals, svecs, U = None):
		"""
		svals:	Singular (nonzero) values of the data matrix
		svecs:	Singular vectors of the data matrix
		U:	Right singular vectors. These can be supplied if primal RLS is used.
		"""
		
		#Number of training examples
		self.size = svecs.shape[0]
		
		#Eigenvalues of the kernel matrix
		self.evals = multiply(svals, svals)
		
		self.svals = svals
		self.svecs = svecs
		self.U = U
		
	
	
	def solve(self, regparam):
		"""Train with regularization parameter value regparam"""
		self.regparam = regparam
		self.newevals = 1. / (self.evals + regparam)
		if not self.U == None:
			# Primal input
			self.newevals = multiply(self.svals, self.newevals)
	
	
	
	
	def initializationForNewInput(self, pdm):
		"""Initialize KDE for the new data point.
		pdm:	a column vector of input kernel evaluations between the new input and the training inputs.
		"""
		if self.U == None:
			# Dual input
			self.A = self.svecs * multiply(self.newevals.T, self.svecs.T * pdm)
		else:
			#Primal input
			self.A = self.svecs * multiply(self.newevals.T, self.U * pdm)
	
	def computeErrorForOutputCandidate(self, pdm, kyy):
		"""Initialize KDE for the new data point.
		pdm:	a column vector of output kernel evaluations between the output candidate and the training outputs.
		kyy:	an output kernel evaluation of the output candidate with itself.
		"""
		return kyy - 2 * pdm.T * self.A


