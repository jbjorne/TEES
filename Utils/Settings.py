# Import global defaults
from DefaultSettings import *

# Import local configuration
import os
if "TEES_SETTINGS" in os.environ:
    import imp
    pathname = os.environ["TEES_SETTINGS"]
    imp.load_source("TEESLocalSettings", pathname)
    # import everything from local settings module
    exec "from TEESLocalSettings import *"
