import sys,os
import time
import shutil
import subprocess
import tempfile
import codecs
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Settings as Settings
import Utils.Download as Download
import Tool
import StanfordParser
from ProcessUtils import *


escDict={"-LRB-":"(",
         "-RRB-":")",
         "-LCB-":"{",
         "-RCB-":"}",
         "-LSB-":"[",
         "-RSB-":"]",
         "``":"\"",
         "''":"\"",
         "\\/":"/",
         "\\*":"*"}

def install(destDir=None, downloadDir=None, redownload=False, updateLocalSettings=False):
    url = Settings.URL["BLLIP_SOURCE"]
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH) + "/tools/download"
    if destDir == None:
        destDir = Settings.DATAPATH + "/tools/BLLIP"
    items = Download.downloadAndExtract(url, destDir, downloadDir + "/bllip.zip", None, False)
    print >> sys.stderr, "Installing BLLIP parser"
    Tool.testPrograms("BLLIP parser", ["make", "flex"], {"flex":"flex --version"})
    parserPath = Download.getTopDir(destDir, items)
    cwd = os.getcwd()
    os.chdir(parserPath)
    print >> sys.stderr, "Compiling first-stage parser"
    subprocess.call("make", shell=True)
    print >> sys.stderr, "Compiling second-stage parser"
    subprocess.call("make reranker", shell=True)
    os.chdir(cwd)
    print >> sys.stderr, "Installing the McClosky biomedical parsing model"
    url = "http://bllip.cs.brown.edu/download/bioparsingmodel-rel1.tar.gz"
    Download.downloadAndExtract(url, destDir, downloadDir, None)
    bioModelDir = os.path.abspath(destDir + "/biomodel")
    # Check that everything works
    Tool.finalizeInstall(["first-stage/PARSE/parseIt", "second-stage/programs/features/best-parses"], 
                         {"first-stage/PARSE/parseIt":"first-stage/PARSE/parseIt " + bioModelDir + "/parser/ < /dev/null",
                          "second-stage/programs/features/best-parses":"second-stage/programs/features/best-parses -l " + bioModelDir + "/reranker/features.gz " + bioModelDir + "/reranker/weights.gz < /dev/null"},
                         parserPath, {"BLLIP_PARSER_DIR":os.path.abspath(parserPath), 
                                      "MCCLOSKY_BIOPARSINGMODEL_DIR":bioModelDir}, updateLocalSettings)
            
def readPenn(treeLine):
    global escDict
    escSymbols = sorted(escDict.keys())
    tokens = []
    phrases = []
    stack = []
    if treeLine.strip() != "":
        # Add tokens
        prevSplit = None
        tokenCount = 0
        splitCount = 0
        splits = treeLine.split()
        for split in splits:
            if split[0] != "(":
                tokenText = split
                while tokenText[-1] == ")":
                    tokenText = tokenText[:-1]
                    if tokenText[-1] == ")": # this isn't the closing parenthesis for the current token
                        stackTop = stack.pop()
                        phrases.append( (stackTop[0], tokenCount, stackTop[1]) )
                origTokenText = tokenText
                for escSymbol in escSymbols:
                    tokenText = tokenText.replace(escSymbol, escDict[escSymbol])
                
                posText = prevSplit
                while posText[0] == "(":
                    posText = posText[1:]
                for escSymbol in escSymbols:
                    posText = posText.replace(escSymbol, escDict[escSymbol])
                tokens.append( (tokenText, posText, origTokenText) )
                tokenCount += 1
            elif splits[splitCount + 1][0] == "(":
                stack.append( (tokenCount, split[1:]) )
            prevSplit = split
            splitCount += 1
    return tokens, phrases

def insertTokens(tokens, sentence, tokenization, idStem="bt_", errorNotes=None):
    tokenCount = 0
    start = 0
    prevStart = None
    for tokenText, posTag, origTokenText in tokens:
        sText = sentence.get("text")
        # Determine offsets
        cStart = sText.find(tokenText, start)
        #assert cStart != -1, (tokenText, tokens, posTag, start, sText)
        if cStart == -1: # Try again with original text (sometimes escaping can remove correct text)
            cStart = sText.find(origTokenText, start)
        if cStart == -1 and prevStart != None: # Try again with the previous position, sometimes the parser duplicates tokens
            cStart = sText.find(origTokenText, prevStart)
            if cStart != -1:
                start = prevStart
                print >> sys.stderr, "Warning, token duplication", (tokenText, tokens, posTag, start, sText, errorNotes)
        if cStart == -1:
            print >> sys.stderr, "Token alignment error", (tokenText, tokens, posTag, start, sText, errorNotes)
            for subElement in [x for x in tokenization]:
                tokenization.remove(subElement)
            return False
        cEnd = cStart + len(tokenText)
        prevStart = start
        start = cStart + len(tokenText)
        # Make element
        token = ET.Element("token")
        token.set("id", idStem + str(tokenCount))
        token.set("text", tokenText)
        token.set("POS", posTag)
        token.set("charOffset", str(cStart) + "-" + str(cEnd)) # NOTE: check
        tokenization.append(token)
        tokenCount += 1
    return True

def insertPhrases(phrases, parse, tokenElements, idStem="bp_"):
    count = 0
    phrases.sort()
    for phrase in phrases:
        phraseElement = ET.Element("phrase")
        phraseElement.set("type", phrase[2])
        phraseElement.set("id", idStem + str(count))
        phraseElement.set("begin", str(phrase[0]))
        phraseElement.set("end", str(phrase[1]))
        t1 = None
        t2 = None
        if phrase[0] < len(tokenElements):
            t1 = tokenElements[phrase[0]]
        if phrase[1] < len(tokenElements):
            t2 = tokenElements[phrase[1]]
        if t1 != None and t2 != None:
            phraseElement.set("charOffset", t1.get("charOffset").split("-")[0] + "-" + t2.get("charOffset").split("-")[-1])
        parse.append(phraseElement)
        count += 1



def insertParse(sentence, treeLine, parseName="McCC", tokenizationName = None, makePhraseElements=True, extraAttributes={}, docId=None):
    # Find or create container elements
    analyses = setDefaultElement(sentence, "analyses")#"sentenceanalyses")
    #tokenizations = setDefaultElement(sentenceAnalyses, "tokenizations")
    #parses = setDefaultElement(sentenceAnalyses, "parses")
    # Check that the parse does not exist
    for prevParse in analyses.findall("parse"):
        assert prevParse.get("parser") != parseName
    # Create a new parse element
    parse = ET.Element("parse")
    parse.set("parser", parseName)
    if tokenizationName == None:
        parse.set("tokenizer", parseName)
    else:
        parse.set("tokenizer", tokenizationName)
    analyses.insert(getPrevElementIndex(analyses, "parse"), parse)
    
    tokenByIndex = {}
    parse.set("pennstring", treeLine.strip())
    for attr in sorted(extraAttributes.keys()):
        parse.set(attr, extraAttributes[attr])
    if treeLine.strip() == "":
        return False
    else:
        tokens, phrases = readPenn(treeLine)
        # Get tokenization
        if tokenizationName == None: # Parser-generated tokens
            for prevTokenization in analyses.findall("tokenization"):
                assert prevTokenization.get("tokenizer") != tokenizationName
            tokenization = ET.Element("tokenization")
            tokenization.set("tokenizer", parseName)
            for attr in sorted(extraAttributes.keys()): # add the parser extra attributes to the parser generated tokenization 
                tokenization.set(attr, extraAttributes[attr])
            analyses.insert(getElementIndex(analyses, parse), tokenization)
            # Insert tokens to parse
            insertTokens(tokens, sentence, tokenization, errorNotes=(sentence.get("id"), docId))
        else:
            tokenization = getElementByAttrib(analyses, "tokenization", {"tokenizer":tokenizationName})
        # Insert phrases to parse
        if makePhraseElements:
            insertPhrases(phrases, parse, tokenization.findall("token"))
    return True           
        
def runBLLIPParser(input, output, tokenizer=False, pathBioModel=None):
    if tokenizer:
        print >> sys.stderr, "Running BLLIP parser with tokenization"
    else:
        print >> sys.stderr, "Running BLLIP parser without tokenization"
    #args = ["./parse-50best-McClosky.sh"]
    #return subprocess.Popen(args, 
    #    stdin=codecs.open(input, "rt", "utf-8"),
    #    stdout=codecs.open(output, "wt", "utf-8"), shell=True)

    assert os.path.exists(pathBioModel), pathBioModel
    if tokenizer:
        firstStageArgs = ["first-stage/PARSE/parseIt", "-l999", "-N50" , pathBioModel+"/parser/"]
    else:
        firstStageArgs = ["first-stage/PARSE/parseIt", "-l999", "-N50" , "-K", pathBioModel+"/parser/"]
    secondStageArgs = ["second-stage/programs/features/best-parses", "-l", pathBioModel+"/reranker/features.gz", pathBioModel+"/reranker/weights.gz"]
    
    firstStage = subprocess.Popen(firstStageArgs,
                                  stdin=codecs.open(input, "rt", "utf-8"),
                                  stdout=subprocess.PIPE)
    secondStage = subprocess.Popen(secondStageArgs,
                                   stdin=firstStage.stdout,
                                   stdout=codecs.open(output, "wt", "utf-8"))
    return ProcessWrapper([firstStage, secondStage])

def getSentences(corpusRoot, requireEntities=False, skipIds=[], skipParsed=True):
    for sentence in corpusRoot.getiterator("sentence"):
        if sentence.get("id") in skipIds:
            print >> sys.stderr, "Skipping sentence", sentence.get("id")
            continue
        if requireEntities:
            if sentence.find("entity") == None:
                continue
        if skipParsed:
            if ETUtils.getElementByAttrib(sentence, "parse", {"parser":"McCC"}) != None:
                continue
        yield sentence

def parse(input, output=None, tokenizationName=None, parseName="McCC", requireEntities=False, skipIds=[], skipParsed=True, timeout=600, makePhraseElements=True, debug=False, pathParser=None, pathBioModel=None, timestamp=True):
    global escDict
    print >> sys.stderr, "BLLIP parser"
    parseTimeStamp = time.strftime("%d.%m.%y %H:%M:%S")
    print >> sys.stderr, "BLLIP time stamp:", parseTimeStamp
    
    if pathParser == None:
        pathParser = Settings.BLLIP_PARSER_DIR
    print >> sys.stderr, "BLLIP parser at:", pathParser
    if pathBioModel == None:
        pathBioModel = Settings.MCCLOSKY_BIOPARSINGMODEL_DIR
    print >> sys.stderr, "Biomodel at:", pathBioModel
    if requireEntities:
        print >> sys.stderr, "Parsing only sentences with entities"
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    if debug:
        print >> sys.stderr, "BLLIP parser workdir", workdir
    infileName = os.path.join(workdir, "parser-input.txt")
    infile = codecs.open(infileName, "wt", "utf-8")
    numCorpusSentences = 0
    if tokenizationName == None or tokenizationName == "PARSED_TEXT": # Parser does tokenization
        if tokenizationName == None:
            print >> sys.stderr, "Parser does the tokenization"
        else:
            print >> sys.stderr, "Parsing tokenized text"
        #for sentence in corpusRoot.getiterator("sentence"):
        for sentence in getSentences(corpusRoot, requireEntities, skipIds, skipParsed):
            infile.write("<s> " + sentence.get("text") + " </s>\n")
            numCorpusSentences += 1
    else: # Use existing tokenization
        print >> sys.stderr, "Using existing tokenization", tokenizationName 
        for sentence in getSentences(corpusRoot, requireEntities, skipIds, skipParsed):
            tokenization = getElementByAttrib(sentence.find("analyses"), "tokenization", {"tokenizer":tokenizationName})
            assert tokenization.get("tokenizer") == tokenizationName
            s = ""
            for token in tokenization.findall("token"):
                s += token.get("text") + " "
            infile.write("<s> " + s + "</s>\n")
            numCorpusSentences += 1
    infile.close()
    
    #PARSERROOT=/home/smp/tools/McClosky-Charniak/reranking-parser
    #BIOPARSINGMODEL=/home/smp/tools/McClosky-Charniak/reranking-parser/biomodel
    #${PARSERROOT}/first-stage/PARSE/parseIt -K -l399 -N50 ${BIOPARSINGMODEL}/parser/ $* | ${PARSERROOT}/second-stage/programs/features/best-parses -l ${BIOPARSINGMODEL}/reranker/features.gz ${BIOPARSINGMODEL}/reranker/weights.gz
    
    # Run parser
    #print >> sys.stderr, "Running parser", pathParser + "/parse.sh"
    cwd = os.getcwd()
    os.chdir(pathParser)
    if tokenizationName == None:
        bllipOutput = runSentenceProcess(runBLLIPParser, pathParser, infileName, workdir, False, "BLLIPParser", "Parsing", timeout=timeout, processArgs={"tokenizer":True, "pathBioModel":pathBioModel})   
    else:
        if tokenizationName == "PARSED_TEXT": # The sentence strings are already tokenized
            tokenizationName = None
        bllipOutput = runSentenceProcess(runBLLIPParser, pathParser, infileName, workdir, False, "BLLIPParser", "Parsing", timeout=timeout, processArgs={"tokenizer":False, "pathBioModel":pathBioModel})   
#    args = [charniakJohnsonParserDir + "/parse-50best-McClosky.sh"]
#    #bioParsingModel = charniakJohnsonParserDir + "/first-stage/DATA-McClosky"
#    #args = charniakJohnsonParserDir + "/first-stage/PARSE/parseIt -K -l399 -N50 " + bioParsingModel + "/parser | " + charniakJohnsonParserDir + "/second-stage/programs/features/best-parses -l " + bioParsingModel + "/reranker/features.gz " + bioParsingModel + "/reranker/weights.gz"
    os.chdir(cwd)
    
    treeFile = codecs.open(bllipOutput, "rt", "utf-8")
    print >> sys.stderr, "Inserting parses"
    # Add output to sentences
    failCount = 0
    for sentence in getSentences(corpusRoot, requireEntities, skipIds, skipParsed):        
        treeLine = treeFile.readline()
        extraAttributes={"source":"TEES"} # parser was run through this wrapper
        if timestamp:
            extraAttributes["date"] = parseTimeStamp # links the parse to the log file
        if not insertParse(sentence, treeLine, parseName, makePhraseElements=makePhraseElements, extraAttributes=extraAttributes):
            failCount += 1
    
    treeFile.close()
    # Remove work directory
    if not debug:
        shutil.rmtree(workdir)
    
    print >> sys.stderr, "Parsed", numCorpusSentences, "sentences (" + str(failCount) + " failed)"
    if failCount == 0:
        print >> sys.stderr, "All sentences were parsed succesfully"
    else:
        print >> sys.stderr, "Warning, parsing failed for", failCount, "out of", numCorpusSentences, "sentences"
        print >> sys.stderr, "The \"pennstring\" attribute of these sentences has an empty string."
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

def insertParses(input, parsePath, output=None, parseName="McCC", tokenizationName = None, makePhraseElements=True, extraAttributes={}):
    import tarfile
    from SentenceSplitter import openFile
    """
    Divide text in the "text" attributes of document and section 
    elements into sentence elements. These sentence elements are
    inserted into their respective parent elements.
    """  
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    print >> sys.stderr, "Inserting parses from", parsePath
    assert os.path.exists(parsePath)
    if parsePath.find(".tar.gz") != -1:
        tarFilePath, parsePath = parsePath.split(".tar.gz")
        tarFilePath += ".tar.gz"
        tarFile = tarfile.open(tarFilePath)
        if parsePath[0] == "/":
            parsePath = parsePath[1:]
    else:
        tarFile = None
    
    docCount = 0
    failCount = 0
    docsWithSentences = 0
    numCorpusSentences = 0
    sentencesCreated = 0
    sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
    counter = ProgressCounter(len(sourceElements), "McCC Parse Insertion")
    for document in sourceElements:
        docCount += 1
        origId = document.get("pmid")
        if origId == None:
            origId = document.get("origId")
        if origId == None:
            origId = document.get("id")
        origId = str(origId)
        counter.update(1, "Processing Documents ("+document.get("id")+"/" + origId + "): ")
        docId = document.get("id")
        if docId == None:
            docId = "CORPUS.d" + str(docCount)
        
        f = openFile(os.path.join(parsePath, origId + ".ptb"), tarFile)
        if f == None: # file with BioNLP'11 extension not found, try BioNLP'09 extension
            f = openFile(os.path.join(parsePath, origId + ".pstree"), tarFile)
            if f == None: # no parse found
                continue
        parseStrings = f.readlines()
        f.close()
        sentences = document.findall("sentence")
        numCorpusSentences += len(sentences)
        assert len(sentences) == len(parseStrings)
        # TODO: Following for-loop is the same as when used with a real parser, and should
        # be moved to its own function.
        for sentence, treeLine in zip(sentences, parseStrings):
            if not insertParse(sentence, treeLine, makePhraseElements=makePhraseElements, extraAttributes=extraAttributes, docId=origId):
                failCount += 1
    
    if tarFile != None:
        tarFile.close()
    #print >> sys.stderr, "Sentence splitting created", sentencesCreated, "sentences"
    #print >> sys.stderr, docsWithSentences, "/", docCount, "documents have sentences"

    print >> sys.stderr, "Inserted parses for", numCorpusSentences, "sentences (" + str(failCount) + " failed)"
    if failCount == 0:
        print >> sys.stderr, "All sentences have a parse"
    else:
        print >> sys.stderr, "Warning, a failed parse exists for", failCount, "out of", numCorpusSentences, "sentences"
        print >> sys.stderr, "The \"pennstring\" attribute of these sentences has an empty string."        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree
    
if __name__=="__main__":
    import sys
    
    from optparse import OptionParser, OptionGroup
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(description="BLLIP parser wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Name of tokenization element.")
    optparser.add_option("-s", "--stanford", default=False, action="store_true", dest="stanford", help="Run stanford conversion.")
    optparser.add_option("--timestamp", default=False, action="store_true", dest="timestamp", help="Mark parses with a timestamp.")
    optparser.add_option("--pathParser", default=None, dest="pathParser", help="")
    optparser.add_option("--pathBioModel", default=None, dest="pathBioModel", help="")
    group = OptionGroup(optparser, "Install Options", "")
    group.add_option("--install", default=None, action="store_true", dest="install", help="Install BANNER")
    group.add_option("--installDir", default=None, dest="installDir", help="Install directory")
    group.add_option("--downloadDir", default=None, dest="downloadDir", help="Install files download directory")
    group.add_option("--redownload", default=False, action="store_true", dest="redownload", help="Redownload install files")
    optparser.add_option_group(group)
    (options, args) = optparser.parse_args()
    
    if options.install:
        install(options.installDir, options.downloadDir, redownload=options.redownload)
    else:
        xml = parse(input=options.input, output=options.output, tokenizationName=options.tokenization, pathParser=options.pathParser, pathBioModel=options.pathBioModel, timestamp=options.timestamp)
        if options.stanford:
            import StanfordParser
            StanfordParser.convertXML(parser="McClosky", input=xml, output=options.output)
    