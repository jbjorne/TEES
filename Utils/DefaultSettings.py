import os

# The default DATAPATH for installing data and tools
DATAPATH=os.path.expanduser("~/TEES_DATA")

# Default locations for evaluators and their devel set gold data (relative to DATAPATH)
EVALUATOR = {}
EVALUATOR["GE"] = "BioNLP-ST_2011_genia_tools_rev1"
EVALUATOR["EPI"] = "BioNLP-ST_2011_EPI-eval-tools"
EVALUATOR["ID"] = "BioNLP-ST_2011_ID-eval-tools"
EVALUATOR["BB"] = "BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software"
EVALUATOR["BI"] = "BioNLP-ST_2011_bacteria_interactions_evaluation_software"
EVALUATOR["REN"] = "BioNLP-ST_2011_bacteria_rename_evaluation_sofware"
EVALUATOR["CO"] = "CREvalPackage1.4"
EVALUATOR["GE09"] = "bionlp09_shared_task_evaluation_tools_v1"
# Gold data for evaluators
EVALUATOR["GE-gold"] = "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
EVALUATOR["EPI-gold"] = "BioNLP-ST_2011_Epi_and_PTM_development_data_rev1.tar.gz"
EVALUATOR["ID-gold"] = "BioNLP-ST_2011_Infectious_Diseases_development_data_rev1.tar.gz"
EVALUATOR["BB-gold"] = "BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz"
EVALUATOR["BI-gold"] = "BioNLP-ST_2011_bacteria_interactions_dev_data_rev1-remixed.tar.gz"
EVALUATOR["REN-gold"] = "BioNLP-ST_2011_bacteria_rename_dev_data.tar.gz"
EVALUATOR["CO-gold"] = "BioNLP-ST_2011_coreference_development_data.tar.gz"
EVALUATOR["GE09-gold"] = "bionlp09_shared_task_development_data_rev1_for_evaluator.tar.gz"


# A dictionary for installation URLs. If there is a problem with a 
# download location, it is possible to override a URL in the "TEES_SETTINGS" 
# local settings file.
URL = {}

# Models

URL["MODELS"] = "https://github.com/downloads/jbjorne/TEES/TEES-models-120723.tar.bz2"

# External Tools ##############################################################

URL["SVM_MULTICLASS_SOURCE"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass.tar.gz"
URL["SVM_MULTICLASS_LINUX"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux.tar.gz"
URL["GENIA_SENTENCE_SPLITTER"] = "http://www.nactem.ac.uk/y-matsu/geniass/geniass-1.00.tar.gz"
URL["BANNER_SOURCE"] = "http://banner.svn.sourceforge.net/viewvc/banner/trunk/?view=tar"
URL["BANNER_COMPILED"] = "https://github.com/downloads/jbjorne/TEES/BANNER-svn-snapshot-120630.tar.gz"
URL["BLLIP_SOURCE"] = "https://github.com/dmcc/bllip-parser/zipball/master"
URL["STANFORD_PARSER"] = "http://nlp.stanford.edu/software/stanford-parser-2012-03-09.tgz"
RUBY_PATH = "ruby" # for GENIA Sentence Splitter

# Corpora #####################################################################

# Preconverted
URL["BIONLP_11_CORPORA"] =  "https://github.com/downloads/jbjorne/TEES/BioNLP11-corpora-XML-120715.zip"
URL["BIONLP_09_CORPUS"] =  "https://github.com/downloads/jbjorne/TEES/BioNLP09-corpus-XML-120715.zip"
URL["DDI_11_CORPUS"] =  "https://github.com/downloads/jbjorne/TEES/DDI11-corpus-XML-120715.zip"

# BioNLP'11
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
URL["BIONLP11_EVALUATORS"] = "https://github.com/downloads/jbjorne/TEES/BioNLP-evaluators-120715.tar.gz"
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
#URL["TEES_PARSES"] = "/home/jari/biotext/TEES-parses-2.0/TEES-parses-120706.tar.gz"
URL["TEES_PARSES"] = "https://github.com/downloads/jbjorne/TEES/TEES-parses-120706.tar.gz"


# BioNLP'09 Shared Task
urlBase = "http://www.nactem.ac.uk/tsujii/GENIA/SharedTask/dat/"
URL["GE09_DEVEL"] = urlBase + "bionlp09_shared_task_development_data_rev1.tar.gz" 
URL["GE09_TRAIN"] = urlBase + "bionlp09_shared_task_training_data_rev2.tar.gz"
URL["GE09_TEST"] = urlBase + "bionlp09_shared_task_test_data_without_gold_annotation.tar.gz"
# BioNLP'09 Evaluator
URL["GE09_EVALUATOR"] = urlBase + "bionlp09_shared_task_evaluation_tools_v1.tar.gz"
# BioNLP'09 Shared Task parses
urlBase = "http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/SharedTask/dat/"
URL["GE09_DEVEL_ANALYSES"] = urlBase + "bionlp09_shared_task_development_analyses_rev2.tar.gz" 
URL["GE09_TRAIN_ANALYSES"] = urlBase + "bionlp09_shared_task_training_analyses_rev2.tar.gz"
URL["GE09_TEST_ANALYSES"] = urlBase + "bionlp09_shared_task_test_analyses_rev2.tar.gz"


# DDI
urlBase = "http://labda.inf.uc3m.es/DDIExtraction2011/"
URL["DDI_TRAIN_UNIFIED"] = urlBase + "DrugDDI_Unified.zip"
URL["DDI_TRAIN_MTMX"] = urlBase + "DrugDDI_MTMX.zip"
# If you have registered for the DDI Shared Task, insert the paths of your downloaded
# test files in the following variables (in your local settings file) to have them 
# converted for use with TEES
URL["DDI_TEST_UNIFIED"] = None
URL["DDI_TEST_MTMX"] = None


# Miscellaneous files
URL["TEES_RESOURCES"] = "https://github.com/downloads/jbjorne/TEES/TEES-resources-120705.tar.gz"
URL["DRUG_BANK_XML"] = "http://www.drugbank.ca/system/downloads/current/drugbank.xml.zip"
