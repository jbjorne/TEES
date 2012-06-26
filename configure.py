import sys, os, shutil
import textwrap
from Utils.Menu import *
import Utils.Settings as Settings
# Classifier wrapper
import Classifiers.SVMMultiClassClassifier
# External tools wrappers
import Tools.GeniaSentenceSplitter
import Tools.BANNER
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
# Corpora
import Utils.BioNLP2011.convertBioNLP11 as convertBioNLP11
# TODO: Logging

def pathMenuInitializer(menu, prevMenu):
    nextMenus = []
    if prevMenu.optDict["1"].toggle:
        nextMenus.append("Classifier")
    if prevMenu.optDict["2"].toggle:
        nextMenus.append("Models")
    if prevMenu.optDict["3"].toggle:
        nextMenus.append("Corpora")
    if prevMenu.optDict["4"].toggle:
        nextMenus.append("Tools")
    if len(nextMenus) == 0:
        print >> sys.stderr, "Nothing to install, exiting"
        sys.exit()
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
        else:
            menu.defaultInstallDir = Settings.DATAPATH
    if os.path.exists(menu.defaultInstallDir):
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
            menu.configFilePath = os.path.join(defaultInstallDir, "LocalSettings.py")
            if os.path.exists(menu.configFilePath):
                """
                The "TEES_SETTINGS" environment variable is not set, but a configuration file has been
                found in the default location. This installation program will use the existing
                file, and by default install only missing components.
                """     
            else:
                """
                The "TEES_SETTINGS" environment variable is not set, so a new local configuration file
                will be created.
                """
    #menu.text += "TEES_SETTINGS = " + menu.configFilePath + "\n\n"
    menu.system.setAttr("defaultInstallDir", menu.defaultInstallDir)
    menu.system.setAttr("configFilePath", menu.configFilePath)
    menu.optDict["c"].handlerArgs = [menu.configFilePath]
    
def initLocalSettings(filename):
    if os.path.exists(filename):
        print >> sys.stderr, "Using existing local settings file", filename
        return
    print >> sys.stderr, "Initializing local settings file", filename
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
    CHARNIAK_JOHNSON_PARSER_DIR = None # The BLLIP parser directory
    MCCLOSKY_BIOPARSINGMODEL_DIR = None # The McClosky BioModel directory
    STANFORD_PARSER_DIR = None # The Stanford parser directory
    
    # BioNLP Shared Task evaluators
    
    # Data
    CORPUS_DIR = None # Directory for the corpus XML-files
    TEES_MODEL_DIR = None # Directory for the official TEES models
    """.replace("    ", ""))
    f.close()
    # Reset local settings
    os.environ["TEES_SETTINGS"] = filename
    reload(Settings)

def checkInstallPath(menu, menuVariable, setting, installSubDir, defaultInstallKey="i", defaultSkipKey="s"):
    if getattr(menu, menuVariable) == None:
        setattr(menu, menuVariable, menu.system.defaultInstallDir + "/" + installSubDir)
    if hasattr(Settings, setting) and getattr(Settings, setting) != None:
        menu.text += "The " + setting + " setting is already configured, so the default option is to skip installing.\n\n"
        menu.text += setting + "=" + getattr(Settings, setting)
        menu.setDefault(defaultSkipKey)
        return False
    else:
        menu.setDefault(defaultInstallKey)
        return True

def checkCorpusInstall(menu, corpus, installKey="i"):
    # If CORPUS_DIR setting is not set, the default is to install everything
    if not hasattr(Settings, "CORPUS_DIR") or getattr(Settings, "CORPUS_DIR") == None:
        menu.setDefault(installKey)
        return True
    # CORPUS_DIR is set, so check if the corpus is installed
    allFound = True # check for all corpus subsets
    for dataSet in ["-train.xml", "-devel.xml", "-test.xml"]:
        if os.path.exists(Settings.CORPUS_DIR + "/" + corpus + dataSet):
            allFound = False
            break
    if allFound: # if corpus files are present, installing this corpora can be skipped
        return True
    else: # if a corpus file is missing, mark it to be installed
        menu.setDefault(installKey)
        return False

def svmMenuInitializer(menu, prevMenu):
    menu.text = """
    TEES uses the SVM Multiclass classifer by Thorsten Joachims for all 
    classification tasks. You can optionally choose to compile it from 
    source if the precompiled Linux-binary does not work on your system.
    """
    checkInstallPath(menu, "svmInstallDir", "SVM_MULTICLASS_DIR", "SVMMultiClass")
    menu.optDict["i"].handlerArgs = [menu.svmInstallDir, os.path.join(menu.system.defaultInstallDir, "tools/download"), True, menu.optDict["1"].toggle, True]

def toolsMenuInitializer(menu, prevMenu):
    handlers = []
    handlerArgs = []
    redownload = menu.optDict["1"].toggle
    if menu.optDict["2"].toggle or checkInstallPath(menu, "geniassInstallDir", "GENIA_SENTENCE_SPLITTER_DIR", "geniass"):
        menu.optDict["2"].toggle = True
        handlers.append(Tools.GeniaSentenceSplitter.install)
        handlerArgs.append([menu.geniassInstallDir, os.path.join(menu.system.defaultInstallDir, "tools/download"), redownload])  
    if menu.optDict["3"].toggle or checkInstallPath(menu, "bannerInstallDir", "BANNER_DIR", "BANNER"):
        menu.optDict["3"].toggle = True
        handlers.append(Tools.BANNER.install)
        handlerArgs.append([menu.bannerInstallDir, os.path.join(menu.system.defaultInstallDir, "tools/download"), redownload])  
    menu.optDict["i"].handler = handlers
    menu.optDict["i"].handlerArgs = handlerArgs

def corpusMenuInitializer(menu, prevMenu):
    menu.text = """
    The corpora are used for training new models and testing existing
    models. The corpora installable here are from the two BioNLP Shared
    Tasks (BioNLP'09 and BioNLP'11) on Event Extraction (organized by 
    University of Tokyo), and the First Challenge Task: Drug-Drug Interaction 
    Extraction (DDI'11, organized by Universidad Carlos III de Madrid).
    
    The corpora will be downloaded from their publishers' pages, then converted
    to the Interaction XML format used by TEES. It is also recommended to download 
    the official Shared Task evaluator programs, which will be used by TEES when 
    training or testing on those corpora.
    """
    # Set the installation path
    if menu.corpusDir == None:
        if not hasattr(Settings, "CORPUS_DIR") or getattr(Settings, "CORPUS_DIR") == None:
            menu.corpusDir = menu.system.defaultInstallDir
        else:
            menu.corpusDir = Settings.CORPUS_DIR
    # Mark "skip" as default option, this will be re-marked as install if a corpus is missing
    menu.setDefault("s")
    handlers = []
    handlerArgs = []
    # Check which corpora need to be installed
    redownload = menu.optDict["1"].toggle
    corporaToInstall = []
    for item, corpus in [("4", "GE"), ("5", "EPI"), ("6", "ID"), ("7", "BB"), ("8", "BI")]:
        if menu.optDict[item].toggle or checkCorpusInstall(menu, corpus):
            menu.optDict[item].toggle = True
            corporaToInstall.append(corpus)
    if len(corporaToInstall) > 0: # All BioNLP'11 corpora can be installed with one command
        handlers.append(convertBioNLP11.convert)
        handlerArgs.append([corporaToInstall, menu.corpusDir + "/corpora", menu.corpusDir + "/download", redownload, False, False])
    # Add the handlers to install option
    menu.optDict["i"].handler = handlers
    menu.optDict["i"].handlerArgs = handlerArgs
    
def buildMenus():
    Menu("Classifier", None, [
        Option("1", "Compile from source", toggle=False),
        Option("2", "Change install directory", dataInput="svmInstallDir"),
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
        
        The classifier (1) is required for all uses of the system, and together with the official
        models (2), can be used to predict events for datasets such as the Shared Task corpora (3), or if
        preprocessing tools are installed (4), for any unprocessed text.
        
        If you are unsure which components you need, just install everything (the default choice). 
        You can also rerun configure.py at any time later to install missing components.
        """, 
        [
        Option("1", "Install classifier (SVM Multiclass)", toggle=True),
        Option("2", "Install models (TEES models for BioNLP'11 and DDI'11)", toggle=True),
        Option("3", "Install corpora (BioNLP'11 and DDI'11)", toggle=True),
        Option("4", "Install preprocessing tools (BANNER, BLLIP parser etc)", toggle=True),
        Option("c", "Continue and install selected items", "Install Directory", isDefault=True),
        Option("q", "Quit", handler=sys.exit),
        ])

    Menu("Models", "Not implemented yet\n", [
        Option("i", "Install", isDefault=True),
        Option("s", "Skip")])
    
    Menu("Corpora", "Install corpora\n", [
        Option("1", "Redownload already downloaded files", toggle=False),
        Option("2", "Change CORPUS_DIR", dataInput="corpusDir"),
        Option("3", "Change BioNLP'11 evaluator directory", dataInput="evaluatorDir"),
        Option.SPACE,
        Option("4", "Install BioNLP'11 GE (GENIA) corpus", toggle=False),
        Option("5", "Install BioNLP'11 EPI (epigenetics and PTMs) corpus", toggle=False),
        Option("6", "Install BioNLP'11 ID (infectious diseases) corpus", toggle=False),
        Option("7", "Install BioNLP'11 BB (bacteria biotopes) corpus", toggle=False),
        Option("8", "Install BioNLP'11 BI (bacteria/gene interactions) corpus", toggle=False),
        Option("9", "Install BioNLP'11 REL (entity relations) corpus", toggle=False),
        Option("10", "Install BioNLP'11 REN (gene renaming) corpus", toggle=False),
        Option("11", "Install BioNLP'11 CO (coreference) corpus", toggle=False),
        Option("12", "Install BioNLP'09 GE (GENIA 2009) corpus", toggle=False),
        Option("13", "Install DDI'11 (drug-drug interactions) corpus", toggle=False),
        Option.SPACE,
        Option("14", "Install BioNLP'11 evaluators", toggle=False),
        Option.SPACE,
        Option("i", "Install", isDefault=True),
        Option("s", "Skip")],
        corpusMenuInitializer)
    
    Menu("Tools", "Not implemented yet\n", [
        Option("1", "Redownload already downloaded files", toggle=False),
        Option.SPACE,
        Option("2", "Install GENIA Sentence Splitter", toggle=False),
        Option("3", "Install BANNER named entity recognizer", toggle=False),
        Option("4", "Install BLLIP parser", toggle=False),
        Option("5", "Install Stanford Parser", toggle=False),
        Option.SPACE,
        Option("6", "Change GENIA_SENTENCE_SPLITTER_DIR", dataInput="geniassInstallDir"),
        Option("7", "Change BANNER_DIR", dataInput="bannerInstallDir"),
        Option("8", "Change BLLIP_PARSER_DIR", dataInput="bllipInstallDir"),
        Option("9", "Change STANFORD_PARSER_DIR", dataInput="stanfordInstallDir"),
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
    Menu.system.run(buildMenus())
    Menu.system.onException = onError

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
    
    configure(options.installDir, options.localSettings, options.auto, options.width, options.clearInstallDir, options.onError)
#    Menu.system.width = options.width
#    Menu.system.progArgs = {}
#    Menu.system.progArgs["installDir"] = options.installDir
#    Menu.system.progArgs["localSettings"] = options.localSettings
#    Menu.system.progArgs["clearInstallDir"] = options.clearInstallDir
#    Menu.system.run(buildMenus())
