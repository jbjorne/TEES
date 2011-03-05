parse__version__ = "$Revision: 1.10 $"

import sys,os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import StanfordParser

import shutil
import subprocess
import tempfile
import codecs
from ProcessUtils import *

charniakJohnsonParserDir = "/home/jari/biotext/tools/reranking-parser"

escDict={"-LRB-":"(",
         "-RRB-":")",
         "-LCB-":"{",
         "-RCB-":"}",
         "-LSB-":"[",
         "-RSB-":"]",
         "``":"\"",
         "''":"\""}

#def makeInitScript():
#    pass
#
#def launchProcesses():
#    pass
#
#def runMurska(cscConnection):
#    cscConnection.upload(textFileName, textFileName, False)
#    cscConnection.run("split -l 50 " + textFileName + " " + textFileName + "-part", True)
#    
#    cscConnection.run("cat " + textFileName + "-part* > cj-output.txt", True)
            
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

def insertTokens(tokens, sentence, tokenization, idStem="cjt_"):
    tokenCount = 0
    start = 0
    for tokenText, posTag, origTokenText in tokens:
        sText = sentence.get("text")
        # Determine offsets
        cStart = sText.find(tokenText, start)
        #assert cStart != -1, (tokenText, tokens, posTag, start, sText)
        if cStart == -1: # Try again with original text (sometimes escaping can remove correct text)
            cStart = sText.find(origTokenText, start)
        if cStart == -1:
            print >> sys.stderr, "Token alignment error", (tokenText, tokens, posTag, start, sText)
            for subElement in [x for x in tokenization]:
                tokenization.remove(subElement)
            return False
        cEnd = cStart + len(tokenText)
        start = cStart + len(tokenText)
        # Make element
        token = ET.Element("token")
        token.set("id", idStem + str(tokenCount + 1))
        token.set("text", tokenText)
        token.set("POS", posTag)
        token.set("charOffset", str(cStart) + "-" + str(cEnd - 1)) # NOTE: check
        tokenization.append(token)
        tokenCount += 1
    return True

def insertPhrases(phrases, parse, tokenElements, idStem="cjp_"):
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

def insertParse(sentence, treeLine, parseName="mccc-preparsed", tokenizationName = None):
    # Find or create container elements
    sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
    tokenizations = setDefaultElement(sentenceAnalyses, "tokenizations")
    parses = setDefaultElement(sentenceAnalyses, "parses")
    prevParseIndex = 0
    for prevParse in parses.findall("parse"):
        assert prevParse.get("parser") != parseName
        prevParseIndex += 1
    parse = ET.Element("parse")
    parse.set("parser", parseName)
    if tokenizationName == None:
        parse.set("tokenizer", parseName)
    else:
        parse.set("tokenizer", tokenizationName)
    parses.insert(prevParseIndex, parse)
    
    tokenByIndex = {}
    parse.set("pennstring", treeLine.strip())
    if treeLine.strip() == "":
        return False
    else:
        tokens, phrases = readPenn(treeLine)
        # Get tokenization
        if tokenizationName == None: # Parser-generated tokens
            prevTokenizationIndex = 0
            for prevTokenization in tokenizations.findall("tokenization"):
                assert prevTokenization.get("tokenizer") != tokenizationName
                prevTokenizationIndex += 1
            tokenization = ET.Element("tokenization")
            tokenization.set("tokenizer", parseName)
            tokenizations.insert(prevTokenizationIndex, tokenization)
            # Insert tokens to parse
            insertTokens(tokens, sentence, tokenization)
        else:
            tokenization = getElementByAttrib(tokenizations, "tokenization", {"tokenizer":tokenizationName})
        # Insert phrases to parse
        insertPhrases(phrases, parse, tokenization.findall("token"))
    return True           

def runCharniakJohnsonParserWithTokenizer(input, output):
    return runCharniakJohnsonParser(input, output, True)

def runCharniakJohnsonParserWithoutTokenizer(input, output):
    return runCharniakJohnsonParser(input, output, False)
        
def runCharniakJohnsonParser(input, output, tokenizer=False):
    if tokenizer:
        print >> sys.stderr, "Running CJ-parser with tokenization"
    else:
        print >> sys.stderr, "Running CJ-parser without tokenization"
    #args = ["./parse-50best-McClosky.sh"]
    #return subprocess.Popen(args, 
    #    stdin=codecs.open(input, "rt", "utf-8"),
    #    stdout=codecs.open(output, "wt", "utf-8"), shell=True)
    
    if tokenizer:
        firstStageArgs = ["first-stage/PARSE/parseIt", "-l999", "-N50" , "../McClosky-biomodel/parser/"]
    else:
        firstStageArgs = ["first-stage/PARSE/parseIt", "-l999", "-N50" , "-K", "../McClosky-biomodel/parser/"]
    secondStageArgs = ["second-stage/programs/features/best-parses", "-l", "../McClosky-biomodel/reranker/features.gz", "../McClosky-biomodel/reranker/weights.gz"]
    
    firstStage = subprocess.Popen(firstStageArgs,
                                  stdin=codecs.open(input, "rt", "utf-8"),
                                  stdout=subprocess.PIPE)
    secondStage = subprocess.Popen(secondStageArgs,
                                   stdin=firstStage.stdout,
                                   stdout=codecs.open(output, "wt", "utf-8"))
    return ProcessWrapper([firstStage, secondStage])

def parse(input, output=None, tokenizationName=None, parseName="McClosky", requireEntities=False, skipIds=[], skipParsed=True):
    global charniakJohnsonParserDir, escDict
    print >> sys.stderr, "Charniak-Johnson Parser"
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    infileName = os.path.join(workdir, "parser-input.txt")
    infile = codecs.open(infileName, "wt", "utf-8")
    numCorpusSentences = 0
    if tokenizationName == None: # Parser does tokenization
        print >> sys.stderr, "Parser does the tokenization"
        for sentence in corpusRoot.getiterator("sentence"):
            if sentence.get("id") in skipIds:
                print >> sys.stderr, "Skipping sentence", sentence.get("id")
                continue
            if requireEntities:
                if sentence.find("entity") == None:
                    continue
            if skipParsed:
                if ETUtils.getElementByAttrib(sentence, "parse", {"parser":"McClosky"}) != None:
                    continue
            infile.write("<s> " + sentence.get("text") + " </s>\n")
            numCorpusSentences += 1
    else: # Use existing tokenization
        print >> sys.stderr, "Using existing tokenization", tokenizationName 
        for sentence in corpusRoot.getiterator("sentence"):
            if sentence.get("id") in skipIds:
                print >> sys.stderr, "Skipping sentence", sentence.get("id")
                continue
            if requireEntities:
                if sentence.find("entity") == None:
                    continue
            for tokenization in sentence.find("sentenceanalyses").find("tokenizations"):
                if tokenization.get("tokenizer") == tokenizationName:
                    break
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
    #print >> sys.stderr, "Running parser", charniakJohnsonParserDir + "/parse.sh"
    cwd = os.getcwd()
    os.chdir(charniakJohnsonParserDir)
    if tokenizationName == None:
        charniakOutput = runSentenceProcess(runCharniakJohnsonParserWithTokenizer, charniakJohnsonParserDir, infileName, workdir, False, "CharniakJohnsonParser", "Parsing", timeout=600)   
    else:
        charniakOutput = runSentenceProcess(runCharniakJohnsonParserWithoutTokenizer, charniakJohnsonParserDir, infileName, workdir, False, "CharniakJohnsonParser", "Parsing", timeout=600)   
#    args = [charniakJohnsonParserDir + "/parse-50best-McClosky.sh"]
#    #bioParsingModel = charniakJohnsonParserDir + "/first-stage/DATA-McClosky"
#    #args = charniakJohnsonParserDir + "/first-stage/PARSE/parseIt -K -l399 -N50 " + bioParsingModel + "/parser | " + charniakJohnsonParserDir + "/second-stage/programs/features/best-parses -l " + bioParsingModel + "/reranker/features.gz " + bioParsingModel + "/reranker/weights.gz"
    os.chdir(cwd)
    
    treeFile = codecs.open(charniakOutput, "rt", "utf-8")
    print >> sys.stderr, "Inserting parses"
    # Add output to sentences
    failCount = 0
    for sentence in corpusRoot.getiterator("sentence"):
        if sentence.get("id") in skipIds:
            print >> sys.stderr, "Skipping sentence", sentence.get("id")
            continue
        if requireEntities:
            if sentence.find("entity") == None:
                continue
        if skipParsed:
            if ETUtils.getElementByAttrib(sentence, "parse", {"parser":"McClosky"}) != None:
                continue
        
        treeLine = treeFile.readline()
        if not insertParse(sentence, treeLine, parseName):
            failCount += 1
#        # Find or create container elements
#        sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
#        tokenizations = setDefaultElement(sentenceAnalyses, "tokenizations")
#        parses = setDefaultElement(sentenceAnalyses, "parses")
#        prevParseIndex = 0
#        for prevParse in parses.findall("parse"):
#            assert prevParse.get("parser") != parseName
#            prevParseIndex += 1
#        parse = ET.Element("parse")
#        parse.set("parser", parseName)
#        if tokenizationName == None:
#            parse.set("tokenizer", parseName)
#        else:
#            parse.set("tokenizer", tokenizationName)
#        parses.insert(prevParseIndex, parse)
#        
#        tokenByIndex = {}
#        parse.set("pennstring", treeLine.strip())
#        if treeLine.strip() == "":
#            failCount += 1
#        else:
#            tokens, phrases = readPenn(treeLine)
#            # Get tokenization
#            if tokenizationName == None: # Parser-generated tokens
#                prevTokenizationIndex = 0
#                for prevTokenization in tokenizations.findall("tokenization"):
#                    assert prevTokenization.get("tokenizer") != tokenizationName
#                    prevTokenizationIndex += 1
#                tokenization = ET.Element("tokenization")
#                tokenization.set("tokenizer", parseName)
#                tokenizations.insert(prevTokenizationIndex, tokenization)
#                # Insert tokens to parse
#                insertTokens(tokens, sentence, tokenization)
#            else:
#                tokenization = getElementByAttrib(tokenizations, "tokenization", {"tokenizer":tokenizationName})
#            # Insert phrases to parse
#            insertPhrases(phrases, parse, tokenization.findall("token"))
    
    treeFile.close()
    # Remove work directory
    #shutil.rmtree(workdir)
    
    if failCount == 0:
        print >> sys.stderr, "Parsed succesfully all sentences"
    else:
        print >> sys.stderr, "Warning, parsing failed for", failCount, "out of", numCorpusSentences, "sentences"
        print >> sys.stderr, "The \"pennstring\" attribute of these sentences has an empty string."
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

def insertParses(input, parsePath, output=None, parseName="mccc-preparsed", tokenizationName = None):
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
    if parsePath.find(".tar.gz") != -1:
        tarFilePath, parsePath = parsePath.split(".tar.gz")
        tarFilePath += ".tar.gz"
        tarFile = tarfile.open(tarFilePath)
        if parsePath[0] == "/":
            parsePath = parsePath[1:]
    else:
        tarFile = None
    
    docCount = 0
    docsWithSentences = 0
    sentencesCreated = 0
    sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
    counter = ProgressCounter(len(sourceElements), "McCC Parse Insertion")
    for document in sourceElements:
        docCount += 1
        counter.update(1, "Processing Documents ("+document.get("id")+"/" + document.get("pmid") + "): ")
        docId = document.get("id")
        if docId == None:
            docId = "CORPUS.d" + str(docCount)
        
        f = openFile(os.path.join(parsePath, document.get("pmid") + ".ptb"), tarFile)
        if f == None:
            continue
        parseStrings = f.readlines()
        f.close()
        sentences = document.findall("sentence")
        assert len(sentences) == len(parseStrings)
        # TODO: Following for-loop is the same as when used with a real parser, and should
        # be moved to its own function.
        for sentence, treeLine in zip(sentences, parseStrings):
            if not insertParse(sentence, treeLine):
                failCount += 1
    
    if tarFile != None:
        tarFile.close()
    #print >> sys.stderr, "Sentence splitting created", sentencesCreated, "sentences"
    #print >> sys.stderr, docsWithSentences, "/", docCount, "documents have sentences"
        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree
    
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
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Name of tokenization element.")
    optparser.add_option("-s", "--stanford", default=False, action="store_true", dest="stanford", help="Run stanford conversion.")
    (options, args) = optparser.parse_args()
    
    xml = parse(input=options.input, output=options.output, tokenizationName=options.tokenization)
    if options.stanford:
        import StanfordParser
        StanfordParser.convertXML(parser="McClosky", input=xml, output=options.output)
    