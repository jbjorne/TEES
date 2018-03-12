import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils
import json

def convertXML(xml, outPath):
    xml = ETUtils.ETFromObj(xml)
    corpusObj = {"name":None, "documents":[]}
    root = xml.getroot()
    for document in root.getiterator("document"):
        docObj = {x:document.get(x) for x in document.attrib.keys()}
        docObj["sentences"] = []
        corpusObj["documents"].append(docObj)
        for sentence in document.getiterator("sentence"):
            sentObj = {x:sentence.get(x) for x in sentence.attrib.keys()}
            docObj["sentences"].append(sentObj)
    with open(outPath, "rt") as f:
        json.dump(corpusObj, f, indent=2, sort_keys=True)
    
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n.")
    optparser.add_option("-i", "--input", default=None, help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, help="Corpus in interaction xml format", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    convertXML(options.input, options.output)