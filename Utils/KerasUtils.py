import numpy as np
import tensorflow as tf
import random as rn
from keras import backend as K
import sys, os

def setRandomSeed(seed):
    print >> sys.stderr, "Setting random seed as", seed
    # The below is necessary in Python 3.2.3 onwards to
    # have reproducible behavior for certain hash-based operations.
    # See these references for further details:
    # https://docs.python.org/3.4/using/cmdline.html#envvar-PYTHONHASHSEED
    # https://github.com/keras-team/keras/issues/2280#issuecomment-306959926
    os.environ['PYTHONHASHSEED'] = '0'
    
    # The below is necessary for starting Numpy generated random numbers
    # in a well-defined initial state.
    
    np.random.seed(seed)
    
    # The below is necessary for starting core Python generated random numbers
    # in a well-defined state.
    
    rn.seed(seed)
    
    # Force TensorFlow to use single thread.
    # Multiple threads are a potential source of
    # non-reproducible results.
    # For further details, see: https://stackoverflow.com/questions/42022950/which-seeds-have-to-be-set-where-to-realize-100-reproducibility-of-training-res
    
    session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
    
    # The below tf.set_random_seed() will make random number generation
    # in the TensorFlow backend have a well-defined initial state.
    # For further details, see: https://www.tensorflow.org/api_docs/python/tf/set_random_seed
    
    tf.set_random_seed(seed)
    
    sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
    K.set_session(sess)