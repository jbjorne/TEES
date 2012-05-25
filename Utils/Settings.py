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
    
def setLocal(variable, value):
    # the settings file must exist and must be in the path
    assert "TEES_SETTINGS" in os.environ
    # define the variable in the current module
    exec "global " + variable
    exec "variable = " + str(value)
    # read the local settings file
    f = open(os.environ["TEES_SETTINGS"], "rt")
    lines = f.readlines()
    f.close()
    
    # if the variable already exists, change its value
    found = False
    for i in range(len(lines)):
        if lines[i].split("=")[0].strip() == variable:
            lines[i] = variable + " = " + str(value) + "\n"
            found = True
    # if the variable doesn't exist, add it to the end of the file
    if not found:
        lines.append(variable + " = " + str(value) + "\n")
    
    # write the local settings file
    f = open(os.environ["TEES_SETTINGS"], "wt")
    for line in lines:
        f.write(line)
    f.close()