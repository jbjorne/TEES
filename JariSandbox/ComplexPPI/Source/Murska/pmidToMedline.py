import sys, os, shutil, tarfile
from optparse import OptionParser

def mapIds(eventFile, idDict):
    try:
        f = tarfile.open(eventFile)
        for name in f.getnames():
            if name.find(".a2.t1") != -1:
                id = name.rsplit(".",2)[0]
                idDict[id] = eventFile
        f.close()
    except:
        print "Failed to open", eventFile

def main(inDir, outDir):
    idDict = {}
    for triple in os.walk(inDir):
        print "Processing", triple[0] 
        inputFiles = []
        for filename in triple[2]:
            if filename.find("geniaformat.tar.gz") != -1:
                mapIds(os.path.join(triple[0], filename), idDict)
    
    f = open(outDir, "wt")
    for k in sorted(idDict.keys()):
        f.write(k + ": " + idDict[k] + "\n")
    f.close()

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    
    main(options.input, options.output)
        