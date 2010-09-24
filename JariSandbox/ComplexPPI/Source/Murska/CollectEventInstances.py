import sys, os, shutil
from optparse import OptionParser

def main(inDir, outDir):
    currDir = None
    outFile = None
    
    for triple in os.walk(inDir):
        print "Processing", triple[0]
        
        if currDir != triple[0]:
            if outFile != None:
                outFile.close()
            currDir = triple[0]
            outFile = open(os.path.join(triple[0], "event-instances.csv"), "wt")
         
        inputFiles = []
        for filename in triple[2]:
            if filename in selectedFiles:
                inputFiles.append(filename)
        if len(inputFiles) == 0:
            continue
        
        for inputFile in inputFiles:
            print "Copying", inputFile 
            if not os.path.exists(os.path.join(outDir,triple[0])):
                os.makedirs(os.path.join(outDir,triple[0]))
            shutil.copy( os.path.join(triple[0],inputFile), os.path.join(outDir,triple[0],inputFile) ) 

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    
    main(options.input, options.output)