import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict

def getEPIBaseType(eType):
    if not isNegatableEPITrigger(eType):
        return eType

    preTag = ""
    if "_" in eType:
        preTag, eType = eType.split("_")
    eType = eType.replace("De", "").replace("de", "")
    if preTag != "":
        return preTag + "_" + eType
    else:
        if eType[0].islower():
            eType = eType[0].upper() + eType[1:]
        return eType

def negateType(eType):
    preTag = ""
    if "_" in eType:
        preTag, eType = eType.split("_")
    eType = eType.lower()
    if preTag != "":
        return preTag + "_" + "de" + eType
    else:
        return "De" + eType

def isNegatableEPITrigger(eType):
    return eType in ["Phosphorylation",
                     "Dephosphorylation",
                     "Hydroxylation",
                     "Dehydroxylation",
                     "Ubiquitination",
                     "Deubiquitination",
                     "DNA_methylation",
                     "DNA_demethylation",
                     "Glycosylation",
                     "Deglycosylation",
                     "Acetylation",
                     "Deacetylation",
                     "Methylation",
                     "Demethylation"]
                     #"Catalysis"]

def determineNewType(eType, eText):
    assert eText != None
    classNames = eType.split("---")
    newNames = set()
    for className in classNames:
        newNames.add(getNewType(className, eText))
    return "---".join(sorted(list(newNames)))
    
def getNewType(eType, eText):    
    if not isNegatableEPITrigger(eType):
        return eType
    eBaseType = getEPIBaseType(eType)
    eTextLower = eText.lower()
    if "remov" in eTextLower:
        eNewType = negateType(eBaseType)
    elif "loss" in eTextLower:
        eNewType = negateType(eBaseType)
    elif "erasure" in eTextLower:
        eNewType = negateType(eBaseType)
    #elif eText.startswith("hypo"):
    #    eNewType = negateType(eBaseType)
    elif eTextLower.startswith("de"):
        eNewType = negateType(eBaseType)
    else:
        eNewType = eBaseType
    return eNewType

def negateEvents(input, output=None, verbose=False):
    if not (ET.iselement(input) and input.tag == "sentence"):
        print >> sys.stderr, "Loading corpus file", input
        corpusTree = ETUtils.ETFromObj(input)
        corpusRoot = corpusTree.getroot()
    
    if not (ET.iselement(input) and input.tag == "sentence"):
        sentences = corpusRoot.getiterator("sentence")
    else:
        sentences = [input]
    counts = defaultdict(int)
    for sentence in sentences:
        for entity in sentence.findall("entity"):
            counts["all-entities"] += 1
            eType = entity.get("type")
            if not isNegatableEPITrigger(eType):
                counts["out-of-scope"] += 1
                continue
            eBaseType = getEPIBaseType(eType)
            eText = entity.get("text").lower()
            eNewType = determineNewType(eType, eText)
        
            # Insert changed charOffset
            counts["entities"] += 1
            if verbose:
                print "Entity", entity.get("id"), [entity.get("text")], [eType, eBaseType, eNewType],
            if eNewType != eBaseType:
                counts["negated"] += 1
                if verbose: print "NEGATED",
            if eNewType == eType:
                counts["correct"] += 1
                if verbose: print "CORRECT"
            else:
                counts["incorrect"] += 1
                if eNewType == eBaseType:
                    counts["incorrect-pos"] += 1
                else:
                    counts["incorrect-neg"] += 1
                if verbose: print "INCORRECT"
            entity.set("type", eNewType)
    if verbose:
        print counts
    
    if not (ET.iselement(input) and input.tag == "sentence"):
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        return corpusTree                    

if __name__=="__main__":
    print >> sys.stderr, "##### Extend Triggers #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    #assert(options.output != None)
    
    negateEvents(options.input, options.output, verbose=options.debug)
