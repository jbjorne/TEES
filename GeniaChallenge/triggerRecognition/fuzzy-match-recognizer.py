#import tre #fuzzy text match

import re
try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET

import cElementTreeUtils as ETUtils
import sys

from optparse import OptionParser

def buildRegexStr(wrdSet,boundaryStart=True,boundaryEnd=True):
    """Builds a compilable regular expression string out of the wordset"""
    strPat="%s"
    if boundaryStart:
        strPat="\\b"+strPat
    if boundaryEnd:
        strPat=strPat+"\\b"
    return "|".join(strPat%w for w in wrdSet)

def buildRegex(listLines):
    wrdSet=set()
    for line in listLines:
        line=line.strip()
        if not line:
            continue
        wrdSet.add(line)
    regexStr=buildRegexStr(wrdSet)
    regex=re.compile(regexStr,re.I)
    return regex

def matchSentence(sNode,regex):
    sTxt=sNode.get("text")
    eNodes=[] #here I gather the <entity> nodes
    for match in regex.finditer(sTxt):
        start=match.start()
        end=match.end()-1
        eNode=ET.Element("entity")
        eNode.set("charOffset","%d-%d"%(start,end))

def matchAll(listLines,xmlTree):
    regex=buildRegex(listLines)
    for sNode in xmlTree.getiterator("sentence"):
        matchSentence(sNode,regex)

def buildlist(fileIn):
    strDict={} #key: (string) value: dict:type->count
    tree=ET.parse(fileIn).getroot()
    for entNode in tree.getiterator("entity"):
        if entNode.get("isName")=="True":
            continue
        trigStr=entNode.get("text").lower()
        trigType=entNode.get("type")
        if trigStr not in strDict:
            strDict[trigStr]={}
        strDict[trigStr][trigType]=strDict[trigStr].get(trigType,0)+1
    #Now I have the dictionary... now let's see some stats
    for trigStr,typeDict in strDict.items():
        if len(typeDict)>1:
            print trigStr,typeDict
    

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("--buildlist", dest="buildlist",action="store_true",default=False,help="list all interaction expressions from an input xml to stdout")
    parser.add_option("--list", dest="list",action="store",default=None,help="file with the list of strings to recognize")
#     parser.add_option("-q", "--quiet",
#                       action="store_false", dest="verbose", default=True,
#                       help="don't print status messages to stdout")

    (options, args) = parser.parse_args()

    if options.buildlist:
        buildlist(sys.stdin)
        sys.exit(0)
    if options.list:
        f=open(options.list,"rt")
        tree=ET.parse(sys.stdin).getroot()
        matchAll(f,tree)
        f.close()
        
