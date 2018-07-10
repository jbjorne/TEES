import sys, os
import shutil
import json
import zipfile
import csv
import tempfile

def getExperimentDirs(rootDir, experimentPatterns):
    experiments = []
    for root, subdirs, files in os.walk(rootDir):
        if "log.txt" in files:
            for pattern in experimentPatterns:
                if pattern in root:
                    experiments.append(root)
                    break
    return experiments

# def extractModels(inPath, output, modelDir):
#     assert input != None
#     assert output != None
#     assert input != output
#     if os.path.exists(output) and not preserveOutput:
#         shutil.rmtree(output)
#     if not os.path.exists(output):
#         os.makedirs(output)
#     
#         
#     
#     for subDir in os.listdir(input):
#         subDirAbs = os.path.join(input, subDir)
#         if os.path.isdir(subDirAbs) and hasTask(subDir, tasks): #subDir.split(".")[0] in tasks:
#             for suffix in ["devel", "test"]:
#                 if os.path.exists(os.path.join(subDirAbs, "model-" + suffix)):
#                     src = os.path.join(subDirAbs, "model-" + suffix)
#                     dst = os.path.join(output, subDir + "-" + suffix) #subDir.split(".")[0] + "-" + suffix)
#                     print >> sys.stderr, "Copying model", src, "to", dst
#                     shutil.copytree(src, dst)
#                 if os.path.exists(os.path.join(subDirAbs, "log.txt")):
#                     print >> sys.stderr, "Copying training log for", subDir
#                     shutil.copy2(os.path.join(subDirAbs, "log.txt"), os.path.join(output, subDir + "-train-log.txt"))
#                 if classificationOutput != None:
#                     if os.path.exists(os.path.join(subDirAbs, "classification-" + suffix)):
#                         src = os.path.join(subDirAbs, "classification-" + suffix + "/" + suffix + "-events.tar.gz")
#                         dst = os.path.join(classificationOutput, subDir + "-" + suffix + "-events.tar.gz")
#                         print src
#                         if os.path.exists(src):
#                             print >> sys.stderr, "Copying classification", src, "to", dst
#                             if not os.path.exists(os.path.dirname(dst)):
#                                 os.makedirs(os.path.dirname(dst))
#                             shutil.copy2(src, dst)

def renameExperiments(experiments, pathPatterns, inPath, templatePath):
    names = {}
    for experiment in experiments:
        #dirName = os.path.basename(experiment)
        newName = templatePath
        for key in pathPatterns:
            if key in experiment:
                for patternKey in pathPatterns[key]:
                    newName = newName.replace("{" + patternKey + "}", pathPatterns[key][patternKey])
        assert "{" not in newName, (experiment, newName)
        names[experiment] = newName
    return names

def process(inPath, outPath, parametersPath):
    if os.path.exists(outPath):
        shutil.rmtree(outPath)
    os.makedirs(outPath)
    print "Loading parameters from", parametersPath
    with open(parametersPath, "rt") as f:
        params = json.load(f)
    experiments = getExperimentDirs(inPath, params["experimentPatterns"])
    names = renameExperiments(experiments, params["pathPatterns"], inPath, params["pathTemplate"])
    print names
    collectLogs(names, outPath)
    collectPredictions(names, outPath)
    collectModels(names, outPath, params["values"])
    collectFiles(params.get("files", []), outPath)

def collectFiles(files, outPath):
    print "Collecting files"
    for filePath in files:
        print "Copying", filePath
        shutil.copy2(filePath, os.path.join(outPath, os.path.basename(filePath)))

def collectModels(names, outPath, values):
    print "Collecting models"
    #subPath = os.path.join(outPath, "models")
    #if not os.path.exists(subPath):
    #    os.makedirs(subPath)
    subPath = outPath
    valuesTempPath = tempfile.mktemp("tsv")
    for experiment in names:
        print "Copying", experiment
        z = zipfile.ZipFile(os.path.join(subPath, names[experiment] + ".zip"), "w", zipfile.ZIP_DEFLATED)
        modelPath = os.path.join(experiment, "model")
        for filename in os.listdir(modelPath):
            fileIsUpdated = False
            if filename == "TEES_MODEL_VALUES.tsv" and values != None:
                for corpusKey in values:
                    if corpusKey in experiment:
                        lines = None
                        with open(os.path.join(modelPath, filename)) as tsvfile:
                            lines = [x for x in csv.reader(tsvfile, delimiter="\t")]
                        for key in sorted(values[corpusKey].keys()):
                            lines.append([key, values[corpusKey][key]])
                        with open(valuesTempPath, "wb") as csv_file:
                            writer = csv.writer(csv_file, delimiter='\t')
                            for line in lines:
                                writer.writerow(line)
                        z.write(valuesTempPath, "TEES_MODEL_VALUES.tsv")
                        fileIsUpdated = True
                        break
            if not fileIsUpdated:
                z.write(os.path.join(modelPath, filename), filename)
        z.close()

def collectLogs(names, outPath):
    print "Collecting logs"
    z = zipfile.ZipFile(os.path.join(outPath, "logs.zip"), "w", zipfile.ZIP_DEFLATED)
    for experiment in names:
        z.write(os.path.join(experiment, "log.txt"), names[experiment] + "-log.txt")
    z.close()
    
def collectPredictions(names, outPath):
    print "Collecting predictions"
    z = zipfile.ZipFile(os.path.join(outPath, "predictions.zip"), "w", zipfile.ZIP_DEFLATED)
    for experiment in names:
        for subDir in ("classification-devel", "classification-test"):
            if not os.path.exists(os.path.join(experiment, subDir)):
                continue
            for filename in ("devel-pred.xml.gz", "devel-events.tar.gz", "test-pred.xml.gz", "test-events.tar.gz"):
                if not os.path.exists(os.path.join(experiment, subDir, filename)):
                    continue
                z.write(os.path.join(experiment, subDir, filename), names[experiment] + "-" + filename)
    z.close()
    
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="Make TEES release files.")
    optparser.add_option("-i", "--input", default=None, help="")
    optparser.add_option("-o", "--output", default=None, help="")
    optparser.add_option("-p", "--parameters", default=None, help="")
    (options, args) = optparser.parse_args()
    
    process(options.input, options.output, options.parameters)