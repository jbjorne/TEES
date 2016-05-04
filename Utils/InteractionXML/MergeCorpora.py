import sys, os
from collections import defaultdict
sysPath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(sysPath)
import Utils.Settings as Settings
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import DeleteElements
import RecalculateIds

RENAME_DICT = {"Localization":"Lives_In", 
     "Host":"Habitat", 
     "HostPart":"Habitat",
     "Food":"Habitat",
     "Soil":"Habitat",
     "Medical":"Habitat",
     "Water":"Habitat",
     "Bacterium":"Bacteria"}

def catenate(inputs, target, inputDir):
    print >> sys.stderr, "##### Catenate interaction XML as elements #####"
    
    root = ET.Element("corpus", {"source":",".join(inputs)})
    tree = ET.ElementTree(root)
    for dataSet in ("devel", "train"):
        print "Processing corpus dataset", dataSet
        for input in inputs:
            if input == target and dataSet == "devel":
                print "Devel set for target", input, "not catenated"
                continue
            corpusPath = os.path.join(inputDir, input + "-" + dataSet + ".xml")
            print >> sys.stderr, "Catenating", corpusPath
            if not os.path.exists(corpusPath):
                print "Input", corpusPath, "not found"
                continue
            xml = ETUtils.ETFromObj(corpusPath)
            for document in xml.getiterator("document"):
                root.append(document)
    
    return RecalculateIds.recalculateIds(tree)

def renameElements(xml, rules):
    counts = defaultdict(int)
    for element in xml.iter():
        if element.get("type") in rules:
            counts["rules-" + element.get("type") + "/" + rules[element.get("type")]] += 1
            element.set("type", rules[element.get("type")])
        if element.tag == "interaction":
            element.set("e1Role", "Bacteria")
            element.set("e2Role", "Location")
        if element.tag == "entity":
            element.set("given", "True")
    print counts

def mergeCorpora(corpusIds, targetId, outputId, inputDir, outDir):
    merged = catenate(corpusIds, targetId, inputDir)
    renameElements(merged.getroot(), RENAME_DICT)
    DeleteElements.removeElements(merged.getroot(), {"interaction":{"type":"PartOf"}})
    if outDir != None:
        ETUtils.write(merged.getroot(), os.path.join(outDir, outputId + "-train.xml"))
        
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-c", "--corpusIds", default="BB11,BB13T2,BB_EVENT_16", help="Datasets to process")
    optparser.add_option("-a", "--targetId", default="BB_EVENT_16", help="")
    optparser.add_option("-i", "--inDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-o", "--outDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-t", "--tag", default="BBCAT", help="Parse with preprocessor")
    (options, args) = optparser.parse_args()
    
    mergeCorpora(options.corpusIds.split(","), options.targetId, options.tag, options.inDir, options.outDir)
