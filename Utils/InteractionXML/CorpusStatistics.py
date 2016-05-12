import sys, os
sysPath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(sysPath)
import Utils.Settings as Settings
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils

def addStats(name, value, dict, tags):
    for tag in tags:
        if name not in dict[tag]:
            dict[tag][name] = 0
        dict[tag][name] += value

def addAnnotation(elements, stats):
    if stats == None:
        stats = {"total":0, "given":0, "types":{}}
    for element in elements:
        stats["total"] += 1
        if element.get("given") == "True":
            stats["given"] += 1
        if element.get("type") not in stats["types"]:
            stats["types"][element.get("type")] = 0
        stats["types"][element.get("type")] += 1
        if element.tag == "interaction":
            if element.get("e1").split(".s")[0] != element.get("e2").split(".s")[0]:
                if not "intersentence" in stats:
                    stats["intersentence"] = 0
                stats["intersentence"] += 1
    return stats

def getStatistics(corpusIds, inputDir):
    stats = []
    for corpusId in corpusIds:
        if not corpusId in stats:
            stats[corpusId] = {"train":{}, "devel":{}, "test":{}, "total":{}}
        for dataSet in ("train", "devel", "test"):
            corpusPath = os.path.join(inputDir, input + "-" + dataSet + ".xml")
            xml = ETUtils.ETFromObj(corpusPath)
            for elementType in ("sentence", "document"):
                addStats(elementType, len([x for x in xml.iter(elementType)]), stats[corpusId], (dataSet, "total"))
            for elementType in ("entity", "interaction"):
                elements = [x for x in xml.iter(elementType)]
                for targetSet in [dataSet, "total"]:
                    if not elementType in stats[corpusId][targetSet]:
                        stats[corpusId][targetSet][elementType] = {}
                    addAnnotation(elements, stats[corpusId][targetSet][elementType])
    return stats

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-c", "--corpusIds", default="BB11,BB13T2,BB_EVENT_16", help="Datasets to process")
    optparser.add_option("-i", "--inDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-o", "--outDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-t", "--tag", default="BBCAT", help="Parse with preprocessor")
    (options, args) = optparser.parse_args()
    
    print getStatistics(options.corpora, options.inDir)