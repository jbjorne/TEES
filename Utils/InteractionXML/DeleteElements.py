import sys, os, copy
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict
import types

def getEmptyCorpus(xml, deletionRules=None, scope="all"):
    """
    A convenience function for getting an empty corpus, useful for testing for information leaks
    in the event extraction process.
    """
    if type(xml) in types.StringTypes:
        # XML is read from disk, so it's a new copy and can be safely modified
        xml = ETUtils.ETFromObj(xml)
    else:
        # XML is already an object in memory. To prevent problems with other users of it, a copy
        # is created before deleting elements.
        xml = copy.deepcopy(xml)
    if deletionRules == None: # use default rules for BioNLP Shared Task
        # We remove all interactions, and all entities that are not named entities. This leaves only
        # the gold standard protein/gene names
        print >> sys.stderr, "Using deletion rule set '" + str(scope) + "'"
        if scope == "all":
            deletionRules = {"interaction":{},"entity":{}}
        elif scope == "non-given":
            deletionRules = {"interaction":{},"entity":{"given":(None, "False")}}
        elif scope == "interactions":
            deletionRules = {"interaction":{}}
        else:
            raise Exception("Unknown scope '" + str(scope) + "'")
    # Remove elements and return the emptied XML
    return processCorpus(xml, None, deletionRules)
    
def removeElements(parent, rules, reverse=False, countsByType=None):
    if countsByType == None:
        countsByType = defaultdict(int)
    toRemove = []
    for element in parent:
        attrType = {}
        if element.tag in rules:
            remove = True
            if rules[element.tag] != None and len(rules[element.tag]) > 0:
                for attrName in rules[element.tag]:
                    if element.get(attrName) not in rules[element.tag][attrName]:
                        remove = False
                        break
                    else:
                        if attrName not in attrType:
                            attrType[attrName] = set()
                        attrType[attrName].add(element.get(attrName))
            if reverse:
                remove = not remove
            if remove:
                toRemove.append(element)
                countsByType[element.tag + " " + str(attrType)] += 1
        else:
            removeElements(element, rules, reverse, countsByType)
    for element in toRemove:
        parent.remove(element)

def processCorpus(input, output, rules, reverse=False):
    print >> sys.stderr, "Deleting elements, rules =", rules
    print >> sys.stderr, "Loading corpus file", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    countsByType = defaultdict(int)
    removeElements(corpusRoot, rules, reverse, countsByType)
    
    print >> sys.stderr, "Deleted elements"
    for k in sorted(countsByType.keys()):
        print >> sys.stderr, "  " + k + ":", countsByType[k]
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

if __name__=="__main__":
    print >> sys.stderr, "##### Delete Elements #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-r", "--rules", default=None, dest="rules", help="dictionary of python dictionaries with attribute:value pairs.")    
    optparser.add_option("-v", "--reverse", default=False, dest="reverse", action="store_true", help="")    
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)

    # Rules e.g. "{\"pair\":{},\"interaction\":{},\"entity\":{\"given\":\"False\"}}"
    rules = eval(options.rules)
    print >> sys.stderr, "Rules:", rules
    processCorpus(options.input, options.output, rules, options.reverse)
