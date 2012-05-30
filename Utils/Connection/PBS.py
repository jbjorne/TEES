import types
from Unix import UnixConnection

class PBSConnection(UnixConnection):
    """
    For using Portable Batch System Professional (PBS Pro) of Altair Engineering (http://www.altair.com).
    """
    def __init__(self):
        self.wallTime = "48:00:00"
        self.cores = 1
        self.modules = []
