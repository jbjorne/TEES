import sys, os
from collections import defaultdict
sysPath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(sysPath)
import Utils.Settings as Settings
import Utils.ElementTreeUtils as ETUtils
import Catenate
import DeleteElements

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

def mergeCorpora(corpusIds, outputId, inputDir, outDir):
    merged = Catenate.catenateElements(corpusIds, inputDir)
    for dataSet in ("devel", "train"):
        renameElements(merged[dataSet].getroot(), {"Localization":"Lives_In", 
                             "Host":"Habitat", 
                             "HostPart":"Habitat",
                             "Food":"Habitat",
                             "Soil":"Habitat",
                             "Medical":"Habitat",
                             "Water":"Habitat",
                             "Bacterium":"Bacteria"})
        DeleteElements.removeElements(merged[dataSet].getroot(), {"interaction":{"type":"PartOf"}})
        if outDir != None:
            outPath = os.path.join(outDir, outputId + "-" + dataSet + ".xml")
            print "Writing set", dataSet, "to", outPath
            ETUtils.write(merged[dataSet].getroot(), outPath)
        
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-c", "--corpusIds", default="BB11,BB13T2,BB_EVENT_16", help="Datasets to process")
    optparser.add_option("-i", "--inDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-o", "--outDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-t", "--tag", default="BBCAT", help="Parse with preprocessor")
    (options, args) = optparser.parse_args()
    
    mergeCorpora(options.corpusIds.split(","), options.tag, options.inDir, options.outDir)
