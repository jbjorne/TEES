import os

# The default DATAPATH for installing data and tools
DATAPATH=os.path.expanduser("~/TEES_DATA")

# The component download locations are listed here.
# If there is a problem with a download location, it is possible to 
# override a URL in the "TEES_SETTINGS" local settings file.
URL={}
URL["SVM_MULTICLASS_SOURCE"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass.tar.gz"
URL["SVM_MULTICLASS_LINUX"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux.tar.gz"