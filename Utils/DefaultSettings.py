import os

# The default DATAPATH for installing data and tools
DATAPATH=os.path.expanduser("~/TEES_DATA")

# The component download locations are listed here.
# If there is a problem with a download location, it is possible to 
# override a URL in the "TEES_SETTINGS" local settings file.
URL={}
URL["SVM_MULTICLASS_SOURCE"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass.tar.gz"
URL["SVM_MULTICLASS_LINUX"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux.tar.gz"
# Tools
URL["GENIA_SENTENCE_SPLITTER"] = "http://www.nactem.ac.uk/y-matsu/geniass/geniass-1.00.tar.gz"
URL["BANNER_SOURCE"] = "http://banner.svn.sourceforge.net/viewvc/banner/trunk/?view=tar"
#URL["JAVA_TROVE"] = "http://www.java2s.com/Code/JarDownload/trove/trove-2.1.0.jar.zip"

# Corpora
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/files/"
URL["GE_DEVEL"] = urlBase + "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz" 
URL["GE_TRAIN"] = urlBase + "BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
URL["GE_TEST"] = urlBase + "BioNLP-ST_2011_genia_test_data.tar.gz"
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/support-files/"
URL["GE_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
URL["GE_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
URL["GE_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_test_data.tar.gz"
URL["GE_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_train_data_rev1.tar.gz" 
URL["GE_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
URL["GE_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_test_data.tar.gz"
