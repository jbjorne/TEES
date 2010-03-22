import sys, os, shutil
import subprocess
thisPath = os.path.dirname(os.path.abspath(__file__))
def relPath(path):
    return os.path.abspath(os.path.join(thisPath, path))

RELEASE = True
#IF LOCAL
RELEASE = False
#ENDIF
if RELEASE:
    sys.path.append( os.path.split(os.path.abspath(__file__))[0] + "/../.." )
#IF LOCAL
else:
    sys.path.append( os.path.split(os.path.abspath(__file__))[0] + "/../../JariSandbox/ComplexPPI/Source" )
#sys.path.append(os.path.join(os.path.abspath(__file__),"/../../JariSandbox/ComplexPPI/Source/Core"))
#ENDIF
import Core.Split as Split
import Utils.TableUtils as TableUtils

perlDir = os.path.dirname(os.path.abspath(__file__))+"/bionlp09_shared_task_evaluation_tools_v1"

def resultsToCSV(results, filename=None):
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
    

def evaluate(sourceDir, task=1, folds=-1, foldToRemove=-1, evaluations=["strict", "approximate", "decomposition"], verbose=True):
    global perlDir
    sourceDir = os.path.abspath(sourceDir)
    #print sourceDir
    
    assert task in [1,12,13,123]
    
    # Go to evaluation scripts
    origDir = os.getcwd()
    os.chdir(perlDir)
    
    goldDir = relPath("../../../data/evaluation-data/evaluation-tools-devel-gold")
    tempDir = relPath("../../../data/evaluation-data/evaluation-temp")
    #IF LOCAL
    goldDir = "/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/evaluation-tools-devel-gold"
    tempDir = "/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/evaluation-temp"
    #ENDIF
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
    
    commands = "export PATH=$PATH:./ ; "
    commands += "perl prepare-eval.pl -g " + goldDir
    commands += " " + sourceSubsetDir + " " + tempDir
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if verbose:
        printLines(p.stderr.readlines())
        printLines(p.stdout.readlines())
    else: # Not reading the lines causes some error in the perl script!
        p.stderr.readlines()
        p.stdout.readlines()
    
    if "strict" in evaluations:
        commands = "export PATH=$PATH:./ ; "
        commands += "a2-evaluate.pl -g " + goldDir + " " + tempDir
        commands += "/*.t" + str(task)
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        printLines(p.stderr.readlines())
        print >> sys.stderr, "##### strict evaluation mode #####"
        stdoutLines = p.stdout.readlines()
        printLines(stdoutLines)
        results["strict"] = parseResults(stdoutLines)
    
    if "approximate" in evaluations:
        print >> sys.stderr, "##### approximate span and recursive mode #####"
        commands = "export PATH=$PATH:./ ; "
        commands += "a2-evaluate.pl -g " + goldDir + " -sp " + tempDir
        commands += "/*.t" + str(task)
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        printLines(p.stderr.readlines())
        stdoutLines = p.stdout.readlines()
        printLines(stdoutLines)
        results["approximate"] = parseResults(stdoutLines)

    if "decomposition" in evaluations:
        print >> sys.stderr, "##### event decomposition in the approximate span mode #####"
        commands = "export PATH=$PATH:./ ; "
        commands += "a2-evaluate.pl -g " + goldDir + " -sp " + tempDir
        commands += "/*.t" + str(task) + "d"
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        printLines(p.stderr.readlines())
        stdoutLines = p.stdout.readlines()
        printLines(stdoutLines)
        results["decomposition"] = parseResults(stdoutLines)
    
    # return to current dir
    os.chdir(origDir)
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
    optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    optparser.add_option("-v", "--variance", default=0, type="int", dest="variance", help="variance folds")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.task in [1,12,13,123])
    
    if options.variance == 0:
        evaluate(options.input, options.task)
    else:
        evaluateVariance(options.input, options.task, options.variance)