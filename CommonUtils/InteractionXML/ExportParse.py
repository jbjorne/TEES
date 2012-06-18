import sys, os, shutil, codecs
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter
from Tools.CharniakJohnsonParser import escDict
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
from collections import defaultdict

unEscDict = {}
for k, v in escDict.iteritems():
    unEscDict[v] = k

def getTokenText(tokenElement):
    # it's unlikely there would be newlines inside tokens
    return tokenElement.get("text").replace("\n", " ").replace("\r", " ").strip()

def exportTokenization(tokenizationElement, parseElement, sentenceElement, outFile):
    pennstring = None
    if parseElement != None:
        pennstring = parseElement.get("pennstring")
    if tokenizationElement != None and pennstring != None and pennstring.strip() != "":
        tokenTexts = []
        for token in tokenizationElement.findall("token"):
            tokenTexts.append(getTokenText(token))
        outFile.write(" ".join(tokenTexts) + "\n")
    else:
        outFile.write(" ".join(sentenceElement.get("text").strip().split()) + "\n")       

def exportPennTreeBank(parseElement, outFile):
    pennstring = None
    if parseElement != None:
        pennstring = parseElement.get("pennstring")
    if pennstring != None and pennstring.strip() != "":
        outFile.write(pennstring.strip())
    outFile.write("\n")

def exportStanfordDependencies(parseElement, tokenizationElement, outFile):
    global unEscDict
    escDictKeys = sorted(unEscDict.keys())
    
    tokens = []
    tokenById = {}
    # Collect tokens
    if tokenizationElement != None:
        for token in tokenizationElement.findall("token"):
            charOffset = token.get("charOffset")
            begin, end = charOffset.split("-")
            tokenId = token.get("id")
            tokenList = [int(begin), int(end), getTokenText(token), tokenId, None]
            for key in escDictKeys:
                tokenList[2] = tokenList[2].replace(key, unEscDict[key])
            tokens.append(tokenList)
            assert tokenId not in tokenById
            tokenById[tokenId] = tokenList
        # Order tokens by charOffset
        tokens.sort()
        # Set token indices for dependencies
        for i in range(len(tokens)):
            tokens[i][-1] = str(i+1)
        
    # Process dependencies
    if parseElement != None:   
        for dependency in parseElement.findall("dependency"):
            t1 = tokenById[dependency.get("t1")]
            t2 = tokenById[dependency.get("t2")]
            outFile.write(dependency.get("type") + "(" + t1[2]+"-"+t1[-1] + ", " + t2[2]+"-"+t2[-1] + ")\n")
    outFile.write("\n") # one more newline to end the sentence (or to mark a sentence with no dependencies)

def export(input, output, parse, tokenization=None, toExport=["tok", "ptb", "sd"], clear=False):
    print >> sys.stderr, "##### Export Parse #####"
    corpusRoot = ETUtils.ETFromObj(input).getroot()
    
    if os.path.exists(output) and clear:
        shutil.rmtree(output)
    if not os.path.exists(output):
        os.makedirs(output)
    
    documents = corpusRoot.findall("document")
    counter = ProgressCounter(len(documents), "Documents")
    counts = defaultdict(int)
    for document in documents:
        counter.update()
        docId = document.get("pmid")
        counts["document"] += 1
        # Open document output files
        outfiles = {}
        for fileExt in toExport:
            outfilePath = output + "/" + docId + "." + fileExt
            assert not os.path.exists(outfilePath)
            outfiles[fileExt] = codecs.open(outfilePath, "wt", "utf-8")
        # Process all the sentences in the document
        for sentence in document.findall("sentence"):
            counts["sentence"] += 1
            parseElement = None
            for e in sentence.getiterator("parse"):
                if e.get("parser") == parse:
                    parseElement = e
                    counts["parse"] += 1
                    break
            if tokenization == None:
                tokenization = parseElement.get("tokenizer")
            tokenizationElement = None
            for e in sentence.getiterator("tokenization"):
                if e.get("tokenizer") == tokenization:
                    tokenizationElement = e
                    counts["tokenization"] += 1
                    break
            if "tok" in outfiles:
                exportTokenization(tokenizationElement, parseElement, sentence, outfiles["tok"])
                counts["tok"] += 1
            if "ptb" in outfiles:
                exportPennTreeBank(parseElement, outfiles["ptb"])
                counts["ptb"] += 1
            if "sd" in outfiles:
                exportStanfordDependencies(parseElement, tokenizationElement, outfiles["sd"])
                counts["sd"] += 1
        # Close document output files
        for fileExt in outfiles:
            outfiles[fileExt].close()
            outfiles[fileExt] = None
        
    print >> sys.stderr, "Parse export counts:"
    for k in sorted(counts.keys()):
        print >> sys.stderr, "  " + str(k) + ":", counts[k]

if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory.")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="")
    optparser.add_option("-c", "--clear", default=False, action="store_true", dest="clear", help="")
    (options, args) = optparser.parse_args()

    export(options.input, options.output, options.parse, clear=options.clear)
