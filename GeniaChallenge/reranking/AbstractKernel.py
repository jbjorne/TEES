#The base class which all kernels should inherit.
#Contains some default functionality which can
#be overriden by the inheriting classes.
#
#The kernel classes have responsibility for reading in the
#data files and making predictions given the learned model,
#to allow the handling of uncommon types of data and optimization
#tricks.
#
#Many of the methods terminate with error messages, if
#their default behaviour is accessed.
import sys

class AbstractKernel(object):
    """The abstract base class from which all kernel implementations
    should be derived. It is the responsibility of a kernel to read
    in the instances, to make it possible to read arbitrary types
    of data files in. Default behaviour for reading files in the
    standard format can be inherited from this base class."""

    def __init__(self):
        """As a default behaviour, reads in a dictionary of features,
        a matrix of output values, possible query ids and the
        dimensonality of the feature space fro datasource"""
        from FileReader import readSparseMatrix
        self.reader = readSparseMatrix
        self.train_km = None
        self.test_km = None
        self.sparse_train_km = None
        self.sparse_test_km = None
        self.primal_train = None
        self.primal_test = None
        self.verbose = False
        self.name = "abstract kernel base class"

    def setVerbose(self, verbosity):
        """Defines whether the kernel module should be verbose or not"""
        self.verbose = verbosity

    def supportPrimal(self):
        """Returns whether the module can return the explicit feature
        mapping of the data instead of the kernel matrix"""
        return False

    def getDimensions(self):
        """Returns statistics related to the data. This method should not
        be called unless the kernel supports the primal option."""
        return self.train_X.shape[0], self.train_X.shape[1]

        
    def readTrainingInstances(self, datasource, reader = None):
        """Reads in the training data. Datasource is an open file-like object,
        reader is the function used for reading the data."""
        if reader == None:
            reader = self.reader
        self.train_X, self.train_comments, self.feaspace_dim = reader(datasource)

    def readTestInstances(self, datasource, reader = None):
        """Reads in the test data. Datasource is an open file-like object,
        reader is the function used for reading the data."""
        if reader == None:
            reader = self.reader
        self.test_X, self.test_comments, foo = reader(datasource)

    def buildTrainingKernelMatrix(self, parameters):
        """Builds a kernel matrix from the training data"""
        sys.stderr.write("ERROR: routine buildTrainingKernelMatrix not implemented\n")
        sys.exit(0)

    def buildTestKernelMatrix(self, parameters):
        """Builds a kernel matrix between training and test data"""
        sys.stderr.write("ERROR: routine buildTestKernelMatrix not implemented\n")
        sys.exit(0)

    def buildSparseTrainingKernelMatrix(self, subset, parameters):
        """Builds a sparse kernel matrix, containing only the rows in the subset"""
        sys.stderr.write("ERROR: routine buildSparseTrainingKernelMatrix not implemented\n")
        sys.exit(0)

    def buildSparseTestKernelMatrix(self, subset, parameters):
        """Builds a sparse kernel matrix between training and test data, containing only the rows in the subset"""
        sys.stderr.write("ERROR: routine buildSparseTrainingKernelMatrix not implemented\n")
        sys.exit(0)

    def buildPrimalDataMatrix(self, parameters):
        """Builds the data matrix containing the explicit feature mapping of the training data points"""
        sys.stderr.write("ERROR: routine buildPrimalDataMatrix not implemented\n")
        sys.exit(0)

    def buildPrimtaTestMatrix(self, parameters):
        """Builds the data matrix containing the explicit feature mapping of the test data points"""
        sys.stderr.write("ERROR: routine buildPrimalTestMatrix not implemented\n")

    def getPrimalTrainingMatrix(self):
        """Returns the data matrix of mapped images of the data points"""
        if self.primal_train == None:
            sys.stderr.write("ERROR: No mapping of the data points available\n")
        else:
            return self.primal_train

    def getPrimalTestMatrix(self):
        """Returns the data matrix of mapped images of the data points"""
        if self.primal_test == None:
            sys.stderr.write("ERROR: No mapping of the data points available\n")
        else:
            return self.primal_test
        
    def getTrainingKernelMatrix(self):
        """Returns the training kernel matrix"""
        if self.train_km == None:
            sys.stderr.write("ERROR: No training kernel matrix built\n")
            sys.exit(0)
        else:
            return self.train_km

    def getTestKernelMatrix(self):
        """Returns the test kernel matrix"""
        if self.test_km == None:
            sys.stderr.write("ERROR: No test kernel matrix built\n")
            sys.exit(0)
        else:
            return self.test_km

    def getSparseTrainingKernelMatrix(self):
        if self.sparse_train_km == None:
            sys.stderr.write("ERROR: No sparse training kernel matrix built\n")
            sys.exit(0)
        else:
            return self.sparse_train_km

    def getSparseTestKernelMatrix(self):
        if self.sparse_test_km == None:
            sys.stderr.write("ERROR: No sparse test kernel matrix built\n")
            sys.exit(0)
        else:
            return self.sparse_test_km

    def getW(self, A):
        """Recover the coefficients of the normal vector of the separating
        hyperplane from the learned A-vector. Implemented by linearizable
        kernels only"""
        sys.stderr.write("Error: getW()-method of a non-linearizable kernel called\n")
        sys.exit(0)

    def primalPredict(self, W):
        """Make predictions given the coefficients of the separating
        hyperplane in the space where the feature vectors are mapped to.
        Meaningful only for linearizable kernels."""
        return self.primal_test.T*W

    def dualPredict(self, A):
        """Make predictions given the A-vector"""
        return self.test_km.T*A

    def getFeaspaceDim(self):
        return self.feaspace_dim

    def getName(self):
        return self.name
        

    
