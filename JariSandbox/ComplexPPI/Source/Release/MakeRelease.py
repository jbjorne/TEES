# After running, go to output/src and run:
# mv __init__.py ../temp ; epydoc -v --exclude networkx --parse-only --debug -o ../doc ./* ; mv ../temp __init__.py

import sys, os, shutil
import Preprocess

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
    #lines = ["import sys\nsys.path.append(\"" + (steps * "../") + "CommonUtils\")\n"] + lines
    lines = ["import sys\nsys.path.insert(0,\"" + (steps * "../") + "CommonUtils\")\n"] + lines
    f = open(os.path.join(dirname, pythonFile), "wt")
    f.writelines(lines)
    f.close()

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
    shutil.copytree("/usr/share/biotext/GeniaChallenge/release-files", dataPath)
    corpusPath = "/usr/share/biotext/GeniaChallenge/xml/"
    shutil.copy(corpusPath + "devel123.xml", dataPath)
    shutil.copy(corpusPath + "train123.xml", dataPath)
    shutil.copy(corpusPath + "everything123.xml", dataPath)
    shutil.copy(corpusPath + "test.xml", dataPath)
    os.makedirs(os.path.join(options.output + "/data/evaluation-data"))
    shutil.copytree("/usr/share/biotext/GeniaChallenge/extension-data/genia/evaluation-data/evaluation-tools-devel-gold", os.path.join(options.output + "/data/evaluation-data/evaluation-tools-devel-gold"))
    os.makedirs(os.path.join(options.output + "/data/evaluation-data/evaluation-temp"))
    
    print >> sys.stderr, "Copying additional files"
    shutil.copy("readme.txt", os.path.join(options.output + "/readme.txt"))
    shutil.copy("Settings.py", os.path.join(options.output + "/src/Settings.py"))