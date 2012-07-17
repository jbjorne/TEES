import sys, os
import codecs, time
from wikitools import wiki
from wikitools import api

def loadPages(site, pages, outDir, wait=3):
    count = 0
    for page in pages:
        print >> sys.stderr, "Loading page", page, "(" + str(count+1) +"/"+str(len(pages)) + ")"
        # define the params for the query
        params = {'action':'query', 'titles':page, 'export':None}
        # create the request object
        request = api.APIRequest(site, params)
        # query the API
        result = request.query()
        
        print >> sys.stderr, "Writing result"
        f = codecs.open(os.path.join(outDir, page+".xml"), "wt", "utf-8")
        f.write( result["query"]["export"]["*"] )
        f.close()
        
        print >> sys.stderr, "Sleeping"
        time.sleep(wait)
        count += 1
    
def readProteinNames(file):
    f = codecs.open(file, "rt", "utf-8")
    names = []
    for line in f:
        names.append(line.strip())
    return names

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

    optparser = OptionParser(description="Extract information from SubtiWiki for the BioNLP'11 REN task")
    optparser.add_option("-i", "--input", default="http://subtiwiki.uni-goettingen.de/wiki/api.php", dest="input", help="")
    optparser.add_option("-o", "--output", default="subtiwiki/pages", dest="output", help="")
    optparser.add_option("-n", "--names", default="subtiwiki/Subtiwiki-Protein-Coding-Genes-Names.txt", dest="names", help="")
    optparser.add_option("-s", "--synonyms", default="subtiwiki/Subtiwiki-Synonyms.csv", dest="synonyms", help="")
    (options, args) = optparser.parse_args()

    # create a Wiki object
    site = wiki.Wiki(options.input)
    loadPages(site, readProteinNames(options.names), options.output, wait=5)
    getSynonyms(options.output, options.synonyms)