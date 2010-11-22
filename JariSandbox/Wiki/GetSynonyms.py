import sys, os, codecs

def getSynonyms(inDir, outFilename):
    outFile = open(outFilename, "wt")
    for file in sorted(os.listdir(inDir)):
        if file.find("xml") != -1:
            protName = file.split(".")[0]
            outFile.write(protName)
            f = codecs.open(os.path.join(inDir, file), "rt", "utf-8")
            geneNameLine = False
            for line in f:
                if geneNameLine:
                    if line.find(protName) == -1:
                        print "Warning,", protName, "not found"
                        geneNameLine = False
                if line.find("||") == -1: # not table line
                    continue
                if line.find("Gene Name") != -1:
                    geneNameLine = True
                elif line.find("Synonyms") != -1:
                    synString = line.split("||")[1]
                    synString = synString.replace("''", "")
                    synonyms = synString.split(",")
                    for i in range(len(synonyms)):
                        #synonyms[i] = synonyms[i].strip()
                        synonym = synonyms[i].strip()
                        if synonym != "":
                            outFile.write(","+synonym)
            outFile.write("\n")             

if __name__=="__main__":
    import sys
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default="subtiwiki/pages", dest="input", help="")
    optparser.add_option("-o", "--output", default="subtiwiki/Subtiwiki-Synonyms.csv", dest="output", help="")
    (options, args) = optparser.parse_args()

    getSynonyms(options.input, options.output)