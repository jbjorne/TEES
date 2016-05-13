import sys, os
sysPath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(sysPath)
import Utils.Settings as Settings
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import json

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
            if element.get("e1").split(".e")[0] != element.get("e2").split(".e")[0]:
                if not "intersentence" in stats:
                    stats["intersentence"] = 0
                stats["intersentence"] += 1
    return stats

def getStatistics(corpusIds, inputDir):
    stats = {}
    for corpusId in corpusIds:
        if not corpusId in stats:
            stats[corpusId] = {"train":{}, "devel":{}, "test":{}, "total":{}}
        for dataSet in ("train", "devel", "test"):
            corpusPath = os.path.join(inputDir, corpusId + "-" + dataSet + ".xml")
            getFileStatistics(corpusPath, stats, (dataSet, "total"), corpusId)
    return stats

def getFileStatistics(filename, stats, targetSets, corpusId):
    if stats == None:
        stats = {corpusId:{x:{} for x in targetSets}}
    if not os.path.exists(filename):
        print >> sys.stderr, "Warning, cannot find", filename
        return
    print >> sys.stderr, "Processing", filename
    xml = ETUtils.ETFromObj(filename)
    for elementType in ("sentence", "document"):
        addStats(elementType, len([x for x in xml.iter(elementType)]), stats[corpusId], targetSets)
    for elementType in ("entity", "interaction"):
        elements = [x for x in xml.iter(elementType)]
        for targetSet in targetSets:
            stats[corpusId][targetSet][elementType] = addAnnotation(elements, stats[corpusId][targetSet].get(elementType))
    return stats

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Datasets to process")
    optparser.add_option("-c", "--corpora", default="BB11,BB13T2,BB_EVENT_16", help="Datasets to process")
    optparser.add_option("-d", "--inDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    (options, args) = optparser.parse_args()
    
    options.corpora = options.corpora.replace("COMPLETE", "GE09,ALL11,ALL13,ALL16")
    options.corpora = options.corpora.replace("ALL11", "GE11,EPI11,ID11,BB11,BI11,CO11,REL11,REN11")
    options.corpora = options.corpora.replace("ALL13", "GE13,CG13,PC13,GRO13,GRN13,BB13T2,BB13T3")
    options.corpora = options.corpora.replace("ALL16", "BB_EVENT_16,BB_EVENT_NER_16,SDB16")
        
    if options.input != None:
        result = getFileStatistics(options.input, None, ("file",), "file")
    else:
        result = getStatistics(options.corpora.split(","), options.inDir)
    print json.dumps(result, indent=4)