import sys, os
import csv
import copy

MARKERS = {
    "devel":[("------------ Empty devel classification ------------", "=== EXIT STEP EMPTY"), 
             ("Generation of files for evaluation", "=== EXIT STEP ST-CONVERT")],
    "test":[("------------ Test set classification ------------", "EventDetector:CLASSIFY(EXIT)"), 
             ("Generation of files for evaluation", "=== EXIT STEP ST-CONVERT")],
}

GENIA_COLUMNS = ["evaluation", "category", "gold", "gold_match", "answer", "answer_match", "precision", "recall", "fscore"]

def parseResults(lines):
    lines = lines[1:]
    rows = []
    evaluation = None
    for line in lines:
        if line[0] == "-":
            continue
        if line.startswith ("####"):
            evaluation = line.strip("#").strip()
            if "strict" in evaluation: evaluation = "strict"
            elif "decomposition" in evaluation: evaluation = "decomposition"
            elif "approximate" in evaluation: evaluation = "approximate"
        elif "Event Class" in line:
            continue
        else:
            splits = line.strip().split()
            assert len(splits) >= 10, (line, splits, lines)
            # define row name
            name = splits[0]
            name = name.replace("=","")
            name = name.replace("[","")
            name = name.replace("]","")
            assert evaluation != None
            row = {"category":name, "evaluation":evaluation}
            # add columns
            row["gold"] = int(splits[1])
            row["gold_match"] = int(splits[3][:-1])
            row["answer"] = int(splits[4])
            row["answer_match"] = int(splits[6][:-1])
            row["recall"] = float(splits[7])
            row["precision"] = float(splits[8])
            row["fscore"] = float(splits[9])
            rows.append(row)
    return rows

def getLines(lines, boundaries):
    for begin, end in boundaries:
        subset = None
        endFound = False
        for line in lines:
            if subset == None and begin in line:
                subset = []
            elif subset != None and end in line: # Look for the end marker only after finding a begin marker
                endFound = True
                break
            elif subset != None:
                subset.append(line)
        if not endFound:
            print >> sys.stderr, "Warning, couldn't find end marker for log section", (begin, end)
            return None
        lines = subset
    return subset

def getGENIAResults(lines, markers=None):
    lines = getLines(lines, markers)
    fullResults = mainResult = None  
    if lines != None:
        fullResults = [x.split("\t", 1)[-1] for x in lines]
        mainResult = getLines(fullResults, [("##### approximate span and recursive mode #####", "##### event decomposition in the approximate span mode #####")])
        for line in mainResult:
            if "==[ALL-TOTAL]==" in line:
                mainResult = line
                break
#         if outPath != None:
#             with open(outPath, "wt") as f:
#                 f.write("------------ Primary Result ------------\n")
#                 f.write(mainResult)
#                 f.write("\n")
#                 f.write("------------ All Results ------------\n")
#                 for line in fullResults:
#                     f.write(line)
    return fullResults, mainResult                   

def collectResults(inDir, inPattern, outStem=None, addEmpties=False):
    print >> sys.stderr, "Collecting results from:", inDir
    models = []
    for filename in os.listdir(inDir):
        fullPath = os.path.join(inDir, filename)
        if os.path.isdir(fullPath) and (inPattern is None or inPattern.match(filename)):
            models.append(fullPath)
    models.sort()
    print >> sys.stderr, "Collecting results for models:", models
    results = {"devel":[], "test":[]}
    for model in models:
        modelName = os.path.basename(model)
        logPath = os.path.join(model, "log.txt")
        print >> sys.stderr, "Reading model:", modelName
        if not os.path.exists(logPath):
            print >> sys.stderr, "Warning, no log file"
            continue
        logLines = None
        print >> sys.stderr, "Reading log file:", logPath
        with open(logPath, "rt") as f:
            logLines = f.readlines()
        for setName in "devel", "test":
            fullResults, mainResult = getGENIAResults(logLines, MARKERS[setName])
            if fullResults == None:
                rows = []
                if addEmpties:
                    emptyRow = {x:"" for x in GENIA_COLUMNS}
                    emptyRow["evaluation"] = "approximate"
                    emptyRow["category"] = "ALL-TOTAL"
                    rows.append(emptyRow)
            else:
                rows = parseResults(fullResults)
            for row in rows:
                row["submission"] = modelName
            results[setName].extend(rows)
            if mainResult != None:
                print >> sys.stderr, setName, "=", mainResult.strip()
            else:
                print >> sys.stderr, "Warning, no result"
    if outStem != None:
        for setName in "devel", "test":
            outPath = outStem + "-" + setName + ".tsv"
            if len(results[setName]) < 1:
                continue
            print >> sys.stderr, "Writing results to", outPath
            with open(outPath, "wt") as f:
                dw = csv.DictWriter(f, ["submission"] + GENIA_COLUMNS, delimiter='\t')
                dw.writeheader()
                dw.writerows(results[setName])
    combineResults(results, outStem)
    
def combineResults(results, outStem):
    print >> sys.stderr, "Combining results"
    combined = {}
    for setName in "devel", "test":
        for row in results[setName]:
            if row["category"] != "ALL-TOTAL" or row["evaluation"] != "approximate":
                continue
            submission = row["submission"]
            if row["submission"] not in combined:
                combined[submission] = {"submission":submission}
            for key in row.keys():
                if key in ("precision", "recall", "fscore"):
                    combined[submission][key + ":" + setName] = row.pop(key)
    combined = [combined[x] for x in sorted(combined.keys())]
    print combined
    if outStem != None:
        outPath = outStem + "-combined.tsv"
        print >> sys.stderr, "Writing combined results to", outPath
        with open(outPath, "wt") as f:
            cols = ("precision", "recall", "fscore")
            cols = ["submission"] + [x + ":devel" for x in cols] + [x + ":test" for x in cols]
            dw = csv.DictWriter(f, cols, delimiter='\t', extrasaction='ignore')
            dw.writeheader()
            dw.writerows(combined)
    return combined

if __name__== "__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="Collect TEES results from log files and models")
    optparser.add_option("-i", "--input", default=None, help="Input directory")
    optparser.add_option("-o", "--output", default=None, help="Output directory")
    optparser.add_option("-p", "--pattern", default=None, help="Input directory subdirectories (optional)")
    optparser.add_option("-e", "--empties", default=False, action="store_true", help="")
    (options, args) = optparser.parse_args()

    collectResults(options.input, options.pattern, options.output, options.empties)