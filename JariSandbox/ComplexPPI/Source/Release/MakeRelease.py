# After running, go to output/src and run:
# mv __init__.py ../temp ; epydoc -v --exclude networkx --parse-only --debug -o ../doc ./* ; mv ../temp __init__.py

import sys, os, shutil
import Preprocess
import subprocess

def getOutPath(filename, outpath):
    filename = filename.replace("GeniaChallenge", "SharedTask")
    filename = filename.replace("JariSandbox/ComplexPPI/Source/", "")
    return os.path.join(outpath, filename)

def addVisit(items, dirname, names):
    for name in names:
        items.append(os.path.join(dirname, name))

def getItems(path):
    items = []
    os.path.walk(path, addVisit, items)
    itemsToKeep = []
    for i in range(len(items)):
        if items[i].find("CVS") == -1:
            itemsToKeep.append( items[i][len(path)+1:].replace(".py","").replace("/",".") )
    return itemsToKeep

def copySources(input, output):
    shutil.copytree(os.path.join(input, "JariSandbox/ComplexPPI/Source"), os.path.join(output, "src"))
    shutil.copytree(os.path.join(input, "GeniaChallenge"), os.path.join(output, "src/SharedTask"))
    shutil.copytree(os.path.join(input, "CommonUtils"), os.path.join(output, "src/CommonUtils"))

def copySourceFiles(input, output):
    f = open("release-files.txt","rt")
    filenames = f.readlines()
    f.close
    toKeep = []
    for i in range(len(filenames)):
        filenames[i] = filenames[i].strip()
        if filenames[i][0] != "#":
            toKeep.append(filenames[i])
    
    for filename in toKeep:
        outPath = getOutPath(filename, output)
        if not os.path.exists(os.path.dirname(outPath)):
            os.makedirs(os.path.dirname(outPath))
        srcPath = os.path.join(input, filename)
        shutil.copy(srcPath, outPath)

def copyDataFiles(input, output):
    shutil.copy(srcPath, outPath)

###############################################
# Imports
###############################################
def fixAllImports(output):
    os.path.walk(output, fixVisit, output)

def fixVisit(outPath, dirname, names):
    for name in names:
        if name.find(".py") != -1:
            fixImports(outPath, dirname, name)
            Preprocess.preprocess(os.path.join(dirname, name), [Preprocess.conditional])
    if not "__init__.py" in names and not dirname.find("networkx") != -1:
        if dirname.find("CommonUtils") != -1 or dirname.find("SharedTask") != -1:
            initFile = open(os.path.join(outPath, dirname, "__init__.py"), "wt")
            initFile.close()
    
def fixImports(outPath, dirname, pythonFile):
    if dirname.find("networkx") != -1:
        return

    f = open(os.path.join(dirname, pythonFile), "rt")
    lines = f.readlines()
    f.close()
    
    steps = dirname[len(outPath)+1:].count("/")
    if len(lines) > 0 and lines[0][0:3] == "\"\"\"":
        count = 1
        while lines[count][0:3] != "\"\"\"":
            count += 1
        lines = lines[:count+1] + ["\nimport sys\nsys.path.insert(0,\"" + (steps * "../") + "CommonUtils\")\n"] + lines[count+1:]
    else:
        #lines = ["import sys\nsys.path.append(\"" + (steps * "../") + "CommonUtils\")\n"] + lines
        lines = ["import sys\nsys.path.insert(0,\"" + (steps * "../") + "CommonUtils\")\n"] + lines        
    f = open(os.path.join(dirname, pythonFile), "wt")
    f.writelines(lines)
    f.close()
    
def copy(filename, targetPath):
    print "copying", filename
    shutil.copy(filename, targetPath)

if __name__=="__main__":
    import sys, os
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-i", "--input", default="/home/jari/cvs_checkout", dest="input", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-o", "--output", default="/home/jari/SharedTaskRelease/output", dest="output", help="Output file for the statistics")
    (options, args) = optparser.parse_args()
    
    #print getItems(os.path.join(options.input, "CommonUtils"))
    #sys.exit()
    
    if os.path.exists(options.output):
        print >> sys.stderr, "Output directory exists, removing", options.output
        shutil.rmtree(options.output)
        os.makedirs(options.output)

    print >> sys.stderr, "Processing"
    #copySources(options.input, options.output)
    copySourceFiles(options.input, options.output + "/src")
    print >> sys.stderr, "Fixing imports"
    fixAllImports(options.output)
    
    print >> sys.stderr, "Copying data files"
    dataPath = os.path.join(options.output, "data")
    shutil.copytree("/usr/share/biotext/GeniaChallenge/CI-release/release-files/release-files-review-version-models", dataPath)
    #os.makedirs(dataPath + "/js")
    #print os.listdir("../../../")
    shutil.copytree("../../../PPIDependencies/Visualization/js", dataPath + "/visualization-js")
    corpusPath = "/usr/share/biotext/GeniaChallenge/xml/"
    copy(corpusPath + "devel123.xml", dataPath)
    copy(corpusPath + "devel-with-duplicates123.xml", dataPath)
    copy(corpusPath + "train123.xml", dataPath)
    copy(corpusPath + "train-with-duplicates123.xml", dataPath)
    copy(corpusPath + "everything123.xml", dataPath)
    copy(corpusPath + "everything-with-duplicates123.xml", dataPath)
    copy(corpusPath + "test.xml", dataPath)
    copy("/usr/share/biotext/GeniaChallenge/extension-data/genia/task3/speculation-words.txt", dataPath)
    os.makedirs(os.path.join(options.output + "/data/evaluation-data"))
    shutil.copytree("/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/evaluation-tools-devel-gold", os.path.join(options.output + "/data/evaluation-data/evaluation-tools-devel-gold"))
    os.makedirs(os.path.join(options.output + "/data/evaluation-data/evaluation-temp"))
    
    print >> sys.stderr, "Copying additional files"
    copy("Readme/readme.pdf", os.path.join(options.output + "/readme.pdf"))
    copy("API-doc.html", os.path.join(options.output + "/API-doc.html"))
    copy("Settings.py", os.path.join(options.output + "/src/Settings.py"))
    # ID sets
    copy("/usr/share/biotext/GeniaChallenge/orig-data/IDsDEVEL", os.path.join(options.output + "/data/devel-set-genia-document-ids.txt"))
    copy("/usr/share/biotext/GeniaChallenge/orig-data/IDsTRAIN", os.path.join(options.output + "/data/train-set-genia-document-ids.txt"))
    copy("/usr/share/biotext/GeniaChallenge/orig-data/IDsEVERYTHING", os.path.join(options.output + "/data/everything-set-genia-document-ids.txt"))
    copy("/usr/share/biotext/GeniaChallenge/orig-data/IDsTEST", os.path.join(options.output + "/data/test-set-genia-document-ids.txt"))
    copy("/home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py", os.path.join(options.output + "/src/SharedTask/formatConversion/ProteinNameSplitter.py"))
    copy("install-svm-multiclass.sh", os.path.join(options.output + "/install-svm-multiclass.sh"))
    copy("gpl.txt", os.path.join(options.output + "/gpl.txt"))
    
    # Remove accidentally generated __init__.py
    os.remove(os.path.join(options.output + "/__init__.py"))
    
    print >> sys.stderr, "Building documentation"
    origDir = os.getcwd()
    os.chdir(os.path.join(options.output, "src"))
    subprocess.call("mv __init__.py ../temp ; epydoc -n \"Turku Event Extraction System\" -v --exclude networkx --parse-only --debug -o ../doc ./* ; mv ../temp __init__.py", shell=True)
    os.chdir(origDir)
    
    print >> sys.stderr, "Release done"