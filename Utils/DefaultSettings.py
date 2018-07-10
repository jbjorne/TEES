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
EVALUATOR["GE11_DEVEL-gold"] = "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
EVALUATOR["EPI11_DEVEL-gold"] = "BioNLP-ST_2011_Epi_and_PTM_development_data_rev1.tar.gz"
EVALUATOR["ID11_DEVEL-gold"] = "BioNLP-ST_2011_Infectious_Diseases_development_data_rev1.tar.gz"
EVALUATOR["BB11_DEVEL-gold"] = "BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1.tar.gz"
EVALUATOR["BI11_DEVEL-gold"] = "BioNLP-ST_2011_bacteria_interactions_dev_data_rev1-remixed.tar.gz"
EVALUATOR["REN11_DEVEL-gold"] = "BioNLP-ST_2011_bacteria_rename_dev_data.tar.gz"
EVALUATOR["CO11_DEVEL-gold"] = "BioNLP-ST_2011_coreference_development_data.tar.gz"
EVALUATOR["GE09_DEVEL-gold"] = "bionlp09_shared_task_development_data_rev1_for_evaluator.tar.gz"
EVALUATOR["GRN13_DEVEL-gold"] = "BioNLP-ST-2013_Gene_Regulation_Network_dev.tar.gz"


# A dictionary for installation URLs. If there is a problem with a 
# download location, it is possible to override a URL in the "TEES_SETTINGS" 
# local settings file.
URL = {}

# Models

URL["MODELS"] = "http://sourceforge.net/projects/tees/files/data/TEES-models-150210.tar.bz2"

# External Tools ##############################################################

URL["SVM_MULTICLASS_SOURCE"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass.tar.gz"
URL["SVM_MULTICLASS_LINUX_32"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux32.tar.gz"
URL["SVM_MULTICLASS_LINUX_64"] = "http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux64.tar.gz"
URL["GENIA_SENTENCE_SPLITTER"] = "http://www.nactem.ac.uk/y-matsu/geniass/geniass-1.00.tar.gz"
URL["BANNER_SOURCE"] = "http://banner.svn.sourceforge.net/viewvc/banner/trunk/?view=tar"
URL["BANNER_COMPILED"] = "http://sourceforge.net/projects/tees/files/data/BANNER-svn-snapshot-120630.tar.gz"
URL["BLLIP_SOURCE"] = "https://github.com/dmcc/bllip-parser/zipball/master"
URL["STANFORD_PARSER"] = "http://nlp.stanford.edu/software/stanford-parser-2012-03-09.tgz"
# "http://nlp.stanford.edu/software/stanford-parser-full-2015-12-09.zip"
RUBY_PATH = "ruby" # for GENIA Sentence Splitter
JAVA = "java" # for programs using java

# Corpora #####################################################################

# Preconverted
URL["BIONLP_13_CORPORA"] =  "http://sourceforge.net/projects/tees/files/data/BioNLP13-corpora-XML-150114.tar.gz"
URL["BIONLP_11_CORPORA"] =  "http://sourceforge.net/projects/tees/files/data/BioNLP11-corpora-XML-150114.tar.gz"
URL["BIONLP_09_CORPUS"] =  "http://sourceforge.net/projects/tees/files/data/BioNLP09-corpus-XML-150114.tar.gz"
URL["DDI_11_CORPUS"] =  "http://sourceforge.net/projects/tees/files/data/DDI11-corpus-XML-150126.tar.gz"
URL["DDI_13_CORPUS"] =  "http://sourceforge.net/projects/tees/files/data/DDI13-corpus-XML-150126.tar.gz"

# BioNLP'16
urlBase = "http://2016.bionlp-st.org/tasks/"
#URL["SDF16_DEVEL"] = urlBase + "seedev/BioNLP-ST-2016_SeeDev-full_train.zip"
#URL["SDF16_TRAIN"] = urlBase + "seedev/BioNLP-ST-2016_SeeDev-full_dev.zip"
URL["SDB16_DEVEL"] = urlBase + "seedev/BioNLP-ST-2016_SeeDev-binary_dev.zip"
URL["SDB16_TRAIN"] = urlBase + "seedev/BioNLP-ST-2016_SeeDev-binary_train.zip"
URL["SDB16_TEST"] = urlBase + "seedev/BioNLP-ST-2016_SeeDev-binary_test.zip"
URL["BB16E_DEVEL"] = urlBase + "bb2/BioNLP-ST-2016_BB-event_dev.zip"
URL["BB16E_TRAIN"] = urlBase + "bb2/BioNLP-ST-2016_BB-event_train.zip"
URL["BB16E_TEST"] = urlBase + "bb2/BioNLP-ST-2016_BB-event_test.zip"
URL["BB16EN_DEVEL"] = urlBase + "bb2/BioNLP-ST-2016_BB-event+ner_dev.zip"
URL["BB16EN_TRAIN"] = urlBase + "bb2/BioNLP-ST-2016_BB-event+ner_train.zip"
URL["BB16EN_TEST"] = urlBase + "bb2/BioNLP-ST-2016_BB-event+ner_test.zip"
URL["BB16KB_DEVEL"] = urlBase + "bb2/BioNLP-ST-2016_BB-kb_dev.zip"
URL["BB16KB_TRAIN"] = urlBase + "bb2/BioNLP-ST-2016_BB-kb_train.zip"
# Resources
urlBase = "https://sites.google.com/site/bionlpst2016/" 
URL["BB16_SPECIES_TRAIN_AND_DEVEL"] = urlBase + "BB3_species-dictionary_train+dev_resources.zip"
URL["BB16_SPECIES_TEST"] = urlBase + "BB3_species-dictionary_test_resources.zip"
URL["BB16_STANFORD_NER_TRAIN_AND_DEVEL"] = urlBase + "BB3_stanford-ner_train+dev_resources.zip"
URL["BB16_STANFORD_NER_TEST"] = urlBase + "BB3_stanford-ner_test_resources.zip"
URL["BB16_LINNAEUS_TRAIN_AND_DEVEL"] = urlBase + "BB3_linnaeus_train+dev_resources.zip"
URL["BB16_LINNAEUS_TEST"] = urlBase + "BB3_linnaeus_test_resources.zip"
URL["BB16_SR4GN_TRAIN_AND_DEVEL"] = urlBase + "BB3_sr4gn_train+dev_resources.zip"
URL["BB16_SR4GN_TEST"] = urlBase + "BB3_sr4gn_test_resources.zip"
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
#urlBase = "http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/SharedTask/dat/"
URL["GE09_DEVEL_ANALYSES"] = urlBase + "bionlp09_shared_task_development_analyses_rev2.tar.gz" 
URL["GE09_TRAIN_ANALYSES"] = urlBase + "bionlp09_shared_task_training_analyses_rev2.tar.gz"
URL["GE09_TEST_ANALYSES"] = urlBase + "bionlp09_shared_task_test_analyses_rev2.tar.gz"


# DDI'11 Shared Task
URL["DDI11_CORPUS"] = "http://sourceforge.net/projects/tees/files/data/DDI_2011_with_MTMX.tar.gz"

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


# Five protein-protein interaction corpora
urlBase = "http://mars.cs.utu.fi/PPICorpora/"
URL["AIMed_LEARNING_FORMAT"] = urlBase + "AImed-learning-format.xml.gz"
URL["BioInfer_LEARNING_FORMAT"] = urlBase + "BioInfer-learning-format.xml.gz"
URL["HPRD50_LEARNING_FORMAT"] = urlBase + "HPRD50-learning-format.xml.gz"
URL["IEPA_LEARNING_FORMAT"] = urlBase + "IEPA-learning-format.xml.gz"
URL["LLL_LEARNING_FORMAT"] = urlBase + "LLL-learning-format.xml.gz"
URL["PPI_EVALUATION_STANDARD"] = urlBase + "ppi-eval-standard-0.9.2b.tar.gz"


# BioCreative VI Task 5: Text mining chemical-protein interactions (CHEMPROT)
urlBase = "http://www.biocreative.org/media/store/files/2017/"
URL["CP17_TRAIN"] = urlBase + "chemprot_training.zip"
URL["CP17_DEVEL"] = urlBase + "chemprot_development.zip"
URL["CP17_TEST"] = urlBase + "chemprot_test.zip"
URL["CP17_TEST_GOLD"] = urlBase + "chemprot_test_gs.zip"


# Miscellaneous files
URL["TEES_RESOURCES"] = "http://sourceforge.net/projects/tees/files/data/TEES-resources-120705.tar.gz"
URL["DRUG_BANK_XML"] = "http://sourceforge.net/projects/tees/files/data/drugbank.xml-150128.zip"
URL["SE10T8_CORPUS"] = "https://drive.google.com/uc?export=download&id=0B_jQiLugGTAkMDQ5ZjZiMTUtMzQ1Yy00YWNmLWJlZDYtOWY1ZDMwY2U4YjFk"

W2VFILE = os.path.expanduser("~/Downloads/wikipedia-pubmed-and-PMC-w2v.bin")
W2V = {}


# Key definitions
KEY_TYPE = {}
KEY_TYPE["W2VFILE"] = {"type":"file", "md5":"ec5d68c1f372011c550eb9c2ff4e71b6"}