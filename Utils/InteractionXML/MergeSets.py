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

def getMatchingFiles(pattern, path=None):
    if path == None:
        path = os.path.dirname(pattern)
        pattern = os.path.basename(pattern)
    pattern = re.compile(pattern)
    return sorted([x for x in os.listdir(path) if pattern.match(x)])

def mergeSets(input, corpusDir=None, output=None, allowNone=False):
    # Find the files
    if isinstance(input, dict):
        filenames = [{"path":input[x], "set":x} for x in input]
    else:
        if corpusDir == None:
            if os.path.dirname(input):
                corpusDir = os.path.dirname(input)
                input = os.path.basename(input)
            else:
                corpusDir = os.path.normpath(Settings.DATAPATH + "/corpora")
        print >> sys.stderr, "Searching for corpus files at " + corpusDir + " using pattern " + input
        filenames = [{"path":os.path.join(corpusDir, x), "set":None} for x in getMatchingFiles(input, corpusDir)]
    
    # Merge the files
    print >> sys.stderr, "Merging input files", filenames
    if len(filenames) == 0:
        if allowNone:
            print >> sys.stderr, "Nothing to merge"
            return
        else:
            raise Exception("No input files found for merging")
    newRoot = None
    counts = defaultdict(int)
    for filename in filenames:
        print >> sys.stderr, "Merging file", filename["path"]
        xml = ETUtils.ETFromObj(filename["path"]).getroot()
        if newRoot == None:
            newRoot = ET.Element("corpus", xml.attrib)
        else:
            assert newRoot.attrib == xml.attrib
        for doc in xml.iter("document"):
            assert doc.get("set") != None, doc.attrib
            if filename["set"] != None:
                assert filename["set"] == doc.get("set")
            counts["set=" + doc.get("set")] += 1
            counts["set(" + filename["path"] + ")=" + doc.get("set")] += 1
        for element in xml:
            newRoot.append(element)
    print >> sys.stderr, dict(counts)
    if output != None:
        print "Writing merged corpus to", output
        ETUtils.write(newRoot, output)
    return ET.ElementTree(newRoot)
        
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-p", "--pattern", default=None, help="Datasets to process")
    optparser.add_option("-i", "--inDir", default=None, help="directory for input files")
    optparser.add_option("-o", "--outPath", default=None, help="directory for output files")
    (options, args) = optparser.parse_args()
    
    mergeSets(options.pattern, options.inDir, options.outPath, allowNone=True)
