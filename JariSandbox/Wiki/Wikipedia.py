import sys, os
import codecs, time
from wikitools import wiki
from wikitools import api
import re

def getCategoryTerms(text):
    inText = False
    firstParagraph = "BEFORE"
    for line in text.split("\n"):
        if not inText:
            if line.find("<text ") != -1:
                inText = True
            continue

        if line.startswith("[[Category:"):
            print line[len("[[Category:"):-2]
        if firstParagraph == "BEFORE":
            if len(line) == 0 or line[0:2] == "[[" or line[0:2] == "{{" or line.strip() == "":
                pass
            else:
                print line
                firstParagraph = "IN"
        if firstParagraph == "IN" and line.strip() == "":
            firstParagraph = "AFTER"
        if firstParagraph == "IN":
            words = re.findall('\[\[(.+?)\]\]', line)
            if len(words) > 0:
                print "FP-links:", words
                # Linkkisanoista kannattaa ottaa vielä erikseen ainakin viimeinen token.

def loadPages(site, pages, outDir, wait=3):
    count = 0
    if not os.path.exists(outDir):
        os.makedirs(outDir)
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
        getCategoryTerms(result["query"]["export"]["*"])
        f.write( result["query"]["export"]["*"] )
        f.close()
        
        print >> sys.stderr, "Sleeping"
        time.sleep(wait)
        count += 1
        
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
    optparser.add_option("-i", "--input", default="http://en.wikipedia.org/w/api.php", dest="input", help="")
    optparser.add_option("-o", "--output", default="/tmp/wikipedia", dest="output", help="")
    optparser.add_option("-n", "--names", default="subtiwiki/Subtiwiki-Protein-Coding-Genes-Names.txt", dest="names", help="")
    (options, args) = optparser.parse_args()

    # create a Wiki object
    site = wiki.Wiki(options.input)
    loadPages(site, ["Cheese", "Sausage"], options.output, wait=5)