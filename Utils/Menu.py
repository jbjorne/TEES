import sys
import textwrap

class Menu:
    def __init__(self, title, text, options=None):
        self.title = title
        self.text = text
        self.options = options
        self.optDict = {}
        for option in options:
            assert option.key not in self.optDict
            self.optDict[option.key] = option
        self.width = 80
        self.doAlignText = True 
    
    def printBorder(self, showTitle=False):
        if showTitle:
            border = ((self.width - len(self.title) - 2) / 2) * "="
            titleBar = border + " " + self.title + " " + border
            titleBar += (len(titleBar) - self.width) * "="
            print >> sys.stderr, titleBar
        else:
            print >> sys.stderr, self.width * "="
    
    def printOptionBorder(self):
        print >> sys.stderr, self.width * "-"
    
    def printOptions(self):
        for option in self.options:
             option.show()

    def getInput(self, items=None):
        choice = None
        default = None
        for item in items:
            if item.isDefault:
                default = item
                break
        while choice == None:
            print >> sys.stderr, ">",
            choice = raw_input()
            #print "Choice", type(choice), len(choice), "End"
            if choice.strip() == "" and default != None:
                return default.key
            elif items != None and choice.lower() in self.optDict.keys():
                choiceLower = choice.lower()
                if self.optDict[choiceLower].toggle != None:
                    self.optDict[choiceLower].toggle = not self.optDict[choiceLower].toggle
                    self.show(askInput=False)
                    choice = None
                else:
                    return choice
            elif items == None:
                return choice
            else:
                print >> sys.stderr, "Unknown option", choice
                choice = None
    
    def alignText(self, text):
        lines = text.split("\n")
        paragraphs = [""]
        for line in lines:
            if line.strip() == "":
                paragraphs.append("")
            else:
                paragraphs[-1] += line.strip() + " "
        paragraphsToKeep = []
        for paragraph in paragraphs:
            paragraph = "\n".join(textwrap.wrap(paragraph, width=self.width))
            if paragraph.strip() != "":
                paragraphsToKeep.append(paragraph)
        return "\n\n".join(paragraphsToKeep)
                
    def show(self, askInput=True):
        self.printBorder(True)
        if self.doAlignText:
            print >> sys.stderr, self.alignText(self.text)
        else:
            print >> sys.stderr, self.text
        self.printOptionBorder()
        if self.options != None:
            self.printOptions()
        else:
            print >> sys.stderr, "Press any key to continue"
        self.printBorder()
        if askInput:
            choice = self.getInput(self.options)
            for option in self.options:
                if choice == option.key:
                    option.do()
                    break

class Option:
    def __init__(self, key, text, action=None, isDefault=False, toggle=None, actionArgs={}):
        self.key = key
        self.text = text
        self.toggle = toggle
        self.action = action
        self.actionArgs = actionArgs
        self.isDefault = isDefault
    
    def show(self, alignText=True):
        if self.isDefault:
            print >> sys.stderr, " * ",
        elif self.toggle != None:
            if self.toggle:
                print >> sys.stderr, "[X]",
            else:
                print >> sys.stderr, "[ ]",
        else:
            print >> sys.stderr, "   ",
        print >> sys.stderr, self.key + ")",
        
        print >> sys.stderr, self.text
    
    def do(self):
        assert self.action != None
        if type(self.action) == Menu:
            self.action.show()
        else:
            self.action(**self.actionArgs)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    m = Menu("Main menu", 
             "Some Text."
             [Option("Y", "Yes", None, True), Option("N", "No")])
    m.show()
