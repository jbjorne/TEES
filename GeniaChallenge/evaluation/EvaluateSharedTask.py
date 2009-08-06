import sys, os, shutil
import subprocess

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
        results[name]["fscore"] = float(splits[8])
    return results
        
def printLines(lines):
    for line in lines:
        print >> sys.stderr, line[:-1]

def evaluate(sourceDir, task=1):
    # Go to evaluation scripts
    perlDir = os.path.dirname(os.path.abspath(__file__))+"/bionlp09_shared_task_evaluation_tools_v1"
    origDir = os.getcwd()
    os.chdir(perlDir)
    
    goldDir = "/usr/share/biotext/GeniaChallenge/orig-devel-test/evaluation-tools-devel-gold"
    tempDir = "/usr/share/biotext/GeniaChallenge/orig-devel-test/evaluation-temp"
    if os.path.exists(tempDir):
        shutil.rmtree(tempDir)
    os.mkdir(tempDir)
    
    results = {}
    
    commands = "export PATH=$PATH:./ ; "
    commands += "perl prepare-eval.pl " + sourceDir + " " + tempDir + " ; "
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

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory with predicted shared task files", metavar="FILE")
    optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.task == 1 or options.task == 2)

    evaluate(options.input, options.task)