import sys, os
from optparse import OptionParser

def main(inDir, failFileName):
    failFile = open(failFileName, "at")
    for triple in os.walk(inDir): 
        for filename in triple[2]:
            if filename[-7:] == ".stderr":
                print "Processing", filename
                f = open(os.path.join(triple[0],filename), "rt")
                medlineName = None
                errorLineCount = 0
                for line in f.readlines():
                    medlinePos = line.find("medline")
                    if medlinePos != -1:
                        medlineName = line[medlinePos:medlinePos+32]
                    if line.find("Traceback") != -1:
                        failFile.write(medlineName+"\n")
                        print medlineName, "failed"
                        errorLineCount = 20
                    if errorLineCount > 0:
                        print "    " + line[:-1]
                        errorLineCount -= 1
                f.close()
    failFile.close()

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-f", "--failFile", default=None, dest="failFile", help="Failed input files will be listed here")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    
    main(options.input, options.failFile)
        