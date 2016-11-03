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
import convertSemEval2010Task8
import train

###############################################################################
# Install
###############################################################################

def install(destPath=None, redownload=False, updateLocalSettings=True):
    if hasattr(Settings, "SE10T8_CORPUS"): # Already installed
        return
    print >> sys.stderr, "---------------", "Downloading the SemEval 2010 Task 8 corpus", "---------------"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "resources/SemEval2010_task8_all_data.zip")
    Utils.Download.download(Settings.URL["SE10T8_CORPUS"], destPath, addName=False, clear=redownload)
    Settings.setLocal("SE10T8_CORPUS", destPath, updateLocalSettings)

###############################################################################
# Evaluate and Export
###############################################################################

def readInteraction(interaction):
    relType = interaction.get("type")
    e1 = None
    e2 = None
    if relType != "Other":
        if interaction.get("directed") == "True" and not "(" in interaction.get("type"):
            e1 = interaction.get("e1").rsplit(".")[-1]
            e2 = interaction.get("e2").rsplit(".")[-1]
        else: # undirected or REVERSE_POS
            assert ")" in relType, interaction.attrib
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
    if otherCount == len(interactions): # all predictions are for the type "Other"
        return {"type":"Other", "e1":None, "e2":None}
    # Generate a relation from the interactions
    if len(interactions) == 0:
        return None
    elif len(interactions) == 1:
        return readInteraction(interactions[0])
    else: # The two directed predictions have to be converted into a single relation
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
        if conf1 == None and conf2 == None: # assume this is gold annotation
            assert i1.get("type").split("(")[0] == i2.get("type").split("(")[0] # check that types match except for reversing
            # The first gold interaction is for e1->e2
            assert i1.get("e1").endswith(".e1")
            assert i1.get("e2").endswith(".e2")
            return readInteraction(i1)
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
    reverseCount = 0
    for sentence in xml.getiterator("sentence"):
        origId = sentence.get("origId")
        assert origId != None and origId.isdigit()
        interactions = [x for x in sentence.findall("interaction")]
        rel = getRelation(interactions)
        if rel != None:
            if rel["type"].startswith("-"): # reversed positive interaction
                rel["e1"], rel["e2"] = rel["e2"], rel["e1"]
                rel["type"] = rel["type"][1:]
                reverseCount += 1
            outFile.write(origId + "\t" + rel["type"])
            if rel["e1"] != None and rel["e2"] != None:
                outFile.write("(" + rel["e1"] + "," + rel["e2"] + ")")
            outFile.write("\n")
    if reverseCount > 0:
        print "Reversed", reverseCount, "interactions"
    outFile.close()

def runCommand(programPath, f1Path=None, f2Path=None, silent=False):
    command = "perl " + programPath
    if f1Path != None:
        command += " " + f1Path
    if f2Path != None:
        command += " " + f2Path
    print "Running:", command
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrText = "".join(p.stderr.readlines()).strip()
    stdoutText = "".join(p.stdout.readlines()).strip()
    if not silent:
        for text in (stderrText, stdoutText):
            if text != "":
                print >> sys.stderr, text
    return stderrText, stdoutText

def evaluate(inputXML, goldXML, outPath):
    install()
    tempDir = os.path.join(tempfile.gettempdir(), "SE10T8_evaluator")
    basePath = "SemEval2010_task8_all_data/SemEval2010_task8_scorer-v1.2/"
    formatChecker = "semeval2010_task8_format_checker.pl"
    evaluator = "semeval2010_task8_scorer-v1.2.pl"
    # Uncompress the evaluator program
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
    # Remove existing answer key files
    inputPath = os.path.join(tempDir, "input.txt")
    goldPath = os.path.join(tempDir, "gold.txt")
    for filePath in (inputPath, goldPath):
        if os.path.exists(filePath):
            os.remove(filePath)
    # Save the answer keys for the current files
    print "Exporting relations from", inputPath
    exportRelations(inputXML, inputPath)
    print "Exporting relations from", goldPath
    exportRelations(goldXML, goldPath)
    # Check the answer key file format
    runCommand(os.path.join(tempDir, formatChecker), inputPath)
    runCommand(os.path.join(tempDir, formatChecker), goldPath)
    # Run the evaluator
    stderrText, stdoutText = runCommand(os.path.join(tempDir, evaluator), inputPath, goldPath)
    # Write the results
    if outPath != None:
        outFile = open(outPath, "wt")
        for text in (stderrText, stdoutText):
            outFile.write(text)
        outFile.close()

###############################################################################
# Batch Processing
###############################################################################

CORPUS_ID = "SE10T8"

def getTargets():
    targets = []
    for directed in (True, False):
        for const in ("BLLIP-BIO", "BLLIP", "STANFORD"):
            for dep in ("STANFORD", "STANFORD-CONVERT"):
                targets.append({"directed":directed, "const":const, "dep":dep})
    return targets[0:1]

def getCorpusId(target, corpusId=None):
    if corpusId == None:
        corpusId = "_".join([CORPUS_ID, ("DIR" if target["directed"] else "UNDIR"), target["const"], target["dep"]])
    return corpusId

def convert(outPath, dummy, debug=False):
    targets = getTargets()
    for target in targets:
        targetDir = os.path.join(outPath, getCorpusId(target))
        if os.path.exists(targetDir):
            print "Skipping existing target", targetDir
        else:
            print "Processing target", targetDir
            if not dummy:
                convertSemEval2010Task8.convert(inPath=None, outDir=targetDir, corpusId=CORPUS_ID, directed=target["directed"], negatives=True, preprocess=True, debug=debug, clear=False, constParser=target["const"], depParser=target["dep"], logging=True)

def predict(inPath, outPath, dummy, corpusId = None):
    targets = getTargets()
    for target in targets:
        targetCorpusId = getCorpusId(target, corpusId)
        corpusDir = inPath
        targetDir = outPath
        if corpusId == None: 
            corpusDir = os.path.join(inPath, targetCorpusId)
            targetDir = os.path.join(outPath, targetCorpusId)
        if os.path.exists(targetDir):
            print "Skipping existing target", targetDir
        else:
            print "Processing target", targetDir
            if not dummy:
                train.train(targetDir, targetCorpusId, corpusDir=corpusDir, exampleStyles={"examples":":wordnet"}, parse="McCC",
                            classifierParams={"examples":"c=1,10,100,500,1000,1500,2500,3500,4000,4500,5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000"})
                for dataset in ("devel", "test"):
                    predicted = os.path.join(targetDir, "classification-" + dataset, dataset + "-pred.xml.gz")
                    if os.path.exists(predicted):
                        gold = os.path.join(corpusDir, targetCorpusId + "-" + dataset + ".xml")
                        evaluate(predicted, gold, os.path.join(targetDir, "official-eval-" + dataset + ".txt"))

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Input file in Interaction XML format")
    optparser.add_option("-o", "--output", default=None, help="Output file, used only when exporting relations")
    optparser.add_option("-g", "--gold", default=None, help="Correct annotation file for evaluation in Interaction XML format")
    optparser.add_option("-a", "--action", default=None, help="'install', 'evaluate', 'export', 'convert' or 'predict'")
    optparser.add_option("--dummy", default=False, action="store_true", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--corpusId", default=None, help="")
    (options, args) = optparser.parse_args()
    
    if options.action == "install":
        install()
    elif options.action == "evaluate":
        evaluate(options.input, options.gold, options.output)
    elif options.action == "export":
        exportRelations(options.input, options.output)
    elif options.action == "convert":
        convert(options.output, options.dummy, options.debug)
    elif options.action == "predict":
        predict(options.input, options.output, options.dummy, options.corpusId)
    else:
        print "Unknown action", options.action