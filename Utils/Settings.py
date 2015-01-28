import sys, os
#print "Settings.vars", vars()
# Import global defaults
from DefaultSettings import *

def getLocalSettingsPath():
    if "TEES_SETTINGS" in os.environ: # TEES_SETTINGS may be set to DISABLED to prevent loading of local settings at import
        return os.environ["TEES_SETTINGS"]
    elif os.path.exists(DEFAULT_LOCAL_SETTINGS):
        return DEFAULT_LOCAL_SETTINGS
    else:
        return None

# Import local configuration
pathname = getLocalSettingsPath()
if pathname:
    if pathname != "DISABLED": # TEES_SETTINGS may be set to DISABLED to prevent loading of local settings at import
        import imp
        imp.load_source("TEESLocalSettings", pathname)
        # combine the settings dictionaries
        tempURL = URL
        tempEVALUATOR = EVALUATOR
        # import everything from local settings module
        exec "from TEESLocalSettings import *"
        # insert new values into the setting dictionaries
        tempURL.update(URL)
        URL = tempURL
        tempEVALUATOR.update(EVALUATOR)
        EVALUATOR = tempEVALUATOR
    else:
        print >> sys.stderr, "No local settings loaded."
else:
    print >> sys.stderr, "Warning, no local settings file."
    
def setLocal(variable, value, setVariable=True):
    # the settings file must exist and must be in the path
    if not setVariable: # notify only, do not add the variable
        print >> sys.stderr, "Remember to add local setting", str(variable) + "=\"" + str(value) + "\""
        return
    assert getLocalSettingsPath() != None
    print >> sys.stderr, "Adding local setting", str(variable) + "=" + str(value),
    # define the variable in the current module
    exec (variable + " = '" + str(value) + "'") in globals()
    # read the local settings file
    f = open(getLocalSettingsPath(), "rt")
    lines = f.readlines()
    f.close()
    
    # if the variable already exists, change its value
    found = False
    for i in range(len(lines)):
        if lines[i].strip() != "" and lines[i].strip()[0] == "#": # skip comment lines
            continue
        if lines[i].split("=")[0].strip() == variable: # variable definition line
            lines[i] = variable + " = '" + str(value) + "'\n"
            print >> sys.stderr, "(updated existing value)"
            found = True
    # if the variable doesn't exist, add it to the end of the file
    if not found:
        lines.append(variable + " = '" + str(value) + "'\n")
        print >> sys.stderr, "(added variable)"
    
    # write the local settings file
    f = open(getLocalSettingsPath(), "wt")
    for line in lines:
        f.write(line)
    f.close()