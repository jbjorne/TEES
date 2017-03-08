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
import re

def mergeSets(pattern, inputDir, outPath):
    counts = defaultdict(int)
    pattern = re.compile(pattern)
    matched = sorted([x for x in os.listdir(inputDir) if pattern.match(x)])
    print "Merging input files", matched
    if len(matched) == 0:
        print "Nothing to merge"
        return
    newRoot = None
    for filename in matched:
        filePath = os.path.join(inputDir, filename)
        print "Merging file", filePath
        xml = ETUtils.ETFromObj(filePath).getroot()
        if newRoot == None:
            newRoot = ET.Element("corpus", xml.attrib)
        else:
            assert newRoot.attrib == xml.attrib
        for doc in xml.iter("document"):
            assert doc.get("set") != None, doc.attrib
            counts["set=" + doc.get("set")] += 1
            counts["set(" + filename + ")=" + doc.get("set")] += 1
        for element in xml:
            newRoot.append(element)
    print dict(counts)
    if outPath != None:
        print "Writing merged corpus to", outPath
        ETUtils.write(newRoot, outPath)
        
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-p", "--pattern", default=None, help="Datasets to process")
    optparser.add_option("-i", "--inDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-o", "--outPath", default=None, help="directory for output files")
    (options, args) = optparser.parse_args()
    
    mergeSets(options.pattern, options.inDir, options.outPath)
