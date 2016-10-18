import sys, os
import shutil
from Utils.ElementTreeUtils import ETFromObj
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.Settings as Settings
import Utils.Download
import tempfile
import zipfile

def install(destPath=None, redownload=False, updateLocalSettings=True):
    if hasattr(Settings, "SE10T8_CORPUS"): # Already installed
        return
    print >> sys.stderr, "---------------", "Downloading the SemEval 2010 Task 8 corpus", "---------------"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "resources/SemEval2010_task8_all_data.zip")
    Utils.Download.download(Settings.URL["SE10T8_CORPUS"], destPath, addName=False, clear=redownload)
    Settings.setLocal("SE10T8_CORPUS", destPath, updateLocalSettings)

def readInteraction(interaction):
    relType = interaction.get("type")
    e1 = None
    e2 = None
    if interaction.get("directed") == "True":
        e1 = interaction.get("e1").rsplit(".")[-1]
        e2 = interaction.get("e1").rsplit(".")[-1]
    elif relType != "Other":
        relType, rest = relType.strip(")").split("(")
        e1, e2 = rest.split(",")
    return {"type":relType, "e1":e1, "e2":e2}

def getRelation(interactions):
    assert len(interactions) in (0,1,2)
    interactions = [x for x in interactions if x.get("type") != "neg"]
    if len(interactions) == 0:
        return None
    elif len(interactions) == 1:
        r = readInteraction(interactions[0])
        if r["type"] != "neg":
            return r
        return None
    else:
        r1 = readInteraction(interactions[0])
        r2 = readInteraction(interactions[1])
        if r1["type"] not in ("neg", "Other") and r2["type"] in ("neg", "Other"):
            return r1
        elif r2["type"] not in ("neg", "Other") and r1["type"] in ("neg", "Other"):
            return r2
        elif r1["type"] == "neg" and r2["type"] == "neg":
            return None
        elif r1["type"] == "Other" and r2["type"] == "Other":
            return {"type":"Other", "e1":None, "e2":None}

def exportRelations(xml, outPath):
    xml = ETFromObj(xml).getroot()
    outFile = open(outPath, "wt")
    for sentence in xml.getiterator("sentence"):
        origId = sentence.get("origId")
        assert origId != None and origId.isdigit()
        interactions = [x for x in sentence.findall("interaction")]

def evaluate(inputXML, goldXML):
    install()
    tempDir = os.path.join(tempfile.gettempdir(), "SE10T8_evaluator")
    if not os.path.exists(tempDir):
        os.makedirs(tempDir)
        archive = zipfile.ZipFile(Settings.SE10T8_CORPUS, 'r')
        basePath = "SemEval2010_task8_all_data/SemEval2010_task8_scorer-v1.2/"
        for filename in ("semeval2010_task8_format_checker.pl", "semeval2010_task8_scorer-v1.2.pl"):
            source = archive.open(basePath + filename)
            target = file(os.path.join(tempDir, filename), "wt")
            shutil.copyfileobj(source, target)
            source.close()
            target.close()

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None)
    optparser.add_option("-o", "--output", default=None)
    optparser.add_option("-a", "--action", default=None)
    (options, args) = optparser.parse_args()
    
    if options.action == "install":
        install()
    elif options.action == "evaluate":
        evaluate(None, None)
    else:
        print "Unknown action", options.action