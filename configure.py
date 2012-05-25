import sys
import textwrap
from Utils.Menu import *

def buildMenus():    
    mainMenu = Menu("Configure TEES", 
        """
        Welcome to using the Turku Event Extraction System (TEES)! In order to work, TEES
        depends on a number of other programs, which have to be set up before use.
         
        The classifier (1), SVM multiclass, is required for all uses of the system. The built-in
        models (2) allow direct classification of annotated data with one of the TEES models 
        used in a Shared Task. The corpora (3) are required e.g. for retraining and
        developing new models. Finally, the preprocessing tools (4), BANNER, BLLIP parser etc,
        are required if you want to detect events on unprocessed natural text.
        
        If you are unsure which components you need, it is recommended to install all the selected
        options. You can also rerun configure.py at any later time to install missing components.
        """, 
        [
        Option("1", "Install classifier (SVM Multiclass)", toggle=True),
        Option("2", "Install models (Official TEES models for BioNLP'11 and DDI)", toggle=True),
        Option("3", "Install corpora (BioNLP'11 and DDI)", toggle=True),
        Option("4", "Install tools (for preprocessing)", toggle=True),
        Option("c", "Continue and install selected items", None, True),
        Option("q", "Quit", sys.exit),
        ])

    dataPathMenu = Menu("Select Installation Directory",
        """
        While TEES itself can be unpacked anywhere, it always depends on a configuration file,
        the location of which is defined in the environment variable "TEES_SETTINGS"
        """, [
        Option("s", "Set the path",
               "c", "Continue", None, True)
              ]
        )

    return mainMenu

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    mainMenu = buildMenus()
    mainMenu.show()
