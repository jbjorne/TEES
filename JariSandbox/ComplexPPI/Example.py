# example is a 3-tuple (or list) of the format: (id, class, features). id is a string,
# class is an int (-1 or +1) and features is a dictionary of int:float -pairs, where
# the int is the feature id and the float is the feature value

def writeExamples(examples, filename, commentLines=None):
    f = open(filename,"wt")
    for example in examples:
        f.write(str(example[1]))
        keys = example[2].keys()
        keys.sort()
        for key in keys:
            f.write(" " + str(key)+":"+str(example[2][key]))
        f.write(" # " + example[0] + "\n")
    f.close()

def divideExamples(examples, division):
    exampleSets = {}
    for example in examples:
        documentId = example[0].rsplit(".",2)[0]
        if not exampleSets.has_key(division[documentId]):
            exampleSets[division[documentId]] = []
        exampleSets[division[documentId]].append(example)
    return exampleSets

def divideExampleFile(exampleFileName, division, outputDir):
    f = open(exampleFileName, "rt")
    lines = f.readlines()
    f.close()
    
    divisionFiles = {}
    for line in lines:
        if line[0] == "#":
            continue
        id = line.split("#")[-1].strip()
        documentId = id.rsplit(".",2)[0]
        if not divisionFiles.has_key(division[documentId]):
            divisionFiles[division[documentId]] = open(outputDir+"/set"+str(division[documentId]),"wt")
        divisionFiles[division[documentId]].write(line)
    for v in divisionFiles.values():
        v.close()