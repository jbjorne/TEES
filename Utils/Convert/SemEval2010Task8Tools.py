import sys, os
import shutil
from Utils.ElementTreeUtils import ETFromObj
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.Settings as Settings
import Utils.Download
import tempfile
import zipfile
import subprocess

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

def getConfDict(conf):
    assert conf != None
    conf = [x.split(":") for x in conf.split(",")]
    return dict((key, value) for (key, value) in conf)

def getRelation(interactions):
    assert len(interactions) in (0,1,2)
    # Remove negatives
    interactions = [x for x in interactions if x.get("type") != "neg"]
    # Check for the undirected "Other" class examples
    otherCount = sum([1 for x in interactions if x.get("type") == "Other"])
    if otherCount == len(interactions):
        {"type":"Other", "e1":None, "e2":None} 
    if len(interactions) == 0:
        return None
    elif len(interactions) == 1:
        return readInteraction(interactions[0])
    else:
        i1 = interactions[0]
        i2 = interactions[1]
        # Prefer non-Other type interactions
        if i1["type"] != "Other" and i2["type"] == "Other":
            return readInteraction(i1)
        elif i1["type"] == "Other" and i2["type"] != "Other":
            return readInteraction(i2)
        # Pick the stronger one
        conf1 = getConfDict(i1.get("conf"))
        conf2 = getConfDict(i2.get("conf"))
        if conf1[i1.get("type")] > conf2[i2.get("type")]:
            return readInteraction(i1)
        else:
            return readInteraction(i2)

def exportRelations(xml, outPath):
    xml = ETFromObj(xml).getroot()
    outFile = open(outPath, "wt")
    for sentence in xml.getiterator("sentence"):
        origId = sentence.get("origId")
        assert origId != None and origId.isdigit()
        interactions = [x for x in sentence.findall("interaction")]
        rel = getRelation(interactions)
        if rel != None:
            outFile.write(origId + "\t" + rel["type"])
            if rel["e1"] != None and rel["e2"] != None:
                outFile.write("(" + rel["e1"] + "," + rel["e2"] + ")")
            outFile.write("\n")

def runPL(programPath, f1Path=None, f2Path=None, silent=False):
    command = "perl " + programPath
    if f1Path != None:
        command += " " + f1Path
    if f2Path != None:
        command += " " + f2Path
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        print >> sys.stderr, "".join(stderrLines)
        print >> sys.stderr, "".join(stdoutLines)

def evaluate(inputXML, goldXML):
    install()
    tempDir = os.path.join(tempfile.gettempdir(), "SE10T8_evaluator")
    basePath = "SemEval2010_task8_all_data/SemEval2010_task8_scorer-v1.2/"
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
    inputPath = os.path.join(tempDir, "input.txt")
    goldPath = os.path.join(tempDir, "gold.txt")
    for filePath in (inputPath, goldPath):
        if os.path.exists(filePath):
            os.remove(filePath)
    exportRelations(inputXML, inputPath)
    exportRelations(goldXML, goldPath)
    runPL("")

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