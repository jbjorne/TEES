import sys, os
import shutil
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
from Utils.ElementTreeUtils import ETFromObj
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
        e2 = interaction.get("e2").rsplit(".")[-1]
    elif relType != "Other":
        relType, rest = relType.strip(")").split("(")
        e1, e2 = rest.split(",")
    return {"type":relType, "e1":e1, "e2":e2}

def getConfDict(conf):
    if conf == None:
        return None
    conf = [x.split(":") for x in conf.split(",")]
    return dict((key, value) for (key, value) in conf)

def getRelation(interactions):
    assert len(interactions) in (0,1,2)
    # Remove negatives
    interactions = [x for x in interactions if x.get("type") != "neg"]
    # Check for the undirected "Other" class examples
    otherCount = sum([1 for x in interactions if x.get("type") == "Other"])
    if otherCount == len(interactions):
        return {"type":"Other", "e1":None, "e2":None}
    if len(interactions) == 0:
        return None
    elif len(interactions) == 1:
        return readInteraction(interactions[0])
    else:
        i1 = interactions[0]
        i2 = interactions[1]
        # Prefer non-Other type interactions
        if i1.get("type") != "Other" and i2.get("type") == "Other":
            return readInteraction(i1)
        elif i1.get("type") == "Other" and i2.get("type") != "Other":
            return readInteraction(i2)
        # Pick the stronger one
        conf1 = getConfDict(i1.get("conf"))
        conf2 = getConfDict(i2.get("conf"))
        assert conf1 != None and conf2 != None, (i1.attrib, i2.attrib, otherCount, len(interactions))
        if conf1[i1.get("type")] > conf2[i2.get("type")]:
            return readInteraction(i1)
        else:
            return readInteraction(i2)

def exportRelations(xml, outPath):
    xml = ETFromObj(xml).getroot()
    assert outPath != None
    if not os.path.exists(os.path.dirname(outPath)):
        os.makedirs(outPath)
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
    outFile.close()

def runCommand(programPath, f1Path=None, f2Path=None, silent=False):
    command = "perl " + programPath
    if f1Path != None:
        command += " " + f1Path
    if f2Path != None:
        command += " " + f2Path
    print "Running:", command
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        for lines in (stderrLines, stdoutLines):
            text = "".join(lines).strip()
            if text != "":
                print >> sys.stderr, text

def evaluate(inputXML, goldXML):
    install()
    tempDir = os.path.join(tempfile.gettempdir(), "SE10T8_evaluator")
    basePath = "SemEval2010_task8_all_data/SemEval2010_task8_scorer-v1.2/"
    formatChecker = "semeval2010_task8_format_checker.pl"
    evaluator = "semeval2010_task8_scorer-v1.2.pl"
    if not os.path.exists(tempDir):
        print "Extracting the evaluator to", tempDir
        os.makedirs(tempDir)
        archive = zipfile.ZipFile(Settings.SE10T8_CORPUS, 'r')
        basePath = "SemEval2010_task8_all_data/SemEval2010_task8_scorer-v1.2/"
        for filename in (formatChecker, evaluator):
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
    print "Exporting relations from", inputPath
    exportRelations(inputXML, inputPath)
    print "Exporting relations from", goldPath
    exportRelations(goldXML, goldPath)
    runCommand(os.path.join(tempDir, formatChecker), inputPath)
    runCommand(os.path.join(tempDir, formatChecker), goldPath)
    runCommand(os.path.join(tempDir, evaluator), inputPath, goldPath)

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Input file in Interaction XML format")
    optparser.add_option("-o", "--output", default=None, help="Output file, used only when exporting relations")
    optparser.add_option("-g", "--gold", default=None, help="Correct annotation file for evaluation in Interaction XML format")
    optparser.add_option("-a", "--action", default=None, help="One of 'install', 'evaluate' or 'export'")
    (options, args) = optparser.parse_args()
    
    if options.action == "install":
        install()
    elif options.action == "evaluate":
        evaluate(options.input, options.gold)
    elif options.action == "export":
        exportRelations(options.input, options.output)
    else:
        print "Unknown action", options.action