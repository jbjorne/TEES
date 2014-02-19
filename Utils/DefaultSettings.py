import os

# The default DATAPATH for installing data and tools
DATAPATH=os.path.expanduser("~/.tees")
DEFAULT_LOCAL_SETTINGS=os.path.expanduser("~/.tees_local_settings.py")

# Default locations for evaluators and their devel set gold data (relative to DATAPATH)
EVALUATOR = {}
EVALUATOR["GE11"] = "BioNLP-ST_2011_genia_tools_rev1"
EVALUATOR["EPI11"] = "BioNLP-ST_2011_EPI-eval-tools"
EVALUATOR["ID11"] = "BioNLP-ST_2011_ID-eval-tools"
EVALUATOR["BB11"] = "BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software"
EVALUATOR["BI11"] = "BioNLP-ST_2011_bacteria_interactions_evaluation_software"
EVALUATOR["REN11"] = "BioNLP-ST_2011_bacteria_rename_evaluation_sofware"
EVALUATOR["CO11"] = "CREvalPackage1.4"
EVALUATOR["GE09"] = "bionlp09_shared_task_evaluation_tools_v1"
EVALUATOR["GRN13"] = "BioNLP-ST-2013_Gene_Regulation_Network_eval"
# Gold data for evaluators
EVALUATOR["GE11-gold"] = "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
EVALUATOR["EPI11-gold"] = "BioNLP-ST_2011_Epi_and_PTM_development_data_rev1.tar.gz"
EVALUATOR["ID11-gold"] = "BioNLP-ST_2011_Infectious_Diseases_development_data_rev1.tar.gz"
EVALUATOR["BB11-gold"] = "BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz"
EVALUATOR["BI11-gold"] = "BioNLP-ST_2011_bacteria_interactions_dev_data_rev1-remixed.tar.gz"
EVALUATOR["REN11-gold"] = "BioNLP-ST_2011_bacteria_rename_dev_data.tar.gz"
EVALUATOR["CO11-gold"] = "BioNLP-ST_2011_coreference_development_data.tar.gz"
EVALUATOR["GE09-gold"] = "bionlp09_shared_task_development_data_rev1_for_evaluator.tar.gz"
EVALUATOR["GRN13-gold"] = "BioNLP-ST-2013_Gene_Regulation_Network_dev.tar.gz"


# A dictionary for installation URLs. If there is a problem with a 
# download location, it is possible to override a URL in the "TEES_SETTINGS" 
# local settings file.
URL = {}

# Models

URL["MODELS"] = "http://sourceforge.net/projects/tees/files/data/TEES-models-130413.tar.bz2"

# External Tools ##############################################################

URL["SVM_MULTICLASS_SOURCE"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass.tar.gz"
URL["SVM_MULTICLASS_LINUX"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux32.tar.gz"
URL["GENIA_SENTENCE_SPLITTER"] = "http://www.nactem.ac.uk/y-matsu/geniass/geniass-1.00.tar.gz"
URL["BANNER_SOURCE"] = "http://banner.svn.sourceforge.net/viewvc/banner/trunk/?view=tar"
URL["BANNER_COMPILED"] = "http://sourceforge.net/projects/tees/files/data/BANNER-svn-snapshot-120630.tar.gz"
URL["BLLIP_SOURCE"] = "https://github.com/dmcc/bllip-parser/zipball/master"
URL["STANFORD_PARSER"] = "http://nlp.stanford.edu/software/stanford-parser-2012-03-09.tgz"
RUBY_PATH = "ruby" # for GENIA Sentence Splitter
JAVA = "java" # for programs using java

# Corpora #####################################################################

# Preconverted
URL["BIONLP_13_CORPORA"] =  "http://sourceforge.net/projects/tees/files/data/BioNLP13-corpora-XML-140216.zip"
URL["BIONLP_11_CORPORA"] =  "http://sourceforge.net/projects/tees/files/data/BioNLP11-corpora-XML-140216.zip"
URL["BIONLP_09_CORPUS"] =  "http://sourceforge.net/projects/tees/files/data/BioNLP09-corpus-XML-140216.zip"
URL["DDI_11_CORPUS"] =  "http://sourceforge.net/projects/tees/files/data/DDI11-corpus-XML-130224.zip"


# BioNLP'13
urlBase = "http://2013.bionlp-st.org/tasks/"
URL["GE13_DEVEL"] = urlBase + "BioNLP-ST-2013_GE_devel_data_rev3.tar.gz" 
URL["GE13_TRAIN"] = urlBase + "BioNLP-ST-2013_GE_train_data_rev3.tar.gz"
URL["GE13_TEST"] = urlBase + "BioNLP-ST-2013_GE_test_data_rev1.tar.gz"
URL["CG13_DEVEL"] = urlBase + "BioNLP-ST_2013_CG_development_data.tar.gz" 
URL["CG13_TRAIN"] = urlBase + "BioNLP-ST_2013_CG_training_data.tar.gz"
URL["CG13_TEST"] = urlBase + "BioNLP-ST_2013_CG_test_data.tar.gz"
URL["PC13_DEVEL"] = urlBase + "BioNLP-ST_2013_PC_development_data.tar.gz" 
URL["PC13_TRAIN"] = urlBase + "BioNLP-ST_2013_PC_training_data.tar.gz"
URL["PC13_TEST"] = urlBase + "BioNLP-ST_2013_PC_test_data.tar.gz"
URL["GRO13_DEVEL"] = urlBase + "BioNLP-ST_2013_GRO_development_data.tar.gz" 
URL["GRO13_TRAIN"] = urlBase + "BioNLP-ST_2013_GRO_training_data.tar.gz"
URL["GRO13_TEST"] = urlBase + "BioNLP-ST_2013_GRO_test-1.0-a1.tgz"
URL["GRN13_DEVEL"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_dev.tar.gz" 
URL["GRN13_TRAIN"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_train.tar.gz"
URL["GRN13_TEST"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_test.tar.gz"
URL["BB13_DEVEL"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_dev.tar.gz" 
URL["BB13_TRAIN"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_train.tar.gz"
URL["BB13_TEST"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_test.tar.gz"
#URL["BioNLP13_TOKENS"] = "http://2013.bionlp-st.org/supporting-resources/bionlp-st-2013_all_tasks_tokenised.tar.gz"
#URL["BioNLP13_STANFORD_PARSES"] = "http://2013.bionlp-st.org/supporting-resources/bionlp-st-2013_all_tasks_stanford_parser.tar.gz"
# Tokenizations
urlBase = "http://weaver.nlplab.org/~ninjin/bionlp_st_2013_supporting/"
URL["BB13_DEVEL_TOK"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_dev_tok_v1.tar.gz"
URL["BB13_TRAIN_TOK"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_train_tok_v1.tar.gz"
URL["BB13_TEST_TOK"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_test_tok_v1.tar.gz"
URL["CG13_DEVEL_TOK"] = urlBase + "BioNLP-ST_2013_CG_development_data_tok_v1.tar.gz"
URL["CG13_TRAIN_TOK"] = urlBase + "BioNLP-ST_2013_CG_training_data_tok_v1.tar.gz"
URL["CG13_TEST_TOK"] = urlBase + "BioNLP-ST_2013_CG_test_data_tok_v1.tar.gz"
URL["GE13_DEVEL_TOK"] = urlBase + "BioNLP-ST-2013_GE_devel_data_rev2_tok_v1.tar.gz"
URL["GE13_TRAIN_TOK"] = urlBase + "BioNLP-ST-2013_GE_train_data_rev2_tok_v1.tar.gz"
URL["GE13_TEST_TOK"] = urlBase + "BioNLP-ST_2013_GE_test_data_tok_v1.tar.gz"
URL["GRN13_DEVEL_TOK"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_dev_tok_v1.tar.gz"
URL["GRN13_TRAIN_TOK"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_train_tok_v1.tar.gz"
URL["GRN13_TEST_TOK"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_test_tok_v1.tar.gz"
URL["GRO13_DEVEL_TOK"] = urlBase + "BioNLP-ST_2013_GRO_development_data_tok_v1.tar.gz"
URL["GRO13_TRAIN_TOK"] = urlBase + "BioNLP-ST_2013_GRO_training_data_tok_v1.tar.gz"
URL["GRO13_TEST_TOK"] = urlBase + "BioNLP-ST_2013_GRO_test-1.0-a1_tok_v1.tar.gz"
URL["PC13_DEVEL_TOK"] = urlBase + "BioNLP-ST_2013_PC_development_data_tok_v1.tar.gz"
URL["PC13_TRAIN_TOK"] = urlBase + "BioNLP-ST_2013_PC_training_data_tok_v1.tar.gz"
URL["PC13_TEST_TOK"] = urlBase + "BioNLP-ST_2013_PC_test_data_tok_v1.tar.gz"
# Parses
URL["BB13_DEVEL_McCCJ"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_dev_mcccj_v1.tar.gz"
URL["BB13_TRAIN_McCCJ"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_train_mcccj_v1.tar.gz"
URL["BB13_TEST_McCCJ"] = urlBase + "BioNLP-ST-2013_Bacteria_Biotopes_test_mcccj_v1.tar.gz"
URL["CG13_DEVEL_McCCJ"] = urlBase + "BioNLP-ST_2013_CG_development_data_mcccj_v1.tar.gz"
URL["CG13_TRAIN_McCCJ"] = urlBase + "BioNLP-ST_2013_CG_training_data_mcccj_v1.tar.gz"
URL["CG13_TEST_McCCJ"] = urlBase + "BioNLP-ST_2013_CG_test_data_mcccj_v1.tar.gz"
URL["GE13_DEVEL_McCCJ"] = urlBase + "BioNLP-ST-2013_GE_devel_data_rev2_mcccj_v1.tar.gz"
URL["GE13_TRAIN_McCCJ"] = urlBase + "BioNLP-ST-2013_GE_train_data_rev2_mcccj_v1.tar.gz"
URL["GE13_TEST_McCCJ"] = urlBase + "BioNLP-ST_2013_GE_test_data_mcccj_v1.tar.gz"
URL["GRN13_DEVEL_McCCJ"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_dev_mcccj_v1.tar.gz"
URL["GRN13_TRAIN_McCCJ"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_train_mcccj_v1.tar.gz"
URL["GRN13_TEST_McCCJ"] = urlBase + "BioNLP-ST-2013_Gene_Regulation_Network_test_mcccj_v1.tar.gz"
URL["GRO13_DEVEL_McCCJ"] = urlBase + "BioNLP-ST_2013_GRO_development_data_mcccj_v1.tar.gz"
URL["GRO13_TRAIN_McCCJ"] = urlBase + "BioNLP-ST_2013_GRO_training_data_mcccj_v1.tar.gz"
URL["GRO13_TEST_McCCJ"] = urlBase + "BioNLP-ST_2013_GRO_test-1.0-a1_mcccj_v1.tar.gz"
URL["PC13_DEVEL_McCCJ"] = urlBase + "BioNLP-ST_2013_PC_development_data_mcccj_v1.tar.gz"
URL["PC13_TRAIN_McCCJ"] = urlBase + "BioNLP-ST_2013_PC_training_data_mcccj_v1.tar.gz"
URL["PC13_TEST_McCCJ"] = urlBase + "BioNLP-ST_2013_PC_test_data_mcccj_v1.tar.gz"

# BioNLP'11
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/files/"
# Main tasks
URL["GE11_DEVEL"] = urlBase + "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz" 
URL["GE11_TRAIN"] = urlBase + "BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
URL["GE11_TEST"] = urlBase + "BioNLP-ST_2011_genia_test_data.tar.gz"
URL["EPI11_DEVEL"] = urlBase + "BioNLP-ST_2011_Epi_and_PTM_development_data_rev1.tar.gz" 
URL["EPI11_TRAIN"] = urlBase + "BioNLP-ST_2011_Epi_and_PTM_training_data_rev1.tar.gz"
URL["EPI11_TEST"] = urlBase + "BioNLP-ST_2011_Epi_and_PTM_test_data.tar.gz"
URL["ID11_DEVEL"] = urlBase + "BioNLP-ST_2011_Infectious_Diseases_development_data_rev1.tar.gz" 
URL["ID11_TRAIN"] = urlBase + "BioNLP-ST_2011_Infectious_Diseases_training_data_rev1.tar.gz"
URL["ID11_TEST"] = urlBase + "BioNLP-ST_2011_Infectious_Diseases_test_data.tar.gz"
URL["BB11_DEVEL"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz" 
URL["BB11_TRAIN"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1.tar.gz"
URL["BB11_TEST"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_test_data.tar.gz"
URL["BI11_DEVEL"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_dev_data_rev1.tar.gz" 
URL["BI11_TRAIN"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_train_data_rev1.tar.gz"
URL["BI11_TEST"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_test_data.tar.gz"
# Supporting tasks
URL["REL11_DEVEL"] = urlBase + "BioNLP-ST_2011_Entity_Relations_development_data.tar.gz" 
URL["REL11_TRAIN"] = urlBase + "BioNLP-ST_2011_Entity_Relations_training_data.tar.gz"
URL["REL11_TEST"] = urlBase + "BioNLP-ST_2011_Entity_Relations_test_data.tar.gz"
URL["REN11_DEVEL"] = urlBase + "BioNLP-ST_2011_bacteria_rename_dev_data.tar.gz" 
URL["REN11_TRAIN"] = urlBase + "BioNLP-ST_2011_bacteria_rename_train_data.tar.gz"
URL["REN11_TEST"] = urlBase + "BioNLP-ST_2011_bacteria_rename_test_data.tar.gz"
URL["CO11_DEVEL"] = urlBase + "BioNLP-ST_2011_coreference_development_data.tar.gz"
URL["CO11_TRAIN"] = urlBase + "BioNLP-ST_2011_coreference_training_data_rev1.tar.gz"
URL["CO11_TEST"] = urlBase + "BioNLP-ST_2011_coreference_test_data.tar.gz"
# BioNLP'11 Evaluators
URL["BIONLP11_EVALUATORS"] = "http://sourceforge.net/projects/tees/files/data/BioNLP-evaluators-130224.tar.gz"
URL["GE11_EVALUATOR"] = urlBase + "BioNLP-ST_2011_genia_tools_rev1.tar.gz"
#URL["EPI_EVALUATOR"] = urlBase + 
#URL["ID_EVALUATOR"] = urlBase + 
URL["BB11_EVALUATOR"] = urlBase + "BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software_rev2.tar.gz"
URL["BI11_EVALUATOR"] = urlBase + "BioNLP-ST_2011_bacteria_interactions_evaluation_software.tar.gz"
#URL["REN_EVALUATOR"] = "http://sites.google.com/site/bionlpst/home/bacteria-gene-renaming-rename/BioNLP-ST_2011_bacteria_rename_evaluation_sofware.tar.gz"
URL["CO11_EVALUATOR"] = urlBase + "CREvalPackage1.6.tar.gz"
# BioNLP'11 Supporting resources
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/support-files/"
#GE
URL["GE11_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
URL["GE11_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
URL["GE11_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_test_data.tar.gz"
URL["GE11_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_train_data_rev1.tar.gz" 
URL["GE11_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
URL["GE11_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_test_data.tar.gz"
#EPI
URL["EPI11_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Epi_and_PTM_development_data.tar.gz"
URL["EPI11_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Epi_and_PTM_training_data.tar.gz"
URL["EPI11_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Epi_and_PTM_test_data.tar.gz"
URL["EPI11_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Epi_and_PTM_development_data.tar.gz" 
URL["EPI11_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Epi_and_PTM_training_data.tar.gz"
URL["EPI11_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Epi_and_PTM_test_data.tar.gz"
#ID
URL["ID11_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Infectious_Diseases_development_data.tar.gz"
URL["ID11_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Infectious_Diseases_training_data.tar.gz"
URL["ID11_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Infectious_Diseases_test_data.tar.gz"
URL["ID11_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Infectious_Diseases_development_data.tar.gz" 
URL["ID11_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Infectious_Diseases_training_data.tar.gz"
URL["ID11_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Infectious_Diseases_test_data.tar.gz"
#BB
URL["BB11_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz"
URL["BB11_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1.tar.gz"
URL["BB11_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_Bacteria_Biotopes_test_data.tar.gz"
URL["BB11_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz" 
URL["BB11_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1.tar.gz"
URL["BB11_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_Bacteria_Biotopes_test_data.tar.gz"
#BI
URL["BI11_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_bacteria_interactions_dev_data_rev1.tar.gz"
URL["BI11_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_bacteria_interactions_train_data_rev1.tar.gz"
URL["BI11_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_bacteria_interactions_test_data.tar.gz"
URL["BI11_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_bacteria_interactions_dev_data_rev1.tar.gz" 
URL["BI11_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_bacteria_interactions_train_data_rev1.tar.gz"
URL["BI11_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_bacteria_interactions_test_data.tar.gz"
# Parses not provided in the shared tasks
#URL["TEES_PARSES"] = "/home/jari/biotext/TEES-parses-2.0/TEES-parses-120706.tar.gz"
URL["TEES_PARSES"] = "http://sourceforge.net/projects/tees/files/data/TEES-parses-130224.tar.gz"


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


# DDI'11 Shared Task
urlBase = "http://labda.inf.uc3m.es/DDIExtraction2011/"
URL["DDI11_TRAIN_UNIFIED"] = urlBase + "DrugDDI_Unified.zip"
URL["DDI11_TRAIN_MTMX"] = urlBase + "DrugDDI_MTMX.zip"
# If you have registered for the DDI'11 Shared Task, insert the paths of your downloaded
# test files in the following variables (in your local settings file) to have them 
# converted for use with TEES
URL["DDI11_TEST_UNIFIED"] = None
URL["DDI11_TEST_MTMX"] = None


# DDI'13 Shared Task
URL["DDI13_TRAIN"] = "http://www.cs.york.ac.uk/semeval-2013/task9/data/uploads/datasets/train/semeval_task9_train.zip"
# If you have registered for the DDI'11 Shared Task, insert the paths of your downloaded
# test files in the following variables (in your local settings file) to have them 
# converted for use with TEES when using Utils/Convert/convertDDI13.py
URL["DDI13_TEST_TASK_9.1"] = None
URL["DDI13_TEST_TASK_9.2"] = None
URL["DDI13_TEST_TASK_9.1_TEES_PARSES"] = None
URL["DDI13_TEST_TASK_9.2_TEES_PARSES"] = None
URL["DDI13_TRAIN_TEES_PARSES"] = "http://sourceforge.net/projects/tees/files/data/DDI13-TEES-parses-130224.tar.gz"


# Miscellaneous files
URL["TEES_RESOURCES"] = "http://sourceforge.net/projects/tees/files/data/TEES-resources-120705.tar.gz"
URL["DRUG_BANK_XML"] = "http://www.drugbank.ca/system/downloads/current/drugbank.xml.zip"
