import sys, os, shutil
import textwrap
from Utils.Menu import *
import Utils.Settings as Settings
import Classifiers.SVMMultiClassClassifier

def pathMenuInitializer(menu, prevMenu):
    nextMenus = []
    if prevMenu.optDict["1"]:
        nextMenus.append("Classifier")
    if prevMenu.optDict["2"]:
        nextMenus.append("Models")
    if prevMenu.optDict["3"]:
        nextMenus.append("Corpora")
    if prevMenu.optDict["4"]:
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
            A configuration file already exists. This installation program will use the existing
            file, and by default install only missing components.
            """
        else:
            menu.configFilePath = os.path.join(defaultInstallDir, "LocalSettings.py")
            if os.path.exists(menu.configFilePath):
                """
                The "TEES_SETTINGS" environment variable is not set, but a configuration file has been
                found in the default location.
                """     
            else:
                """
                The "TEES_SETTINGS" environment variable is not set, so a new local configuration file
                will be created.
                """
    #menu.text += "TEES_SETTINGS = " + menu.configFilePath + "\n\n"
    menu.system.setAttr("defaultInstallDir", menu.defaultInstallDir)
    menu.system.setAttr("configFilePath", menu.configFilePath)

def svmMenuInitializer(menu, prevMenu):
    menu.text = """
    TEES uses the SVM Multiclass classifer by Thorsten Joachims for all 
    classification tasks. You can optionally choose to compile it from 
    source if the precompiled Linux-binary does not work on your system.
    """
    
    if menu.svmInstallDir == None:
        menu.svmInstallDir = os.path.join(menu.system.defaultInstallDir, "SVMMultiClass")
    if hasattr(Settings, "SVM_MULTICLASS_DIR"):
        menu.text += """
        The SVM_MULTICLASS_DIR setting is already configured,
        so the default option is to skip installing the classifier.
        
        """
        menu.text += "SVM_MULTICLASS_DIR=" + Settings.SVM_MULTICLASS_DIR
        menu.setDefault("s")
    else:
        menu.setDefault("i")
    menu.optDict["i"].handlerArgs = [menu.svmInstallDir, os.path.join(menu.system.defaultInstallDir, "tools/download"), True, menu.optDict["1"].toggle]

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
        Option("c", "Continue", "Classifier", isDefault=True)],
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

    Menu("Classifier", None, [
        Option("1", "Compile from source", toggle=False),
        Option("2", "Change install directory", dataInput="svmInstallDir"),
        Option("i", "Install", handler=Classifiers.SVMMultiClassClassifier.install),
        Option("s", "Skip")],
        svmMenuInitializer)
    
#    smvMenu = Menu("Install Classifier",
#        """
#        """,[
#        Option()
#             ])

    return "Configure TEES"

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
    optparser.add_option("--auto", default=False, action="store_true", dest="auto", help="")
    optparser.add_option("--clearInstallDir", default=False, action="store_true", dest="clearInstallDir", help="")
    (options, args) = optparser.parse_args()
    
    Menu.system.progArgs = {}
    Menu.system.progArgs["installDir"] = options.installDir
    Menu.system.progArgs["localSettings"] = options.localSettings
    Menu.system.progArgs["clearInstallDir"] = options.clearInstallDir
    Menu.system.run(buildMenus())
