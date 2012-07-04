import sys, os, shutil
import subprocess
import tempfile
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(thisPath,".."))
import Utils.Settings as Settings
import Utils.Download as Download

# TODO: Move somewhere else
#sys.path.append(os.path.abspath(os.path.join(thisPath, "../GeniaChallenge/evaluation")))
#from EvaluateSharedTask import evaluate as evaluateGE09
evaluateGE09 = None

#perlDir = os.path.expanduser("~/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_genia_tools")

def install(destDir=None, downloadDir=None, redownload=False):
    print >> sys.stderr, "Installing BioNLP'11 evaluators"
    settings = {}
    if downloadDir == None:
        downloadDir = Settings.DATAPATH
    if destDir == None:
        destDir = Settings.DATAPATH
    for corpus in ["GE", "BB", "BI", "CO"]:
        print >> sys.stderr, "Installing BioNLP'11", corpus, "evaluator"
        settings[corpus + "_EVALUATOR"] = Download.getTopDir(destDir + "/tools/evaluators/", Download.downloadAndExtract(Settings.URL[corpus + "_EVALUATOR"], destDir + "/tools/evaluators/", downloadDir + "/tools/download/"))
        print >> sys.stderr, "Installing BioNLP'11", corpus, "evaluator gold data"
        Download.downloadAndExtract(Settings.URL[corpus + "_DEVEL"], destDir + "/tools/evaluators/gold/" + corpus + "-devel", downloadDir + "/corpora/BioNLP11-original/corpus/", os.path.basename(Settings.URL[corpus + "_DEVEL"])[:-len(".tar.gz")])
    return settings

#def resultsToCSV(results, filename=None):
#    import Utils.TableUtils as TableUtils
#    rows = []
#    for k1 in sorted(results.keys()):
#        for k2 in sorted(results[k1].keys()):
#            rows.append({})
#            rows[-1]["eval"] = k1
#            rows[-1]["event_class"] = k2
#            for k3 in sorted(results[k1][k2].keys()):                
#                rows[-1][k3] = results[k1][k2][k3]
#    if filename != None:
#        fieldnames = ["eval", "event_class", "gold", "gold_match", "answer", "answer_match", "recall", "precision", "fscore"]
#        TableUtils.writeCSV(rows, filename, fieldnames)
#    return rows

def parseResults(lines):
    lines = lines[3:]
    results = {}
    for line in lines:
        if line[0] == "-":
            continue
        splits = line.strip().split()
        # define row name
        name = splits[0]
        name = name.replace("=","")
        name = name.replace("[","")
        name = name.replace("]","")
        results[name] = {}
        # add columns
        results[name]["gold"] = int(splits[1])
        results[name]["gold_match"] = int(splits[3][:-1])
        results[name]["answer"] = int(splits[4])
        results[name]["answer_match"] = int(splits[6][:-1])
        results[name]["recall"] = float(splits[7])
        results[name]["precision"] = float(splits[8])
        results[name]["fscore"] = float(splits[9])
    return results
        
def printLines(lines):
    for line in lines:
        print >> sys.stderr, line[:-1]

def getFolds(path, folds, seed=0):
    import Core.Split as Split
    files = os.listdir(path)
    docNumbers = set()
    for file in files:
        numPart = file.split(".",1)[0]
        if numPart.isdigit():
            docNumbers.add(int(numPart))
    docNumbers = list(docNumbers)
    folds = Split.getFolds(len(docNumbers), folds, seed)
    foldByDocNumber = {}
    for i in range(len(docNumbers)):
        foldByDocNumber[docNumbers[i]] = folds[i]
    return foldByDocNumber

def removeDocuments(path, folds, foldToRemove):
    files = os.listdir(path)
    for file in files:
        numPart = file.split(".",1)[0]
        if numPart.isdigit():
            numPart = int(numPart)
            assert folds.has_key(numPart)
            if folds[numPart] == foldToRemove:
                os.remove(os.path.join(path, file))

def evaluateVariance(sourceDir, task, folds):
    results = []
    for i in range(folds):
        results.append( evaluate(sourceDir, task, folds, i) )
    print >> sys.stderr, "##### Variance estimation results #####"
    for r in results:
        print >> sys.stderr, r["approximate"]["ALL-TOTAL"]

def hasGoldDocuments(sourceDir, goldDir):
    goldDocIds = set()
    for filename in os.listdir(goldDir):
        if filename[-4:] == ".txt":
            goldDocIds.add(filename.split(".", 1)[0])
    for filename in os.listdir(sourceDir):
        if filename.find(".a2") != -1:
            if filename.split(".", 1)[0] in goldDocIds:
                return True
    return False

#def getSourceDir(input):
#    if input.endswith(".tar.gz"):
#        import tarfile
#        tempDir = tempfile.mkdtemp()
#        f = tarfile.open(input)
#        f.extractall(tempDir)
#        f.close()
#        return tempDir, True
#    else:
#        return input, False

def getFScore(results, task):
    if task in ["GE", "GE09"]:
        path = ["approximate", "ALL-TOTAL", "fscore"]
    elif task in ["EPI", "ID", "REN"]:
        path = ["TOTAL", "fscore"]
    elif task in ["BB", "BI"]:
        path = ["fscore"]
    else:
        assert False
    
    current = results
    for step in path:
        if step in current:
            current = current[step]
        else:
            return -1
    return current

def evaluate(source, task, goldDir=None, debug=False):
    # Determine task
    subTask = "1"
    if "." in task:
        task, subTask = task.split(".")
    # Do the evaluation
    if task in ["GE", "GE09"]:
        results = evaluateGE(source, subTask, goldDir=goldDir, debug=debug)
    elif task in ["EPI", "ID"]:
        results = evaluateEPIorID(task, source, goldDir)
    elif task == "REN":
        results = evaluateREN(source, goldDir)
    elif task in ["BB", "BI"]:
        results = evaluateBX(task, source, goldDir)
    elif task == "CO":
        results = evaluateCO(sourceDir, goldDir)
    else:
        results = None
        print >> sys.stderr, corpus, "No BioNLP'11 evaluator for task", task
    # Return results
    if results == None:
        return None
    return (getFScore(results, task), results)

def checkEvaluator(corpus, sourceDir, goldDir = None):
    # Check evaluator
    if not hasattr(Settings, "BIONLP_EVALUATOR_DIR"):
        print >> sys.stderr, corpus, "BIONLP_EVALUATOR_DIR setting not defined"
        evaluatorDir = None
    else:
        evaluatorDir = os.path.join(Settings.BIONLP_EVALUATOR_DIR, Settings.EVALUATOR[corpus])
    # Check source data
    tempdir = None
    if sourceDir.endswith(".tar.gz"):
        tempdir = tempfile.mkdtemp()
        Download.extractPackage(sourceDir, os.path.join(tempdir, "source"))
        sourceDir = os.path.join(tempdir, "source")
    # Check gold data
    if goldDir == None:
        if not hasattr(Settings, "BIONLP_EVALUATOR_GOLD_DIR"):
            print >> sys.stderr, corpus, "BIONLP_EVALUATOR_GOLD_DIR setting not defined"
            return evaluatorDir, None
        goldDir = os.path.join(Settings.BIONLP_EVALUATOR_GOLD_DIR, Settings.EVALUATOR[corpus + "-gold"])
    if not os.path.exists(goldDir):
        print >> sys.stderr, corpus, "Evaluator gold data directory", goldDir, "does not exist"
        goldDir = None
    if goldDir != None and goldDir.endswith(".tar.gz"):
        if tempdir == None:
            tempdir = tempfile.mkdtemp()
        goldDir = Download.getTopDir(os.path.join(tempdir, "gold"), Download.extractPackage(goldDir, os.path.join(tempdir, "gold")))
        print >> sys.stderr, "Uncompressed evaluation gold to", goldDir
    if goldDir != None and not hasGoldDocuments(sourceDir, goldDir):
        print >> sys.stderr, "Evaluation input has no gold documents"
        goldDir = None
    return evaluatorDir, sourceDir, goldDir, tempdir

def evaluateGE(sourceDir, task=1, goldDir=None, folds=-1, foldToRemove=-1, evaluations=["strict", "approximate", "decomposition"], verbose=True, silent=False, debug=False):
    task = str(task)
    assert task in ["1","2","3"]
    if not silent:
        print >> sys.stderr, "GE task", task, "evaluation of", sourceDir, "against", goldDir
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("GE", sourceDir, goldDir)
    if goldDir == None:
        return None
    
    origDir = os.getcwd()
    os.chdir(evaluatorDir)
    if tempDir == None:
        tempDir = tempfile.mkdtemp()
    if folds != -1:
        folds = getFolds(sourceDir, folds)
        sourceSubsetDir = tempDir + "/source-subset"
        if os.path.exists(sourceSubsetDir):
            shutil.rmtree(sourceSubsetDir)
        shutil.copytree(sourceDir, sourceSubsetDir)
        removeDocuments(sourceSubsetDir, folds, foldToRemove)
    else:
        sourceSubsetDir = sourceDir
    
    results = {}
    
    #commands = "export PATH=$PATH:./ ; "
    outDir = tempDir + "/output"
    commands = "perl a2-normalize.pl -g " + goldDir
    commands += " -o " + outDir
    commands += " " + sourceSubsetDir + "/*.a2"
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if verbose and not silent:
        printLines(p.stderr.readlines())
        printLines(p.stdout.readlines())
    else: # Not reading the lines causes some error in the perl script!
        p.stderr.readlines()
        p.stdout.readlines()
                
    if "strict" in evaluations:
        #commands = "export PATH=$PATH:./ ; "
        commands = "perl a2-evaluate.pl" 
        commands += " -t " + str(task)
        if debug: commands += " -v -d"
        commands += " -g " + goldDir + " " + outDir +"/*.a2"
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderrLines = p.stderr.readlines()
        stdoutLines = p.stdout.readlines()
        if not silent:
            printLines(stderrLines)
            print >> sys.stderr, "##### strict evaluation mode #####"
            printLines(stdoutLines)
        results["strict"] = parseResults(stdoutLines)
    
    if "approximate" in evaluations:
        if not silent:
            print >> sys.stderr, "##### approximate span and recursive mode #####"
        #commands = "export PATH=$PATH:./ ; "
        commands = "perl a2-evaluate.pl"
        commands += " -t " + str(task)
        if debug: commands += " -v -d"
        commands += " -g " + goldDir + " -sp " + outDir + "/*.a2"
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderrLines = p.stderr.readlines()
        stdoutLines = p.stdout.readlines()
        if not silent:
            printLines(stderrLines)
            printLines(stdoutLines)
        results["approximate"] = parseResults(stdoutLines)

    if "decomposition" in evaluations:
        if not silent:
            print >> sys.stderr, "##### event decomposition in the approximate span mode #####"
        #commands = "export PATH=$PATH:./ ; "
        commands = "perl a2-evaluate.pl"
        commands += " -t " + str(task)
        if debug: commands += " -v -d"
        commands += " -g " + goldDir + " -sp " + outDir + "/*.a2"
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderrLines = p.stderr.readlines()
        stdoutLines = p.stdout.readlines()
        if not silent:
            printLines(stderrLines)
            printLines(stdoutLines)
        results["decomposition"] = parseResults(stdoutLines)
    
    shutil.rmtree(tempDir)
    
    # return to current dir
    os.chdir(origDir)
    return results

def printLinesBX(lines):
    queue = []
    category = None
    for line in lines:
        if ":" in line:
            if len(queue) > 0:
                print >> sys.stderr, str(category) + ":", ", ".join(queue)
                queue = []
            category = line.split(":")[0].strip()
        elif line.startswith("    "):
            queue.append(line.strip())
        else:
            print >> sys.stderr, line[:-1]
    if len(queue) > 0:
        print >> sys.stderr, str(category) + ":", ", ".join(queue)
        queue = []

def evaluateBX(corpusName, sourceDir, goldDir=None, silent=False):
    assert corpusName in ["BI", "BB"], corpusName
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator(corpusName, sourceDir, goldDir)
    if goldDir == None:
        return None
    
    if corpusName == "BI":
        commands = "java -jar " + evaluatorDir + "/BioNLP-ST_2011_bacteria_interactions_evaluation_software.jar " + golDir + " " + sourceDir
    elif corpusName == "BB":
        commands = "java -jar " + evaluatorDir + "/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software.jar " + golDir + " " + sourceDir
    else:
        assert False, corpusName

    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        printLinesBX(stderrLines)
        printLinesBX(stdoutLines)
    
    results = {}
    if corpusName == "BI":
        category = None
        for line in stdoutLines:
            if ":" in line:
                category = line.split(":")[0].strip()
            if category == "Global scores" and line.startswith("    "):
                key, value = line.strip().split("=")
                key = key.strip()
                value = value.strip()
                assert key not in results
                if key == "f-score":
                    key = "fscore"
                if value == "NaN":
                    results[key] = 0.0
                else:
                    results[key] = float(value)
    elif corpusName == "BB":
        for line in stdoutLines:
            key, value = line.strip().split("=")
            key = key.strip()
            value = value.strip()
            assert key not in results
            if key == "F-score":
                key = "fscore"
            if value == "NaN":
                results[key] = 0.0
            else:
                results[key] = float(value)
    if tempDir != None: 
        shutil.rmtree(tempDir)
    return results
     
def evaluateEPIorID(corpus, sourceDir, goldDir=None, silent=False):
    assert corpus in ["EPI", "ID"], corpus
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator(corpus, sourceDir, goldDir)
    if goldDir == None:
        return None
    commands = "cd " + evaluatorDir
    commands += " ; " + "python evaluation.py -s -p -r " + goldDir + " " + sourceDir + "/*.a2"
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        for line in stderrLines:
            print >> sys.stderr, line,
        for line in stdoutLines:
            print >> sys.stderr, line,
        print >> sys.stderr
    for line in stderrLines + stdoutLines:
        if "No such file or directory" in line:
            return None
    if tempDir != None: 
        shutil.rmtree(tempDir)
    return parseResults(stdoutLines)

def evaluateREN(sourceDir, goldDir=None, silent=False):
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("REN", sourceDir, goldDir)
    if goldDir == None:
        return None
    commands = "cd " + evaluatorDir
    commands += " ; " + "java -jar eval_rename.jar " + goldDir + " " + sourceDir
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        for line in stderrLines:
            print >> sys.stderr, line,
        for line in stdoutLines:
            print >> sys.stderr, line,
        print >> sys.stderr
    results = {}
    for line in stdoutLines:
        category, value = line.strip().split(":")
        value = value.strip()
        if value == "NaN":
            value = 0.0
        elif "." in value:
            value = float(value)
        else:
            value = int(value)
        results[category.strip()] = value
    if tempDir != None: 
        shutil.rmtree(tempDir)
    return results

#def evaluateCO(sourceDir, goldDir=None, silent=False):
#    goldDir = os.path.expanduser("~/data/BioNLP11SharedTask/supporting-tasks/BioNLP-ST_2011_coreference_development_data")
#    evaluatorPath = os.path.expanduser("~/data/BioNLP11SharedTask/supporting-tasks/CREvalPackage1.4")
#    sourceDir = os.path.abspath(sourceDir)
#    commands = "cd " + evaluatorPath
#    commands += " ; " + "java -jar [-mention=strict|partial] [-link=atom|surface] [-recall=system|algorithm] [-details] " + goldDir + " " + sourceDir + " " + resultDir
#    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#    stderrLines = p.stderr.readlines()
#    stdoutLines = p.stdout.readlines()
#    if not silent:
#        for line in stderrLines:
#            print >> sys.stderr, line,
#        for line in stdoutLines:
#            print >> sys.stderr, line,
#        print >> sys.stderr
##    results = {}
##    for line in stdoutLines:
##        category, value = line.strip().split(":")
##        value = value.strip()
##        if value == "NaN":
##            value = 0.0
##        elif "." in value:
##            value = float(value)
##        else:
##            value = int(value)
##        results[category.strip()] = value
##    return results

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory with predicted shared task files", metavar="FILE")
    #optparser.add_option("-c", "--corpus", default="GE", dest="corpus", help="")
    optparser.add_option("-t", "--task", default="GE.2", dest="task", help="")
    #optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    optparser.add_option("-v", "--variance", default=0, type="int", dest="variance", help="variance folds")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="debug")
    optparser.add_option("--install", default=None, dest="install", help="Install directory (or DEFAULT)")
    (options, args) = optparser.parse_args()
    #assert(options.task in [1,2,3])
    
    if options.install == None:
        assert(options.input != None)
        evaluate(options.input, options.task, debug=options.debug)
    else:
        downloadDir = None
        destDir = None
        if options.install != "DEFAULT":
            if "," in options.install:
                destDir, downloadDir = options.install.split(",")
            else:
                destDir = options.install
        settings = install(destDir, downloadDir)
        for key in sorted(settings.keys()):
            print key + "=\"" + str(settings[key]) + "\""
    
#    if options.corpus == "GE":
#        if options.variance == 0:
#            evaluate(options.input, options.task, debug = options.debug)
#        else:
#            evaluateVariance(options.input, options.task, options.variance)
#    elif options.corpus in ["EPI", "ID"]:
#        print evaluateEPIorID(options.input, options.corpus)
#    elif options.corpus == "REN":
#        print evaluateREN(options.input)
#    else:
#        print evaluateBX(options.input, options.corpus)