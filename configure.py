#!/usr/bin/env python

"""
Configure TEES by installing data files and external components.
"""

import sys, os, shutil
import textwrap
from Utils.Menu import *
import Utils.Settings as Settings
# Classifier wrapper
import Classifiers.SVMMultiClassClassifier
# External tools wrappers
import Tools.GeniaSentenceSplitter
import Tools.BANNER
import Tools.BLLIPParser
import Tools.StanfordParser
# Corpora
import Utils.Convert.convertBioNLP as convertBioNLP
import Utils.Convert.convertDDI13 as convertDDI13
import Utils.Download
# TODO: Logging

def pathMenuInitializer(menu, prevMenu):
    if menu != prevMenu:
        nextMenus = []
        if prevMenu.optDict["1"].toggle:
            nextMenus.append("Classifier")
        if prevMenu.optDict["2"].toggle:
            nextMenus.append("Models")
        if prevMenu.optDict["3"].toggle:
            nextMenus.append("Corpora")
        if prevMenu.optDict["4"].toggle:
            nextMenus.append("Tools")
        menu.optDict["c"].nextMenu = nextMenus
    
    menu.text = """
    1. By default, all data and tools will be installed to one directory, the DATAPATH. 
    You can later set the installation directory individually for each component, or 
    you can change the default path now.
    
    """
    if menu.defaultInstallDir == None:
        if menu.system.progArgs["installDir"] != None:
            menu.defaultInstallDir = menu.system.progArgs["installDir"]
            if menu.system.progArgs["clearInstallDir"] and os.path.exists(menu.system.progArgs["installDir"]):
                shutil.rmtree(menu.system.progArgs["installDir"])
            menu.text += "\nUsing the DATAPATH path from configure.py command line options.\n\n"
        elif menu.system.progArgs["localSettings"] != None:
            os.environ["TEES_SETTINGS"] = os.path.abspath(menu.system.progArgs["localSettings"])
            reload(Settings)
            menu.defaultInstallDir = Settings.DATAPATH
        elif "TEES_SETTINGS" in os.environ:
            menu.defaultInstallDir = Settings.DATAPATH
        else:
            menu.defaultInstallDir = os.path.expanduser("~/.tees")
    elif os.path.exists(menu.defaultInstallDir):
        if not os.path.isdir(menu.defaultInstallDir):
            menu.text += "WARNING! The DATAPATH directory is not a directory.\n\n"
    else:
        try:
            os.makedirs(menu.defaultInstallDir)
        except:
            menu.text += "WARNING! Could not create DATAPATH.\n\n"
    #menu.text += "DATAPATH = " + menu.defaultInstallDir + "\n"
    
    menu.text += """
    2. TEES reads its configuration from a file defined by the environment
    variable "TEES_SETTINGS". This environment variable must be set, and
    point to a configuration file for TEES to work. By editing this 
    configuration file you can configure TEES in addition (or instead of)
    using this configuration program.
    """
    if menu.configFilePath == None:
        if menu.system.progArgs["localSettings"] != None:
            menu.configFilePath = menu.system.progArgs["localSettings"]
            menu.text += "\nUsing the TEES_SETTINGS path from configure.py command line options.\n\n"
        elif "TEES_SETTINGS" in os.environ:
            menu.configFilePath = os.environ["TEES_SETTINGS"]
            menu.text += """
            The "TEES_SETTINGS" environment variable is already set. If the configuration file
            exists, this installation program will use it and by default install only missing components.
            """
        else:
            menu.configFilePath = os.path.expanduser("~/.tees_local_settings.py")
            if os.path.exists(menu.configFilePath):
                menu.text += """
                The "TEES_SETTINGS" environment variable is not set, but a configuration file has been
                found in the default location. This installation program will use the existing
                file, and by default install only missing components.
                """     
            else:
                menu.text += """
                The "TEES_SETTINGS" environment variable is not set, so a new local configuration file
                will be created.
                """
    #menu.text += "TEES_SETTINGS = " + menu.configFilePath + "\n\n"
    menu.system.setAttr("defaultInstallDir", menu.defaultInstallDir)
    Settings.DATAPATH = menu.defaultInstallDir
    menu.system.setAttr("configFilePath", menu.configFilePath)
    os.environ["TEES_SETTINGS"] = menu.configFilePath
    setClosingMessage(menu.system, menu.configFilePath)
    menu.optDict["c"].handlerArgs = [menu.configFilePath]
    
def setClosingMessage(menuSystem, configFilePath):
    menuSystem.closingMessage = "!!!!!!!!!!!!!!!!!!!!!! Important Note !!!!!!!!!!!!!!!!!!!!!!\n"
    menuSystem.closingMessage += "Before using TEES, remember to define the TEES_SETTINGS\n"
    menuSystem.closingMessage += "environment variable, if you used a local settings path\n"
    menuSystem.closingMessage += "other than " + os.path.expanduser("~/.tees_local_settings.py") + "\n"
    menuSystem.closingMessage += "How to do this depends on your shell,\n"
    menuSystem.closingMessage += "some common commands are:\n\n"
    menuSystem.closingMessage += "bash: 'export TEES_SETTINGS=" + configFilePath + "'\n"
    menuSystem.closingMessage += "tcsh: 'setenv TEES_SETTINGS " + configFilePath + "'\n" 
    
def initLocalSettings(filename):
    assert Menu.system.defaultInstallDir != None
    if os.path.exists(filename):
        print >> sys.stderr, "Using existing local settings file", filename
        return
    print >> sys.stderr, "Initializing local settings file", filename
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    f = open(filename, "wt")
    f.write("""
    # Edit these settings to configure TEES. A variable must have a value 
    # other than None for it to be usable. This file is interpreted as
    # a Python module, so Python code can be used.
    
    # Tools
    SVM_MULTICLASS_DIR = None # svm_multiclass_learn and svm_multiclass_classify directory
    BANNER_DIR = None # BANNER program directory
    GENIA_SENTENCE_SPLITTER_DIR = None # GENIA Sentence Splitter directory
    RUBY_PATH = "ruby" # Command to run Ruby (used only by the GENIA Sentence Splitter)
    BLLIP_PARSER_DIR = None # The BLLIP parser directory
    MCCLOSKY_BIOPARSINGMODEL_DIR = None # The McClosky BioModel directory
    STANFORD_PARSER_DIR = None # The Stanford parser directory
    
    # Data
    DATAPATH = 'DATAPATH_VALUE' # Main directory for datafiles
    CORPUS_DIR = None # Directory for the corpus XML-files
    MODEL_DIR = None # Directory for the official TEES models
    """.replace("    ", "").replace("DATAPATH_VALUE", Menu.system.defaultInstallDir))
    f.close()
    # Reset local settings
    os.environ["TEES_SETTINGS"] = filename
    reload(Settings)

def checkInstallPath(menu, setting, defaultInstallKey="i", defaultSkipKey="s"):
    #if getattr(menu, menuVariable) == None:
    #    setattr(menu, menuVariable, menu.system.defaultInstallDir + "/" + installSubDir)
    if hasattr(Settings, setting) and getattr(Settings, setting) != None:
        menu.text += "The " + setting + " setting is already configured, so the default option is to skip installing.\n\n"
        menu.text += setting + "=" + getattr(Settings, setting)
        menu.setDefault(defaultSkipKey)
        return False
    else:
        menu.setDefault(defaultInstallKey)
        return True

def checkCorpusInstall(corpus, dataSets=("-train.xml", "-devel.xml", "-test.xml")):
    # CORPUS_DIR is set, so check if the corpus is installed
    allFound = True # check for all corpus subsets
    for dataSet in dataSets:
        filePath = Settings.CORPUS_DIR + "/" + corpus + dataSet
        if not os.path.exists(filePath):
            #print >> sys.stderr, "Corpus file", filePath, "is not installed" 
            allFound = False
    if allFound: # if corpus files are present, installing this corpora can be skipped
        return True
    else: # if a corpus file is missing, mark it to be installed
        return False

def svmMenuInitializer(menu, prevMenu):
    menu.text = """
    TEES uses the SVM Multiclass classifer by Thorsten Joachims for all 
    classification tasks. You can optionally choose to compile it from 
    source if the precompiled Linux-binary does not work on your system.
    """
    checkInstallPath(menu, "SVM_MULTICLASS_DIR")
    if hasattr(Settings, "SVM_MULTICLASS_DIR") and getattr(Settings, "SVM_MULTICLASS_DIR") != None:
        menu.setDefault("s")
        svmInstallDir = Settings.SVM_MULTICLASS_DIR
    else:
        menu.setDefault("i")
        svmInstallDir = None
    menu.optDict["i"].handlerArgs = [None, os.path.join(menu.system.defaultInstallDir, "tools/download"), True, menu.optDict["1"].toggle, True]

def toolsMenuInitializer(menu, prevMenu):
    # Java path for ANT
    #if getattr(menu, "javaHome") == None:
    #    if "JAVA_HOME" in os.environ:
    #        setattr(menu, "javaHome", os.environ("JAVA_HOME"))
    #    else:
    #        setattr(menu, "javaHome", "")
    # Tool initializers
    handlers = []
    handlerArgs = []
    redownload = menu.optDict["1"].toggle
    if menu.optDict["2"].toggle or (menu != prevMenu and checkInstallPath(menu, "GENIA_SENTENCE_SPLITTER_DIR")):
        menu.optDict["2"].toggle = True
        handlers.append(Tools.GeniaSentenceSplitter.install)
        handlerArgs.append([None, None, redownload, True])  
    if menu.optDict["3"].toggle or (menu != prevMenu and checkInstallPath(menu, "BANNER_DIR")):
        menu.optDict["3"].toggle = True
        handlers.append(Tools.BANNER.install)
        handlerArgs.append([None, None, redownload, False, None, True])  
    if menu.optDict["4"].toggle or (menu != prevMenu and checkInstallPath(menu, "BLLIP_PARSER_DIR")):
        menu.optDict["4"].toggle = True
        handlers.append(Tools.BLLIPParser.install)
        handlerArgs.append([None, None, redownload, True])  
    if menu.optDict["5"].toggle or (menu != prevMenu and checkInstallPath(menu, "STANFORD_PARSER_DIR")):
        menu.optDict["5"].toggle = True
        handlers.append(Tools.StanfordParser.install)
        handlerArgs.append([None, None, redownload, True])  
    menu.optDict["i"].handler = handlers
    menu.optDict["i"].handlerArgs = handlerArgs

def modelsMenuInitializer(menu, prevMenu):
    menu.text = """
    TEES models are used for predicting events or relations using
    classify.py. Models are provided for all tasks in the BioNLP'11, 
    BioNLP'09 and DDI'11 shared tasks, for all BioNLP'13 tasks except
    BB task 1, and for task 9.2 of the DDI'13 shared task.
    
    For a list of models and instructions for using them see
    https://github.com/jbjorne/TEES/wiki/Classifying.
    """
    # Mark "skip" as default option, this will be re-marked if there is no model directory
    if menu != prevMenu:
        menu.setDefault("s")
    redownload = menu.optDict["1"].toggle
    destPath = os.path.join(menu.system.defaultInstallDir, "models")
    downloadPath = os.path.join(menu.system.defaultInstallDir, "models/download")
    # If MODEL_DIR setting is not set set it now
    if menu != prevMenu and (not hasattr(Settings, "MODEL_DIR") or Settings.MODEL_DIR == None or not os.path.exists(Settings.MODEL_DIR)):
        menu.setDefault("i")
    menu.optDict["i"].handler = [Utils.Download.downloadAndExtract, Settings.setLocal]
    menu.optDict["i"].handlerArgs = [[Settings.URL["MODELS"], destPath, downloadPath, None, True, redownload], ["MODEL_DIR", destPath]]

def corpusMenuInitializer(menu, prevMenu):
    menu.text = """
    The corpora are used for training new models and testing existing
    models. The corpora installable here are from the three BioNLP Shared
    Tasks (2009, 2011 and 2013) on Event Extraction (organized by 
    University of Tokyo), and the two Drug-Drug Interaction  Extraction 
    tasks (DDI'11 and 13, organized by Universidad Carlos III de Madrid).
    
    The 2009 and 2011 corpora are downloaded as interaction XML files, 
    generated from the original Shared Task files. If you need to convert 
    the corpora from  the original files, you can use the convertBioNLP.py, 
    convertDDI.py and convertDDI13.py programs located at Utils/Convert.
    
    The 2013 corpora will be converted to interaction XML from the official 
    corpus files, downloaded automatically from the task websites. Installing 
    the BioNLP'13 corpora will take about 10 minutes.
    
    It is also recommended to download the official BioNLP Shared Task evaluator 
    programs, which will be used by TEES when training or testing on those corpora.
    """
    # Mark "skip" as default option, this will be re-marked as install if a corpus is missing
    menu.setDefault("s")
    # If CORPUS_DIR setting is not set set it now
    if not hasattr(Settings, "CORPUS_DIR") or getattr(Settings, "CORPUS_DIR") == None:
        Settings.setLocal("CORPUS_DIR", os.path.join(menu.system.defaultInstallDir, "corpora"))
        print >> sys.stderr
    # Initialize handlers
    handlers = []
    handlerArgs = []
    corpusInstallPath = os.path.join(menu.system.defaultInstallDir, "corpora")
    corpusDownloadPath = os.path.join(menu.system.defaultInstallDir, "corpora/download")
    # Check which corpora need to be installed
    redownload = menu.optDict["1"].toggle
    # 2009-2011 corpora
    for corpus in ["GE11", "EPI11", "ID11", "BB11", "BI11", "CO11", "REL11", "REN11"]:
        if menu.optDict["2"].toggle or (menu != prevMenu and not checkCorpusInstall(corpus)):
            menu.setDefault("i")
            menu.optDict["2"].toggle = True
            handlers.append(convertBioNLP.installPreconverted)
            handlerArgs.append(["BIONLP_11_CORPORA", corpusInstallPath, corpusDownloadPath, redownload, True])
            break
    if menu.optDict["3"].toggle or (menu != prevMenu and not checkCorpusInstall("GE09")):
        menu.setDefault("i")
        menu.optDict["3"].toggle = True
        handlers.append(convertBioNLP.installPreconverted)
        handlerArgs.append(["BIONLP_09_CORPUS", corpusInstallPath, corpusDownloadPath, redownload, True])
    if menu.optDict["4"].toggle or (menu != prevMenu and not checkCorpusInstall("DDI11", ("-train.xml", "-devel.xml"))):
        menu.setDefault("i")
        menu.optDict["4"].toggle = True
        handlers.append(convertBioNLP.installPreconverted)
        handlerArgs.append(["DDI_11_CORPUS", corpusInstallPath, corpusDownloadPath, redownload, True])
    # 2013 corpora
    bioNLP13Corpora = ["GE13", "CG13", "PC13", "GRO13", "GRN13", "BB13T2", "BB13T3"]
    for corpus in bioNLP13Corpora:
        if menu.optDict["5"].toggle or (menu != prevMenu and not checkCorpusInstall(corpus)):
            menu.setDefault("i")
            menu.optDict["5"].toggle = True
            #handlers.append(convertBioNLP.convert)
            #handlerArgs.append([bioNLP13Corpora, corpusInstallPath, corpusDownloadPath, redownload, False])
            handlers.append(convertBioNLP.installPreconverted)
            handlerArgs.append(["BIONLP_13_CORPORA", corpusInstallPath, corpusDownloadPath, redownload, True])
            break
    if menu.optDict["6"].toggle or (menu != prevMenu and not checkCorpusInstall("DDI13", ("-train.xml",))):
        menu.setDefault("i")
        menu.optDict["6"].toggle = False #True
        handlers.append(convertDDI13.convertDDI13)
        handlerArgs.append([corpusInstallPath, corpusDownloadPath, ["DDI13_TRAIN", "DDI13_TEST_TASK_9.1", "DDI13_TEST_TASK_9.2"], redownload])
    # A handler for installing BioNLP'11 evaluators
    evaluatorInstallPath = os.path.join(menu.system.defaultInstallDir, "tools/evaluators")
    evaluatorDownloadPath = os.path.join(menu.system.defaultInstallDir, "tools/download")
    if menu.optDict["7"].toggle or (menu != prevMenu and (not hasattr(Settings, "BIONLP_EVALUATOR_DIR") or getattr(Settings, "BIONLP_EVALUATOR_DIR") == None)):
        menu.setDefault("i")
        menu.optDict["7"].toggle = True
        handlers.append(convertBioNLP.installEvaluators)
        handlerArgs.append([evaluatorInstallPath, evaluatorDownloadPath, redownload, True])
    # Add the handlers to install option
    menu.optDict["i"].handler = handlers
    menu.optDict["i"].handlerArgs = handlerArgs
    
def buildMenus():
    Menu("Classifier", None, [
        Option("1", "Compile from source", toggle=False),
        Option("i", "Install", handler=Classifiers.SVMMultiClassClassifier.install),
        Option("s", "Skip")],
        svmMenuInitializer)
       
    Menu("Install Directory", None, [
        Option("1", "Change DATAPATH", dataInput="defaultInstallDir"),
        Option("2", "Change TEES_SETTINGS", dataInput="configFilePath"),
        Option("c", "Continue", "Classifier", isDefault=True, handler=initLocalSettings)],
        pathMenuInitializer)

    Menu("Configure TEES", 
        """
        Welcome to using the Turku Event Extraction System (TEES)! In order to work, TEES
        depends on a number of other programs, which have to be set up before use.
        
        The classifier (1) is required for all uses of the system. The models (2) are 
        required for predicting events and together with the preprocessing tools (4)
        can be used on any unprocessed text. The corpora (3) are used for testing the 
        performance of a model or for training a new model.
        
        If you are unsure which components you need, just install everything (the default choice). 
        You can also rerun configure.py at any time later to install missing components.
        
        To make a choice, type the option's key and press enter, or just press enter for the
        default option. The '*' sign indicates the default option and brackets a selectable one.
        """,
        [
        Option("1", "Install classifier (SVM Multiclass)", toggle=True),
        Option("2", "Install models (TEES models for BioNLP'09-13 and DDI'11-13)", toggle=True),
        Option("3", "Install corpora (BioNLP'09-13 and DDI'11-13)", toggle=True),
        Option("4", "Install preprocessing tools (BANNER, BLLIP parser etc)", toggle=True),
        Option("c", "Continue and install selected items", "Install Directory", isDefault=True),
        Option("q", "Quit", handler=sys.exit),
        ])

    Menu("Models", "Install TEES models\n", [
        Option("1", "Redownload already downloaded files", toggle=False),
        Option.SPACE,
        Option("i", "Install", isDefault=True),
        Option("s", "Skip")],
        modelsMenuInitializer)
    
    Menu("Corpora", "Install corpora\n", [
        Option("1", "Redownload already downloaded files", toggle=False),
        Option.SPACE,
        Option("2", "Install BioNLP'11 corpora", toggle=False),
        Option("3", "Install BioNLP'09 (GENIA) corpus", toggle=False),
        Option("4", "Install DDI'11 (Drug-Drug Interactions) corpus", toggle=False),
        Option.SPACE,
        Option("5", "Install BioNLP'13 corpora", toggle=False),
        Option("6", "Install DDI'13 (Drug-Drug Interactions) corpus", toggle=False),
        Option.SPACE,
        Option("7", "Install BioNLP evaluators", toggle=False),
        Option.SPACE,
        Option("i", "Install", isDefault=True),
        Option("s", "Skip")],
        corpusMenuInitializer)
    
    Menu("Tools", 
         """
         The tools are required for processing unannotated text and can
         be used as part of TEES, or independently through their wrappers. For
         information and usage conditions, see https://github.com/jbjorne/TEES/wiki/Licenses.
         Some of the tools need to be compiled from source, this will take a while.
         
         The external tools used by TEES are:
         
         The GENIA Sentence Splitter of Tokyo University (Tsuruoka Y. et. al.)
         
         The BANNER named entity recognizer by Robert Leaman et. al.
         
         The BLLIP parser of Brown University (Charniak E., Johnson M. et. al.)
         
         The Stanford Parser of the Stanford Natural Language Processing Group
         """, 
         [
        Option("1", "Redownload already downloaded files", toggle=False),
        Option.SPACE,
        Option("2", "Install GENIA Sentence Splitter", toggle=False),
        Option("3", "Install BANNER named entity recognizer", toggle=False),
        Option("4", "Install BLLIP parser", toggle=False),
        Option("5", "Install Stanford Parser", toggle=False),
        Option.SPACE,
        Option("i", "Install", isDefault=True),
        Option("s", "Skip")],
        toolsMenuInitializer)

    return "Configure TEES"

def configure(installDir=None, localSettings=None, auto=False, width=80, clear=False, onError="ASK"):
    Menu.system.width = width
    Menu.system.progArgs = {}
    Menu.system.progArgs["installDir"] = installDir
    Menu.system.progArgs["localSettings"] = localSettings
    Menu.system.progArgs["clearInstallDir"] = clear
    Menu.system.onException = onError
    Menu.system.run(buildMenus())
    Menu.system.finalize()

if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        pass

    optparser = OptionParser(usage="%prog [options]\nConfigure TEES")
    optparser.add_option("-i", "--installDir", default=None, dest="installDir", help="", metavar="FILE")
    optparser.add_option("-l", "--localSettings", default=None, dest="localSettings", help="", metavar="FILE")
    optparser.add_option("-w", "--width", default=80, type="int", dest="width", help="")
    optparser.add_option("--auto", default=False, action="store_true", dest="auto", help="")
    optparser.add_option("--clearInstallDir", default=False, action="store_true", dest="clearInstallDir", help="")
    optparser.add_option("--onError", default="ASK", dest="onError", help="ASK, IGNORE or EXIT")
    (options, args) = optparser.parse_args()
    assert options.onError in ["ASK", "IGNORE", "EXIT"]

    try:
        configure(options.installDir, options.localSettings, options.auto, options.width, options.clearInstallDir, options.onError)
    except KeyboardInterrupt:
        # User interupted the program, exit gracefully
        sys.exit(0)
#    Menu.system.width = options.width
#    Menu.system.progArgs = {}
#    Menu.system.progArgs["installDir"] = options.installDir
#    Menu.system.progArgs["localSettings"] = options.localSettings
#    Menu.system.progArgs["clearInstallDir"] = options.clearInstallDir
#    Menu.system.run(buildMenus())
