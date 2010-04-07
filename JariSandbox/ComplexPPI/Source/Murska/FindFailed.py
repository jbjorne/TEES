import sys, os
from optparse import OptionParser

def main(inDir, outDir, failFileName):
    failFile = open(failFileName, "at")
    for triple in os.walk(inDir):
        print "Processing", triple[0] 
        inputFiles = []
        for filename in triple[2]:
            if filename[-7:] == ".xml.gz" or filename[-4:] == ".xml":
                inputFiles.append(filename)
        if len(inputFiles) == 0:
            continue
        
        for inputFile in inputFiles:
            if inputFile[-7:] == ".xml.gz":
                fileStem = inputFile[:-7]
            elif inputFile[-4:] == ".xml":
                fileStem = inputFile[:-4]
            if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events.xml.gz")):
                print "Input file", inputFile, "has failed"
                failFile.write(os.path.join(triple[0],inputFile)+"\n")
            missing = []
            if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_unflattened.xml.gz")):
                missing.append("unflattened")
            if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_unflattened_task3.xml.gz")):
                missing.append("unflattened_task3")
            if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_geniaformat.tar.gz")):
                missing.append("geniaformat")
            if len(missing) > 0:
                print "Input file", inputFile, "is missing", sorted(missing)
            
    failFile.close()

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-f", "--failFile", default=None, dest="failFile", help="Failed input files will be listed here")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    assert options.output != None
    assert os.path.exists(options.output)
    
    main(options.input, options.output, options.failFile)
        