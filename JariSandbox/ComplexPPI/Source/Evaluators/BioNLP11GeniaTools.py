import sys, os, shutil
import subprocess
thisPath = os.path.dirname(os.path.abspath(__file__))
def relPath(path):
    return os.path.abspath(os.path.join(thisPath, path))

perlDir = "/home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_genia_tools"

def resultsToCSV(results, filename=None):
    import Utils.TableUtils as TableUtils
    rows = []
    for k1 in sorted(results.keys()):
        for k2 in sorted(results[k1].keys()):
            rows.append({})
            rows[-1]["eval"] = k1
            rows[-1]["event_class"] = k2
            for k3 in sorted(results[k1][k2].keys()):                
                rows[-1][k3] = results[k1][k2][k3]
    if filename != None:
        fieldnames = ["eval", "event_class", "gold", "gold_match", "answer", "answer_match", "recall", "precision", "fscore"]
        TableUtils.writeCSV(rows, filename, fieldnames)
    return rows

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

def evaluate(sourceDir, task=1, folds=-1, foldToRemove=-1, evaluations=["strict", "approximate", "decomposition"], verbose=True, silent=False, debug=False):
    global perlDir
    sourceDir = os.path.abspath(sourceDir)
    #print sourceDir

    assert task in [1,2,3]
    
    # Go to evaluation scripts
    origDir = os.getcwd()
    os.chdir(perlDir)
    
    goldDir = "/home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_genia_devel_data_rev1"
    if not hasGoldDocuments(sourceDir, goldDir):
        print >> sys.stderr, "Evaluation input has no gold documents"
        return 
    
    tempDir = os.path.join(perlDir, "temp-work")
    if os.path.exists(tempDir):
        shutil.rmtree(tempDir)
    os.mkdir(tempDir)
    
    if folds != -1:
        folds = getFolds(sourceDir, folds)
        sourceSubsetDir = "/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/source-subset"
        if os.path.exists(sourceSubsetDir):
            shutil.rmtree(sourceSubsetDir)
        shutil.copytree(sourceDir, sourceSubsetDir)
        removeDocuments(sourceSubsetDir, folds, foldToRemove)
    else:
        sourceSubsetDir = sourceDir
    
    results = {}
    
    #commands = "export PATH=$PATH:./ ; "
    commands = "perl a2-normalize.pl -g " + goldDir
    commands += " -o " + tempDir
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
        commands += " -g " + goldDir + " " + tempDir +"/*.a2"
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
        commands += " -g " + goldDir + " -sp " + tempDir + "/*.a2"
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
        commands += " -g " + goldDir + " -sp " + tempDir + "/*.a2"
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderrLines = p.stderr.readlines()
        stdoutLines = p.stdout.readlines()
        if not silent:
            printLines(stderrLines)
            printLines(stdoutLines)
        results["decomposition"] = parseResults(stdoutLines)
    
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

def evaluateBX(sourceDir, corpusName, silent=False):
    if corpusName == "BI":
        commands = "java -jar /home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_bacteria_interactions_evaluation_software/BioNLP-ST_2011_bacteria_interactions_evaluation_software.jar /home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_bacteria_interactions_dev_data_rev1-remixed/ " + sourceDir
    elif corpusName == "BB":
        commands = "java -jar /home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software.jar /home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1-fixed/ " + sourceDir
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
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory with predicted shared task files", metavar="FILE")
    optparser.add_option("-c", "--corpus", default="GE", dest="corpus", help="")
    optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    optparser.add_option("-v", "--variance", default=0, type="int", dest="variance", help="variance folds")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="debug")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.task in [1,2,3])
    
    if options.corpus == "GE":
        if options.variance == 0:
            evaluate(options.input, options.task, debug = options.debug)
        else:
            evaluateVariance(options.input, options.task, options.variance)
    else:
        print evaluateBX(options.input, options.corpus)