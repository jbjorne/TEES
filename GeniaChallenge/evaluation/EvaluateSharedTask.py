import sys, os, shutil
import subprocess
sys.path.append( os.path.split(os.path.abspath(__file__))[0] + "/../../JariSandbox/ComplexPPI/Source/Core" )
#sys.path.append(os.path.join(os.path.abspath(__file__),"/../../JariSandbox/ComplexPPI/Source/Core"))
import Split

perlDir = os.path.dirname(os.path.abspath(__file__))+"/bionlp09_shared_task_evaluation_tools_v1"

def parseResults(lines):
    lines = lines[3:]
    for line in lines:
        if line[0] == "-":
            continue
        splits = line.strip().split()
        results = {}
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
    

def evaluate(sourceDir, task=1, folds=-1, foldToRemove=-1):
    global perlDir
    sourceDir = os.path.abspath(sourceDir)
    print sourceDir
    
    # Go to evaluation scripts
    origDir = os.getcwd()
    os.chdir(perlDir)
    
    goldDir = "/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/evaluation-tools-devel-gold"
    tempDir = "/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/evaluation-temp"
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
    commands += "perl prepare-eval.pl " + sourceSubsetDir + " " + tempDir + " ; "
    commands += "a2-evaluate.pl -g " + goldDir + " " + tempDir
    if task == 1:
        commands += "/*.t1"
    else:
        commands += "/*.t12"
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    printLines(p.stderr.readlines())
    print >> sys.stderr, "##### strict evaluation mode #####"
    stdoutLines = p.stdout.readlines()
    printLines(stdoutLines)
    results["strict"] = parseResults(stdoutLines)
    
    print >> sys.stderr, "##### approximate span and recursive mode #####"
    commands = "export PATH=$PATH:./ ; "
    commands += "a2-evaluate.pl -g " + goldDir + " -sp " + tempDir
    if task == 1:
        commands += "/*.t1"
    else:
        commands += "/*.t12"
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    printLines(p.stderr.readlines())
    stdoutLines = p.stdout.readlines()
    printLines(stdoutLines)
    results["approximate"] = parseResults(stdoutLines)

    print >> sys.stderr, "##### event decomposition in the approximate span mode #####"
    commands = "export PATH=$PATH:./ ; "
    commands += "a2-evaluate.pl -g " + goldDir + " -sp " + tempDir
    if task == 1:
        commands += "/*.t1d"
    else:
        commands += "/*.t12d"
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
    assert(options.task == 1 or options.task == 2)
    
    if options.variance == 0:
        evaluate(options.input, options.task)
    else:
        evaluateVariance(options.input, options.task, options.variance)