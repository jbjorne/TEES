import sys, os, shutil, codecs
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
from Utils.ProgressCounter import ProgressCounter
from Tools.Parser import Parser
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
from collections import defaultdict

parser = Parser()
unEscDict = {}
for k, v in parser.escDict.iteritems():
    unEscDict[v] = k

def getTokenText(tokenElement):
    # it's unlikely there would be newlines inside tokens
    return tokenElement.get("text").replace("\n", " ").replace("\r", " ").strip()

def getTokens(tokenizationElement):
    # order tokens by charOffset
    tokenElements = []
    for tokenElement in tokenizationElement.findall("token"):
        charOffset = tokenElement.get("charOffset")
        begin, end = charOffset.split("-")
        tokenElements.append( [int(begin), int(end), tokenElement] )
    tokenElements.sort()
    
    # Get token texts, and mark indices moved by splitting
    index = 0
    tokenTexts = []
    tokenIdMap = {} # zero-based
    splitFrom = None
    for tokenElement in tokenElements:
        token = tokenElement[2]
        if token.get("splitFrom") != None:
            if splitFrom != token.get("splitFrom"): # this token begins a new set of split tokens
                splitFrom = token.get("splitFrom")
                tokenTexts.append(getTokenText(token))
            else: # this token continues an existing set of split tokens
                tokenTexts[-1] = tokenTexts[-1] + getTokenText(token)
        else: # a non-split token
            splitFrom = None
            tokenTexts.append(getTokenText(token))
        tokenIdMap[index] = len(tokenTexts) - 1
        index += 1
    return tokenTexts, tokenIdMap

def exportTokenization(tokenizationElement, parseElement, sentenceElement, outFile):
    pennstring = None
    if parseElement != None:
        pennstring = parseElement.get("pennstring")
    if tokenizationElement != None and pennstring != None and pennstring.strip() != "":
        tokenTexts = []
        tokenTexts, tokenIdMap = getTokens(tokenizationElement)
        outFile.write(" ".join(tokenTexts) + "\n")
    else:
        outFile.write(" ".join(sentenceElement.get("text").strip().split()) + "\n")
    return True  

def exportPennTreeBank(parseElement, outFile):
    pennstring = None
    if parseElement != None:
        pennstring = parseElement.get("pennstring")
    if pennstring != None and pennstring.strip() != "":
        outFile.write(pennstring.strip())
    outFile.write("\n")
    if pennstring == None:
        return False
    else:
        return True

def exportStanfordDependencies(parseElement, tokenizationElement, outFile, tokenIdOffset=0):
    global unEscDict
    escDictKeys = sorted(unEscDict.keys())
    
    tokens = []
    # Collect tokens
    if tokenizationElement != None:
        tokens, tokenIdMap = getTokens(tokenizationElement)
        for i in range(len(tokens)):
            for key in escDictKeys:
                tokens[i] = tokens[i].replace(key, unEscDict[key])
        
    # Process dependencies
    if parseElement != None:
        for dependency in parseElement.findall("dependency"):
            if dependency.get("split") != None: # ignore dependencies created by protein name splitter
                continue
            t1Index = tokenIdMap[int(dependency.get("t1").split("_")[-1]) + tokenIdOffset] # tokenIdOffset can convert to zero-based
            t2Index = tokenIdMap[int(dependency.get("t2").split("_")[-1]) + tokenIdOffset] # tokenIdOffset can convert to zero-based
            assert t1Index < len(tokens), (t1Index, tokens, tokenIdMap, dependency.attrib)
            assert t2Index < len(tokens), (t2Index, tokens, tokenIdMap, dependency.attrib)
            t1 = tokens[t1Index] + "-" + str(t1Index + 1)
            t2 = tokens[t2Index] + "-" + str(t2Index + 1)
            outFile.write(dependency.get("type") + "(" + t1 + ", " + t2 + ")\n")
    outFile.write("\n") # one more newline to end the sentence (or to mark a sentence with no dependencies)
    if parseElement != None:
        return True
    else:
        return False

def export(input, output, parse, tokenization=None, toExport=["tok", "ptb", "sd"], inputSuffixes=None, clear=False, tokenIdOffset=0, exportIds=None):
    print >> sys.stderr, "##### Export Parse #####"
    if toExport == None:
        toExport = ["txt", "sentences", "tok", "ptb", "sd"]
    print >> sys.stderr, "Exporting parse formats", toExport
    
    if os.path.exists(output) and clear:
        shutil.rmtree(output)
    if not os.path.exists(output):
        os.makedirs(output)
    if inputSuffixes != None:
        inputFileNames = []
        for suffix in inputSuffixes:
            inputFileNames.append(input + suffix)
    else:
        inputFileNames = [input]

    for inputFileName in inputFileNames:
        print >> sys.stderr, "Processing input file", inputFileName
        corpusRoot = ETUtils.ETFromObj(inputFileName).getroot()
        documents = corpusRoot.findall("document")
        counter = ProgressCounter(len(documents), "Documents")
        counts = defaultdict(int)
        for document in documents:
            counter.update()
#             docId = document.get("pmid")
#             if docId == None:
#                 docId = document.get("origId")
#             if docId == None:
#                 docId = document.get("id")
            exportId = IXMLUtils.getExportId(document, exportIds)
            counts["document"] += 1
            # Open document output files
            outfiles = {}
            for fileExt in toExport:
                #print output, exportId , fileExt
                outfilePath = output + "/" + exportId + "." + fileExt
                if os.path.exists(outfilePath): # check for overlapping files
                    raise Exception("Export file '" + str(outfilePath) + "' already exists")
                outfiles[fileExt] = codecs.open(outfilePath, "wt", "utf-8")
            # Export document text
            if "txt" in outfiles and document.get("text") != None:
                outfiles["txt"].write(document.get("text"))
                counts["txt"] += 1
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
                if "sentences" in outfiles:
                    outfiles["sentences"].write(sentence.get("text").strip().replace("\n", " ").replace("\r", " ") + "\n")
                    counts["sentences"] += 1
                if "tok" in outfiles:
                    if exportTokenization(tokenizationElement, parseElement, sentence, outfiles["tok"]):
                        counts["tok"] += 1
                if "ptb" in outfiles:
                    if exportPennTreeBank(parseElement, outfiles["ptb"]):
                        counts["ptb"] += 1
                if "sd" in outfiles:
                    if exportStanfordDependencies(parseElement, tokenizationElement, outfiles["sd"], tokenIdOffset):
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
    optparser.add_option("-s", "--inputSuffixes", default=None, dest="inputSuffixes", help="e.g. '-train.xml,-devel.xml,-test.xml'", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory.")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="")
    optparser.add_option("-c", "--clear", default=False, action="store_true", dest="clear", help="")
    optparser.add_option("--tokenIdOffset", default=0, type="int", dest="tokenIdOffset", help="")
    (options, args) = optparser.parse_args()
    
    if options.inputSuffixes != None:
        options.inputSuffixes = options.inputSuffixes.split(",")
    export(options.input, options.output, options.parse, clear=options.clear, inputSuffixes=options.inputSuffixes, tokenIdOffset=options.tokenIdOffset)
