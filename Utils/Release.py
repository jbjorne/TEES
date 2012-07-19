import sys,os
import types
import shutil
import filecmp
import subprocess
mainTEESDir = os.path.abspath(os.path.join(__file__, "../.."))
print mainTEESDir
sys.path.append(mainTEESDir)

def listExecutables(filter=["Core", "FeatureBuilders", "InteractionXML", "GeniaEventsToSharedTask"]):
    tableTitleLines = "| Program | Location | Description |\n"
    tableTitleLines += "|:-----------|:-----------|:-----------|"
    mainTableTitleLines = "| Program | Description |\n"
    mainTableTitleLines += "|:-----------|:-----------|"
    categories = ["Main Programs", "Tool Wrappers", "Other Programs"]
    programs = {}
    for category in categories:
        programs[category] = []
    for triple in os.walk(mainTEESDir):
        for filename in sorted(triple[2]):
            skip = False
            for filterRule in filter:
                if filterRule in os.path.join(triple[0], filename):
                    skip = True
                    break
            if skip:
                continue
            if filename.endswith(".py"):
                f = open(os.path.join(triple[0], filename), "rt")
                lines = f.readlines()
                f.close()
                isExecutable = False
                description = ""
                for line in lines:
                    if "optparser = OptionParser(" in line:
                        assert line.count("\"") in [0, 2], line
                        if line.count("\"") == 2:
                            description = line.split("\"")[1]
                            description = description.split("\\n", 1)[-1]
                            description = description.split(".")[0]
                            description = description.strip()
                        isExecutable = True
                if isExecutable:
                    subDir = triple[0][len(mainTEESDir)+1:].strip()
                    if subDir == "":
                        category = "Main Programs"
                    elif "Tools" in subDir or "Preprocessor" in filename:
                        category = "Tool Wrappers"
                    else:
                        category = "Other Programs"
                    programs[category].append( [subDir, filename, description] )
    
    for category in categories:
        print "##", category
        if category == "Main Programs":
            print mainTableTitleLines
        else:
            print tableTitleLines
        for program in sorted(programs[category]):
            if program[0] == "":
                print "|", program[1], "|", program[2], "|"
            else:
                print "|", program[1], "|", program[0], "|", program[2], "|"
        print

def extractModels(input, output, tasks, classificationOutput=None):
    assert input != None
    assert output != None
    assert input != output
    if os.path.exists(output):
        shutil.rmtree(output)
    if not os.path.exists(output):
        os.makedirs(output)
    for subDir in os.listdir(input):
        subDirAbs = os.path.join(input, subDir)
        if os.path.isdir(subDirAbs) and subDir.split(".")[0] in tasks:
            for suffix in ["devel", "test"]:
                if os.path.exists(os.path.join(subDirAbs, "model-" + suffix)):
                    src = os.path.join(subDirAbs, "model-" + suffix)
                    dst = os.path.join(output, subDir.split(".")[0] + "-" + suffix)
                    print >> sys.stderr, "Copying model", src, "to", dst
                    shutil.copytree(src, dst)
                if os.path.exists(os.path.join(subDirAbs, "log.txt")):
                    print >> sys.stderr, "Copying training log for", subDir
                    shutil.copy2(os.path.join(subDirAbs, "log.txt"), os.path.join(output, subDir.split(".")[0] + "-train-log.txt"))
                if classificationOutput != None:
                    if os.path.exists(os.path.join(subDirAbs, "classification-" + suffix)):
                        src = os.path.join(subDirAbs, "classification-" + suffix + "/" + suffix + "-events.tar.gz")
                        dst = os.path.join(classificationOutput, subDir.split(".")[0] + "-" + suffix + "-events.tar.gz")
                        print src
                        if os.path.exists(src):
                            print >> sys.stderr, "Copying classification", src, "to", dst
                            if not os.path.exists(os.path.dirname(dst)):
                                os.makedirs(os.path.dirname(dst))
                            shutil.copy2(src, dst)
                
def linkDuplicates(input, output):
    if os.path.exists(output):
        print >> sys.stderr, "Removing output directory"
        shutil.rmtree(output)
    print >> sys.stderr, "Copying input directory"
    shutil.copytree(input, output)
    print >> sys.stderr, "Listing files"
    files = []
    for triple in os.walk(output):
        for filename in triple[2]:
            filePath = os.path.join(triple[0], filename)
            if os.path.isfile(filePath):
                files.append(filePath)
    print >> sys.stderr, "Detecting duplicates"
    duplicates = {}
    for i in range(len(files)-1):
        if os.path.getsize(files[i]) > 1000:
            print >> sys.stderr, "Processing", files[i]
            for j in range(i+1, len(files)):
                if filecmp.cmp(files[i], files[j], shallow=False):
                    if files[i] not in duplicates:
                        duplicates[files[i]] = []
                    duplicates[files[i]].append(files[j])
        else:
            print >> sys.stderr, "Skipping small file", files[i]
    print >> sys.stderr, "Duplicates found:"
    for key in sorted(duplicates.keys()):
        print key, sorted(duplicates[key])
    print >> sys.stderr, "Replacing duplicates with links"
    for original in sorted(duplicates.keys()):
        for duplicate in duplicates[original]:
            os.remove(duplicate)
            relPath = os.path.relpath(original, os.path.commonprefix((original, duplicate)))
            lnCommand = "cd " + os.path.dirname(duplicate) + "; ln -s " + relPath + " " + os.path.basename(duplicate) + "; cd -"
            print >> sys.stderr, "Linking:", lnCommand
            subprocess.call(lnCommand, shell=True)

def buildModels(output, tasks, connection, dummy=False):
    """
    Build the release models.
    
    This function should be run on the cluster, so the connection argument is the
    same for both the batch system and the train-program it runs.
    """
    global mainTEESDir
    from batch import batch
    for task in tasks:
        taskName = task
        if task in ["GE", "GE09"]:
            taskName += ".2"
        command = "python " + os.path.join(mainTEESDir, "train.py") + " -t " + taskName + " -o %o/%j -c " + connection + " --clearAll"
        batch(command, input=None, connection=connection, jobTag=task, output=output, debug=True, dummy=dummy)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(description="Make TEES release files.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("-a", "--action", default=None, dest="action", help="")
    optparser.add_option("-t", "--tasks", default="GE,EPI,ID,BB,BI,BI-FULL,GE09,CO,REL,REN,DDI,DDI-FULL", dest="tasks", help="")
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option("-d", "--dummy", action="store_true", default=False, dest="dummy", help="")
    optparser.add_option("--classificationOutput", default=None, dest="classificationOutput", help="")
    (options, args) = optparser.parse_args()
    assert options.action in ["CONVERT_CORPORA", "BUILD_MODELS", "EXTRACT_MODELS", "PACKAGE_MODELS", "BUILD_APIDOC", "LIST_EXECUTABLES"]
    options.tasks = options.tasks.split(",")
    
    if options.action == "LIST_EXECUTABLES":
        listExecutables()
    elif options.action == "BUILD_MODELS":
        buildModels(options.output, options.tasks, options.connection, options.dummy)
    elif options.action == "EXTRACT_MODELS":
        extractModels(options.input, options.output, options.tasks, options.classificationOutput)
    elif options.action == "PACKAGE_MODELS":
        linkDuplicates(options.input, options.output)