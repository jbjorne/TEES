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

# BioNLP'11 Corpora
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/files/"
# Main tasks
URL["GE_DEVEL"] = urlBase + "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz" 
URL["GE_TRAIN"] = urlBase + "BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
URL["GE_TEST"] = urlBase + "BioNLP-ST_2011_genia_test_data.tar.gz"
URL["EPI_DEVEL"] = urlBase + "BioNLP-ST_2011_Epi_and_PTM_development_data_rev1.tar.gz" 
URL["EPI_TRAIN"] = urlBase + "BioNLP-ST_2011_Epi_and_PTM_training_data_rev1.tar.gz"
URL["EPI_TEST"] = urlBase + "BioNLP-ST_2011_Epi_and_PTM_test_data.tar.gz"
URL["ID_DEVEL"] = urlBase + "BioNLP-ST_2011_Infectious_Diseases_development_data_rev1.tar.gz" 
URL["ID_TRAIN"] = urlBase + "BioNLP-ST_2011_Infectious_Diseases_training_data_rev1.tar.gz"
URL["ID_TEST"] = urlBase + "BioNLP-ST_2011_Infectious_Diseases_test_data.tar.gz"
URL["BB_DEVEL"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz" 
URL["BB_TRAIN"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1.tar.gz"
URL["BB_TEST"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_test_data.tar.gz"
URL["BI_DEVEL"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_dev_data_rev1.tar.gz" 
URL["BI_TRAIN"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_train_data_rev1.tar.gz"
URL["BI_TEST"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_test_data.tar.gz"
# Supporting tasks
URL["REL_DEVEL"] = urlBase + "BioNLP-ST_2011_Entity_Relations_development_data.tar.gz" 
URL["REL_TRAIN"] = urlBase + "BioNLP-ST_2011_Entity_Relations_training_data.tar.gz"
URL["REL_TEST"] = urlBase + "BioNLP-ST_2011_Entity_Relations_test_data.tar.gz"
URL["REN_DEVEL"] = urlBase + "BioNLP-ST_2011_bacteria_rename_dev_data.tar.gz" 
URL["REN_TRAIN"] = urlBase + "BioNLP-ST_2011_bacteria_rename_train_data.tar.gz"
URL["REN_TEST"] = urlBase + "BioNLP-ST_2011_bacteria_rename_test_data.tar.gz"
URL["CO_DEVEL"] = urlBase + "BioNLP-ST_2011_coreference_development_data.tar.gz"
URL["CO_TRAIN"] = urlBase + "BioNLP-ST_2011_coreference_training_data_rev1.tar.gz"
URL["CO_TEST"] = urlBase + "BioNLP-ST_2011_coreference_test_data.tar.gz"
# BioNLP'11 Evaluators
URL["GE_EVALUATOR"] = urlBase + "BioNLP-ST_2011_genia_tools_rev1.tar.gz"
#URL["EPI_EVALUATOR"] = urlBase + 
#URL["ID_EVALUATOR"] = urlBase + 
URL["BB_EVALUATOR"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software_rev2.tar.gz"
URL["BI_EVALUATOR"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_evaluation_software.tar.gz"
#URL["REN_EVALUATOR"] = "http://sites.google.com/site/bionlpst/home/bacteria-gene-renaming-rename/BioNLP-ST_2011_bacteria_rename_evaluation_sofware.tar.gz"
URL["CO_EVALUATOR"] = urlBase + "CREvalPackage1.6.tar.gz"
# BioNLP'11 Supporting resources
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/support-files/"
#GE
URL["GE_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
URL["GE_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
URL["GE_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_test_data.tar.gz"
URL["GE_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_train_data_rev1.tar.gz" 
URL["GE_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
URL["GE_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_test_data.tar.gz"
#EPI
URL["EPI_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Epi_and_PTM_development_data.tar.gz"
URL["EPI_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Epi_and_PTM_training_data.tar.gz"
URL["EPI_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Epi_and_PTM_test_data.tar.gz"
URL["EPI_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Epi_and_PTM_development_data.tar.gz" 
URL["EPI_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Epi_and_PTM_training_data.tar.gz"
URL["EPI_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Epi_and_PTM_test_data.tar.gz"
#ID
URL["ID_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Infectious_Diseases_development_data.tar.gz"
URL["ID_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Infectious_Diseases_training_data.tar.gz"
URL["ID_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Infectious_Diseases_test_data.tar.gz"
URL["ID_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Infectious_Diseases_development_data.tar.gz" 
URL["ID_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Infectious_Diseases_training_data.tar.gz"
URL["ID_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Infectious_Diseases_test_data.tar.gz"
#BB
URL["BB_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz"
URL["BB_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1.tar.gz"
URL["BB_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Bacteria_Biotopes_test_data.tar.gz"
URL["BB_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz" 
URL["BB_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1.tar.gz"
URL["BB_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Bacteria_Biotopes_test_data.tar.gz"
#BI
URL["BI_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_bacteria_interactions_dev_data_rev1.tar.gz"
URL["BI_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_bacteria_interactions_train_data_rev1.tar.gz"
URL["BI_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_bacteria_interactions_test_data.tar.gz"
URL["BI_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_bacteria_interactions_dev_data_rev1.tar.gz" 
URL["BI_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_bacteria_interactions_train_data_rev1.tar.gz"
URL["BI_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_bacteria_interactions_test_data.tar.gz"
# Parses not provided in the shared tasks
URL["TEES_PARSES"] = "/home/jari/biotext/BioNLP2011/data/parseExport/TEES-parses-2.0.tar.gz"
