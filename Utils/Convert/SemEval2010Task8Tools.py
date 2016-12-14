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
import re
import csv

SPLIT_CONF = re.compile(r'(?:[^,(]|\([^)]*\))+') # split by commas outside parentheses

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
        e1 = interaction.get("e1").rsplit(".")[-1]
        e2 = interaction.get("e2").rsplit(".")[-1]
        # Check if SemEval directionality is included in the interaction type
        if interaction.get("directed") == "True" or "(" in interaction.get("type"):
            assert ")" in relType, interaction.attrib
            relType, rest = relType.strip(")").split("(")
            # In the SemEval corpus, relations are defined relative to the linear order of the entities e1->e2
            typeE1, typeE2 = rest.split(",") # In the XML, the interaction type is the SemEval relation defined relative to the interaction element
            if e1 == "e1" and e2 == "e2": # The interaction element is e1->e1, therefore the type is the SemEval relation
                #e1, e2 = e2, e1
                e1, e2 = typeE1, typeE2
            else: # The interaction element is e2->e1, therefore the reverse of the type equals is SemEval relation
                assert e1 == "e2" and e2 == "e1"
                e1, e2 = typeE2, typeE1
    return {"type":relType, "e1":e1, "e2":e2}

def getConfDict(conf):
    global SPLIT_CONF
    if conf == None:
        return None
    conf = [x.split(":") for x in SPLIT_CONF.findall(conf)]
    return dict((key, value) for (key, value) in conf)

def getRelation(interactions, conflict="conf"):
    assert len(interactions) in (0,1,2)
    assert conflict in ("conf", "remove")
    # Remove negatives
    interactions = [x for x in interactions if x.get("type") != "neg"]
    # Check for the undirected "Other" class examples
    otherCount = sum([1 for x in interactions if x.get("type") == "Other"])
    if otherCount == len(interactions): # all predictions are for the type "Other"
        return {"type":"Other", "e1":None, "e2":None}
    # Generate a relation from the interactions
    if len(interactions) == 0: # Predit "Other" for all "neg" sentences
        return {"type":"Other", "e1":None, "e2":None} #None
    elif len(interactions) == 1:
        #if conflict == "remove":
        #    return {"type":"Other", "e1":None, "e2":None}
        #else:
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
        undirected1 = i1.get("type").split("(")[0]
        undirected2 = i2.get("type").split("(")[0]
        if conf1 == None and conf2 == None: # assume this is gold annotation
            assert undirected1 == undirected2 # check that types match except for reversing
            # The first gold interaction is for e1->e2
            assert i1.get("e1").endswith(".e1")
            assert i1.get("e2").endswith(".e2")
            return readInteraction(i1)
        assert conf1 != None and conf2 != None, (i1.attrib, i2.attrib, otherCount, len(interactions))
        if (undirected1 != undirected2) and conflict == "remove":
            return {"type":"Other", "e1":None, "e2":None}
        elif conf1[i1.get("type")] > conf2[i2.get("type")]:
            return readInteraction(i1)
        else:
            return readInteraction(i2)

def exportRelations(xml, outPath, conflict="conf"):
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
        rel = getRelation(interactions, conflict)
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

def evaluate(inputXML, goldXML, outPath, conflict="conf"):
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
    exportRelations(inputXML, inputPath, conflict)
    print "Exporting relations from", goldPath
    exportRelations(goldXML, goldPath, conflict)
    # Check the answer key file format
    runCommand(os.path.join(tempDir, formatChecker), inputPath)
    runCommand(os.path.join(tempDir, formatChecker), goldPath)
    # Run the evaluator
    stderrText, stdoutText = runCommand(os.path.join(tempDir, evaluator), inputPath, goldPath)
    # Write the results
    if outPath != None:
        outFile = open(outPath, "wt")
        outFile.write("Input file: " + inputXML + "\n")
        outFile.write("Gold file: " + goldXML + "\n")
        for text in (stderrText, stdoutText):
            outFile.write(text)
        outFile.close()

###############################################################################
# Batch Processing
###############################################################################

CORPUS_ID = "SE10T8"

def getTargets():
    targets = []
    for const in ("BLLIP-BIO", "BLLIP", "STANFORD"):
        for dep in ("STANFORD", "STANFORD-CONVERT"):
            targets.append({"const":const, "dep":dep})
            #targets.append({"directed":False, "const":const, "dep":dep})
            #targets.append({"directed":True, "const":const, "dep":dep, "negatives":"NEG"})
            #targets.append({"directed":True, "const":const, "dep":dep, "negatives":"REVERSE_POS"})
    #return targets #[0:1]
    return [{"const":None, "dep":"SYNTAXNET"}]

def getCorpusId(target, corpusId=None):
    if corpusId == None:
        #mode = "DIR" if target["directed"] else "UNDIR"
        #if target["directed"]:
        #    mode += "-" + target["negatives"]
        #corpusId = "_".join([CORPUS_ID, mode, target["const"], target["dep"]])
        corpusId = "_".join([CORPUS_ID, str(target["const"]), str(target["dep"])])
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
                convertSemEval2010Task8.convert(inPath=None, outDir=targetDir, corpusId=CORPUS_ID, directed=True, negatives="REVERSE_POS", preprocess=True, debug=debug, clear=False, constParser=target["const"], depParser=target["dep"], logging=True)

def getModels(corpusPath, modelsPath, corpusId, directed="both"):
    models = []
    assert directed in ("both", "true", "false")
    modelTypes = (True, False)
    if directed != "both": 
        modelTypes = (True,) if directed == "true" else (False,)
    targets = getTargets()
    for target in targets:
        targetCorpusId = getCorpusId(target, corpusId)
        corpusDir = os.path.join(corpusPath, targetCorpusId) if (corpusId == None) else corpusId
        for directed in modelTypes:
            targetDir = os.path.join(modelsPath, targetCorpusId + ("_DIR" if directed else "_UNDIR")) if (corpusId == None) else modelsPath
            model = {"model":targetDir, "corpusDir":corpusDir, "directed":directed, "const":target["const"], "dep":target["dep"]}
            for dataset in ("devel", "test"): 
                model[dataset] = os.path.join(targetDir, "classification-" + dataset, dataset + "-pred.xml.gz")
                model[dataset + "-gold"] = os.path.join(corpusDir, CORPUS_ID + "-" + dataset + ".xml")
                model[dataset + "-eval"] = os.path.join(targetDir, "official-eval-" + dataset + ".txt")
            model["exampleStyle"] = "wordnet:filter_types=Other"
            if not directed:
                model["exampleStyle"] += ":undirected:se10t8_undirected"
            models.append(model)
    return models

def predict(corpusPath, modelsPath, dummy, corpusId=None, connection=None, directed="both"):
    for model in getModels(corpusPath, modelsPath, corpusId, directed):
        if os.path.exists(model["model"]):
            print "Skipping existing target", model["model"]
            continue
        print "Processing target", model["model"], "directed =", model["directed"]
        if dummy:
            continue
        train.train(model["model"], task=CORPUS_ID, corpusDir=model["corpusDir"], connection=connection,
                    exampleStyles={"examples":model["exampleStyle"]}, parse="McCC",
                    classifierParams={"examples":"c=1,10,100,500,1000,1500,2500,3500,4000,4500,5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000"})
        for dataset in ("devel", "test"):
            if os.path.exists(model[dataset]):
                evaluate(model[dataset], model[dataset + "-gold"], model[dataset + "-eval"])

def collect(modelsPath, resultPath, corpusId=None, directed="both"):
    csvFile = open(resultPath, "wt")
    fields = ["directed", "const", "dep", "score-devel", "score-test"]
    dw = csv.DictWriter(csvFile, delimiter='\t', fieldnames=fields)
    dw.writeheader()
    for model in getModels("DUMMY", modelsPath, corpusId, directed):
        #if not model["directed"]:
        #    continue
        print "Processing target", model["model"], "directed =", model["directed"]
        result = {"directed":model["directed"], "const":model["const"], "dep":model["dep"]}
        for dataset in ("devel", "test"):
            if os.path.exists(model[dataset + "-eval"]):
                with open(model[dataset + "-eval"], "rt") as f:
                    lines = f.readlines()
                    lines = [x for x in lines if x.startswith("<<< The official score")]
                    assert len(lines) == 1
                    score = lines[0].split("=")[1].strip().split()[0]
                    result["score-" + dataset] = score
        dw.writerow(result)
    csvFile.close()

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Input file in Interaction XML format")
    optparser.add_option("-o", "--output", default=None, help="Output file, used only when exporting relations")
    optparser.add_option("-g", "--gold", default=None, help="Correct annotation file for evaluation in Interaction XML format")
    optparser.add_option("-a", "--action", default=None, help="'install', 'evaluate', 'export', 'convert' or 'predict'")
    optparser.add_option("--conflict", default="conf", help="How to merge conflicting relations")
    optparser.add_option("--dummy", default=False, action="store_true", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--corpusId", default=None, help="")
    optparser.add_option("--connection", default=None, help="")
    optparser.add_option("--directed", default="both", help="both, true or false")
    (options, args) = optparser.parse_args()
    
    if options.action == "install":
        install()
    elif options.action == "evaluate":
        evaluate(options.input, options.gold, options.output, options.conflict)
    elif options.action == "export":
        exportRelations(options.input, options.output)
    elif options.action == "convert":
        convert(options.output, options.dummy, options.debug)
    elif options.action == "predict":
        predict(options.input, options.output, options.dummy, options.corpusId, options.connection, options.directed)
    elif options.action == "collect":
        collect(options.input, options.output, options.corpusId, options.directed)
    else:
        print "Unknown action", options.action