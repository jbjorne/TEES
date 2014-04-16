import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Menu
import Utils.Settings as Settings

def finalizeInstall(programs, testCommand={}, programDir=None, settings={}, updateLocalSettings=False):
    installOK = checkPrograms(programs, testCommand, programDir)
    if installOK:
        setVariable = updateLocalSettings
    else:
        print >> sys.stderr, "All programs may not have been installed correctly"
        print >> sys.stderr, "Do not use the following settings if not sure:"
        setVariable = False
    for key in sorted(settings.keys()):
        if settings[key] != None:
            #raise Exception("Local setting " + str(key) + " is undefined")
            Settings.setLocal(key, settings[key], setVariable)
        else:
            print >> sys.stderr, "Warning, local setting " + str(key) + " is undefined"
    if not installOK:
        raise Exception("Error installing programs: " + ", ".join(programs))

def checkReturnCode(code):
    if code != 0:
        print >> sys.stderr, "*** Non-zero return code", str(code) + ", program may not be working."
        return False
    else:
        print >> sys.stderr, "*** Return code", str(code) + ", program appears to be working."
        return True

def checkPrograms(programs, testCommand={}, programDir=None, combineResults=True):
    if testCommand == None:
        testCommand = {}
    if programDir != None:
        cwd = os.getcwd()
        os.chdir(programDir)
    status = {}
    for program in programs:
        print >> sys.stderr, "*** Testing", program, "..."
        command = program + " -v"
        if program in testCommand:
            command = testCommand[program]
        status[program] = checkReturnCode(os.system(command))
    if programDir != None:
        os.chdir(cwd)
    if combineResults:
        return not False in status.values()
    else:
        return status

def testPrograms(dependentProgramName, programs, testCommand={}):
    print >> sys.stderr, "Testing programs", programs
    # check program status
    status = checkPrograms(programs, testCommand, combineResults=False)
    # if there is a problem, show a menu
    if False in status.values():
        menu = Utils.Menu.Menu("Missing programs", "", 
            [Utils.Menu.Option("r", "Retry and check again program status"),
            Utils.Menu.Option("c", "Continue"), 
            Utils.Menu.Option("q", "Quit", isDefault=True, handler=sys.exit, handlerArgs=[1])], 
            addToSystem=False, initializer=initProgramTestMenu)
        menu.status = status # no need to check on the first show of the menu
        while menu.prevChoice == None or menu.prevChoice == "r":
            menu.programName = dependentProgramName
            menu.programs = programs
            menu.testCommand = testCommand
            menu.show()
            menu.status = None

def initProgramTestMenu(menu, prevMenu):
    # Check program status if this hasn't been done yet
    if menu.status == None:
        menu.status = checkPrograms(menu.programs, menu.testCommand, combineResults=False)
    # Explain situation
    if False in menu.status.values():
        if menu.system.auto:
            menu.setDefault("q") # avoid getting in a loop
        else:
            menu.setDefault("r")
        menu.text = """
        Some programs required for installing MAIN_PROGRAM may not be present.
        The current status of required programs is:
        
        """
    else: # ready to continue
        menu.setDefault("c")
        menu.text = """
        All programs required for installing MAIN_PROGRAM are present.
        The current status of required programs is:
        
        """
    # Show program status
    for program in menu.programs:
        menu.text += program
        if menu.status[program]:
            menu.text += ":OK "
        else:
            menu.text += ":ERROR "
    # Recommend option
    if False in menu.status.values():
        menu.text += """
        
        These programs are most likely available through your operating system's
        package manager. You can leave this configuration program open, while you
        install the missing components. Afterwards, check the status again (r).
        
        You can also continue installing directly (c), but then it may not be
        possible to install MAIN_PROGRAM.
        """
    else:
        menu.text += """
        
        Please continue installation by choosing (c).
        """
    menu.text = menu.text.replace("MAIN_PROGRAM", menu.programName)

    