import sys, os, shutil
import subprocess
import tempfile
import codecs
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
    for corpus in ["GE11", "BB11", "BI11", "CO11"]:
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
    if task in ["GE11", "GE09"]:
        path = ["approximate", "ALL-TOTAL", "fscore"]
    elif task in ["EPI11", "ID11", "REN11"]:
        path = ["TOTAL", "fscore"]
    elif task in ["BB11", "BI11"]:
        path = ["fscore"]
    elif task == "CO11":
        path = ["MENTION LINKING", "fscore"]
    elif task == "CO11":
        path = ["MENTION LINKING", "fscore"]
    elif task in ["GRN13"]:
        path = ["Relaxed F-score"]
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
    print >> sys.stderr, "BioNLP task", task, "devel evaluation"
    # Determine task
    subTask = "1"
    if "." in task:
        task, subTask = task.split(".")
    # Do the evaluation
    if task in ["GE11", "GE09"]:
        results = evaluateGE(source, task, subTask, goldDir=goldDir, debug=debug)
    elif task in ["EPI11", "ID11"]:
        results = evaluateEPIorID(task, source, goldDir)
    elif task == "REN11":
        results = evaluateREN(source, goldDir)
    elif task in ["BB11", "BI11"]:
        results = evaluateBX(task, source, goldDir, debug=debug)
    elif task == "CO11":
        results = evaluateCO(source, goldDir)
    elif task == "GRN13":
        results = evaluateGRN13(source, goldDir, debug=debug)
    else:
        results = None
        print >> sys.stderr, "No official evaluator for task", task
    # Return results
    if results == None:
        return None
    return (getFScore(results, task), results)

def removeXLines(dir, filePatterns=[".a1", ".rel", ".a2"]):
    for filename in os.listdir(dir):
        match = False
        for pattern in filePatterns:
            if pattern in filename:
                match = True
                break
        if match:
            filePath = os.path.join(dir, filename)
            f = codecs.open(filePath, "rt", "utf-8")
            lines = f.readlines()
            f.close()
            f = codecs.open(filePath, "wt", "utf-8")
            for line in lines:
                if line[0] != "X":
                    f.write(line)
            f.close()

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
    else: #if corpus in ("GE09", "BB11", "BI11"):
        # GE09 a2 files have to be renamed and relation identifier "R" has to be replaced with "E" for the BB11 and BI11 relations.
        # X-lines have to be removed from all tasks
        tempdir = tempfile.mkdtemp()
        shutil.copytree(sourceDir, os.path.join(tempdir, "source"))
        sourceDir = os.path.join(tempdir, "source")
    # Filter extra data
    removeXLines(sourceDir)
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
    # Use absolute paths
    sourceDir = os.path.abspath(sourceDir)
    if evaluatorDir != None:
        evaluatorDir = os.path.abspath(evaluatorDir)
    if goldDir != None:
        goldDir = os.path.abspath(goldDir)
    if tempdir != None:
        tempdir = os.path.abspath(tempdir)
    return evaluatorDir, sourceDir, goldDir, tempdir

def evaluateGE(sourceDir, mainTask="GE11", task=1, goldDir=None, folds=-1, foldToRemove=-1, evaluations=["strict", "approximate", "decomposition"], verbose=True, silent=False, debug=False):
    task = str(task)
    assert mainTask in ["GE11", "GE09"], mainTask
    assert task in ["1","2","3"], task
    if not silent:
        print >> sys.stderr, mainTask, "task", task, "evaluation of", sourceDir, "against", goldDir
    if mainTask == "GE11":
        evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("GE11", sourceDir, goldDir)
        taskSuffix = ".a2"
    else:
        evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("GE09", sourceDir, goldDir)
        # Rename files in the copied source directory
        taskSuffix = ".a2.t1"
        for filename in os.listdir(sourceDir):
            if filename.endswith(".a2"):
                if task == 1:
                    taskSuffix = ".a2.t1"
                elif task == 2:
                    taskSuffix = ".a2.t12"
                else:
                    taskSuffix = ".a2.t123"
                shutil.move(os.path.join(sourceDir, filename), os.path.join(sourceDir, filename.rsplit(".", 1)[0] + taskSuffix))
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
    
    # Prepare gold data
    if mainTask == "GE09":
        preparedGoldDir = os.path.join(tempDir, "prepared-gold")
        commands = "perl prepare-gold.pl " + goldDir + " " + preparedGoldDir
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if verbose and not silent:
            printLines(p.stderr.readlines())
            printLines(p.stdout.readlines())
        else: # Not reading the lines causes some error in the perl script!
            p.stderr.readlines()
            p.stdout.readlines()
        goldDir = preparedGoldDir
    
    # Prepare evaluated data
    outDir = tempDir + "/output"
    if mainTask == "GE11":
        commands = "perl a2-normalize.pl -g " + goldDir
        commands += " -o " + outDir
        commands += " " + sourceSubsetDir + "/*" + taskSuffix #".a2"
    else:
        commands = "perl prepare-eval.pl -g " + goldDir
        commands += " " + sourceSubsetDir + " " + outDir
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
        if mainTask == "GE11": commands += " -t " + str(task)
        if debug: commands += " -v -d"
        commands += " -g " + goldDir + " " + outDir + "/*" + taskSuffix #".a2"
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
        if mainTask == "GE11": commands += " -t " + str(task)
        if debug: commands += " -v -d"
        commands += " -g " + goldDir + " -sp " + outDir + "/*" + taskSuffix #".a2"
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
        if mainTask == "GE11": commands += " -t " + str(task)
        if debug: commands += " -v -d"
        commands += " -g " + goldDir + " -sp " + outDir + "/*" + taskSuffix #".a2"
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderrLines = p.stderr.readlines()
        stdoutLines = p.stdout.readlines()
        if not silent:
            printLines(stderrLines)
            printLines(stdoutLines)
        results["decomposition"] = parseResults(stdoutLines)
    
    if not debug:
        shutil.rmtree(tempDir)
    else:
        print >> sys.stderr, "Temporary directory left at", tempDir
    
    # return to current dir
    os.chdir(origDir)
    return results

def printLinesBX(lines):
#    queue = []
#    category = None
    for line in lines:
        print >> sys.stderr, line[:-1]
    
#    for line in lines:
#        if ":" in line:
#            if len(queue) > 0:
#                print >> sys.stderr, str(category) + ":", ", ".join(queue)
#                queue = []
#            category = line.split(":")[0].strip()
#        elif line.startswith("    "):
#            queue.append(line.strip())
#        else:
#            print >> sys.stderr, line[:-1]
#    if len(queue) > 0:
#        print >> sys.stderr, str(category) + ":", ", ".join(queue)
#        queue = []

def evaluateBX(corpusName, sourceDir, goldDir=None, silent=False, debug=False):
    assert corpusName in ["BI11", "BB11"], corpusName
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator(corpusName, sourceDir, goldDir)
    if goldDir == None:
        return None
    
    if corpusName == "BI11":
        commands = Settings.JAVA + " -jar " + evaluatorDir + "/BioNLP-ST_2011_bacteria_interactions_evaluation_software.jar " + goldDir + " " + sourceDir
    elif corpusName == "BB11":
        commands = Settings.JAVA + " -jar " + evaluatorDir + "/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software.jar " + goldDir + " " + sourceDir
    else:
        assert False, corpusName
    
    # Relabel relation annotation identifiers RX to EX.
    for filename in os.listdir(sourceDir):
        if filename.endswith(".a2"): # BB task is all relations, but uses a2 as file tag
            f = codecs.open(os.path.join(sourceDir, filename), "rt", "utf-8")
            lines = f.readlines()
            f.close()
            modified = False
            for i in range(len(lines)):
                if lines[i][0] == "R":
                    lines[i] = "E" + lines[i][1:]
                    modified = True
            if modified:
                f = codecs.open(os.path.join(sourceDir, filename), "wt", "utf-8")
                for line in lines:
                    f.write(line)
                f.close()

    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        printLinesBX(stderrLines)
        printLinesBX(stdoutLines)
    
    results = {}
    if corpusName == "BI11":
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
    elif corpusName == "BB11":
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
    if not debug and tempDir != None:
        shutil.rmtree(tempDir)
    else:
        print >> sys.stderr, "Temporary directory left at", tempDir
    return results
     
def evaluateEPIorID(corpus, sourceDir, goldDir=None, silent=False):
    assert corpus in ["EPI11", "ID11"], corpus
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
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("REN11", sourceDir, goldDir)
    if goldDir == None:
        return None
    commands = "cd " + evaluatorDir
    commands += " ; " + Settings.JAVA + " -jar eval_rename.jar " + goldDir + " " + sourceDir
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

def evaluateCO(sourceDir, goldDir=None, silent=False):
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("CO11", sourceDir, goldDir)
    if goldDir == None:
        return None
    # Run the evaluation program, which writes the result into a file
    if tempDir == None:
        tempDir = tempfile.mkdtemp()
    resultDir = os.path.join(tempDir, "result")
    os.makedirs(resultDir)
    commands = "cd " + evaluatorDir
    commands += " ; " + Settings.JAVA + " -jar CRScorer.jar " + goldDir + " " + sourceDir + " " + resultDir
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    stdoutLines = p.stdout.readlines()
    if not silent:
        for i in range(len(stdoutLines)):
            # Skip mentions of processing a document if no error happened in that document
            if (not stdoutLines[i].strip().endswith("...")) or (i < len(stdoutLines) - 1 and not stdoutLines[i+1].strip().endswith("...")):
                print >> sys.stderr, stdoutLines[i],
        for line in stderrLines:
            print >> sys.stderr, line,
        print >> sys.stderr
    # Read the evaluation result from the file it has been written to
    f = open(os.path.join(resultDir, "eval.results"), "rt")
    resultLines = f.readlines()
    f.close()
    results = {"MENTION DETECTION":{}, "MENTION LINKING":{}}
    currentBlock = None
    for line in resultLines:
        line = line.replace("\t", " ")
        print >> sys.stderr, line.rstrip()
        if line[0] == "*":
            continue
        if "EVALUATION OF MENTION DETECTION" in line:
            currentBlock = results["MENTION DETECTION"]
        elif "EVALUATION OF MENTION LINKING" in line:
            currentBlock = results["MENTION LINKING"]
        elif ":" in line:
            name, value = line.split(":")
            name = name.strip()
            value = int(value)
            currentBlock[name] = value
        elif line[0] == "P":
            splits = line.split()
            assert splits[0] == "P" and splits[1] == "=" and splits[3] == "R" and splits[4] == "=" and splits[6] == "F" and splits[7] == "=", line
            currentBlock["precision"] = float(splits[2])
            currentBlock["recall"] = float(splits[5])
            currentBlock["fscore"] = float(splits[8])
    # Remove temporary directory
    if tempDir != None: 
        shutil.rmtree(tempDir)
    return results

def evaluateGRN13(sourceDir, goldDir=None, silent=False, debug=False):
    evaluatorDir, sourceDir, goldDir, tempDir = checkEvaluator("GRN13", sourceDir, goldDir)
    if goldDir == None:
        return None
    commands = "cd " + evaluatorDir
    commands += " ; " + "python GRN.py --a1-dir " + goldDir + " --a2-dir " + goldDir + " --pred-dir " + sourceDir + " " + goldDir + "/PMID-*.txt"
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
        splits = line.strip().split(":")
        if len(splits) == 2 and splits[1].strip() != "":
            value = splits[1].strip()
            if value == "NaN":
                value = 0.0
            elif "." in value:
                value = float(value)
            else:
                value = int(value)
            results[splits[0].strip()] = value
    if not debug and tempDir != None:
        shutil.rmtree(tempDir)
    return results

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(description="Evaluate BioNLP Shared Task predictions")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory with predicted shared task files", metavar="FILE")
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="optional gold directory (default is the task development set)", metavar="FILE")
    optparser.add_option("-t", "--task", default="GE.2", dest="task", help="")
    optparser.add_option("-v", "--variance", default=0, type="int", dest="variance", help="variance folds")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="debug")
    optparser.add_option("--install", default=None, dest="install", help="Install directory (or DEFAULT)")
    (options, args) = optparser.parse_args()
    #assert(options.task in [1,2,3])
    
    if options.install == None:
        assert(options.input != None)
        evalResult = evaluate(options.input, options.task, options.gold, debug=options.debug)
        if options.debug:
            print >> sys.stderr, "evaluate output:", evalResult
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