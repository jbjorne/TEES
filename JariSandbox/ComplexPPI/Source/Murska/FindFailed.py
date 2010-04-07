import sys, os
from optparse import OptionParser

def main(inDirs, outDir, failFileName):
    failFile = open(failFileName, "at")
    for inDir in inDirs:
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
                
                missing = []
                if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events.xml.gz")):
                    missing.append("events")
                else:
                    inFileSize = os.path.getsize(os.path.join(triple[0], inputFile))
                    outFileSize = os.path.getsize(os.path.join(outDir,triple[0],fileStem+"-events.xml.gz"))
                    if inFileSize == outFileSize:
                        missing.append("unchanged")
                if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_unflattened.xml.gz")):
                    missing.append("unflattened")
                if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_unflattened.xml.gz")):
                    missing.append("unflattened")
                if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_unflattened_task3.xml.gz")):
                    missing.append("unflattened_task3")
                if not os.path.exists(os.path.join(outDir,triple[0],fileStem+"-events_geniaformat.tar.gz")):
                    missing.append("geniaformat")
                if len(missing) > 0:
                    missing = sorted(missing)
                    print "Input file", inputFile, "is missing", missing
                    failFile.write(os.path.join(triple[0],inputFile)+ " ; " + missing + "\n")
            
    failFile.close()

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-f", "--failFile", default=None, dest="failFile", help="Failed input files will be listed here")
    (options, args) = optparser.parse_args()
    assert options.input != None
    if options.input.find(",") != -1:
        options.input = options.input.split(",")
    else:
        options.input = [options.input]
    for i in options.input:
        assert os.path.exists(i)
    assert options.output != None
    assert os.path.exists(options.output)
    
    main(options.input, options.output, options.failFile)
        