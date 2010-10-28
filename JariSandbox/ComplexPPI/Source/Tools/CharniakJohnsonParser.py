parse__version__ = "$Revision: 1.4 $"

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
         "-RSB-":"]"}

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

def setDefaultElement(parent, name):
    element = parent.find(name)
    if element == None:
        element = ET.Element(name)
        parent.append(element)
    return element
            
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
                for escSymbol in escSymbols:
                    tokenText = tokenText.replace(escSymbol, escDict[escSymbol])
                
                posText = prevSplit
                while posText[0] == "(":
                    posText = posText[1:]
                for escSymbol in escSymbols:
                    posText = posText.replace(escSymbol, escDict[escSymbol])
                tokens.append( (tokenText, posText) )
                tokenCount += 1
            elif splits[splitCount + 1][0] == "(":
                stack.append( (tokenCount, split[1:]) )
            prevSplit = split
            splitCount += 1
    return tokens, phrases

def insertTokens(tokens, tokenization, idStem="cjt_"):
    tokenCount = 0
    start = 0
    for tokenText, posTag in tokens:
        sText = sentence.get("text")
        # Determine offsets
        cStart = sText.find(tokenText, start)
        assert cStart != -1, (tokenText, tokens, posTags, treeLine, start, sText)
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

def insertPhrases(phrases, parse, tokenElements, idStem="cjp_"):
    count = 0
    phrases.sort()
    for phrase in phrases:
        phraseElement = ET.Element("phrase")
        phraseElement.set("type", phrase[2])
        phraseElement.set("id", idStem + str(count))
        phraseElement.set("begin", str(phrase[0]))
        phraseElement.set("end", str(phrase[1]))
        t1 = tokenElements[phrase[0]]
        t2 = tokenElements[phrase[1]]
        phraseElement.set("charOffset", t1.get("charOffset").split("-")[0] + "-" + t2.get("charOffset").split("-")[-1])
        parse.append(phraseElement)
        count += 1

def parse(input, output=None, tokenizationName=None, parseName="McClosky", requireEntities=False, skipIds=[]):
    global charniakJohnsonParserDir, escDict
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    infile = codecs.open(os.path.join(workdir, "parser-input.txt"), "wt", "utf-8")
    numCorpusSentences = 0
    if tokenizationName == None: # Parser does tokenization
        print >> sys.stderr, "Parser does the tokenization (Doesn't work ATM)"
        for sentence in corpusRoot.getiterator("sentence"):
            if sentence.get("id") in skipIds:
                print >> sys.stderr, "Skipping sentence", sentence.get("id")
                continue
            if requireEntities:
                if sentence.find("entity") == None:
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
            for tokenization in sentence.find("sentenceAnalyses").find("tokenizations"):
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
    print >> sys.stderr, "Running parser", charniakJohnsonParserDir + "/parse.sh"
    cwd = os.getcwd()
    os.chdir(charniakJohnsonParserDir)
    args = [charniakJohnsonParserDir + "/parse-50best-McClosky.sh"]
    #bioParsingModel = charniakJohnsonParserDir + "/first-stage/DATA-McClosky"
    #args = charniakJohnsonParserDir + "/first-stage/PARSE/parseIt -K -l399 -N50 " + bioParsingModel + "/parser | " + charniakJohnsonParserDir + "/second-stage/programs/features/best-parses -l " + bioParsingModel + "/reranker/features.gz " + bioParsingModel + "/reranker/weights.gz"
    #subprocess.call(args,
    process = subprocess.Popen(args, 
        stdin=codecs.open(os.path.join(workdir, "parser-input.txt"), "rt", "utf-8"),
        stdout=codecs.open(os.path.join(workdir, "parser-output.txt"), "wt", "utf-8"))
    waitForProcess(process, numCorpusSentences, False, os.path.join(workdir, "parser-output.txt"), "CharniakJohnsonParser", "Parsing Sentences")
    os.chdir(cwd)
    
    # Read parse
    outfile = codecs.open(os.path.join(workdir, "parser-output.txt"), "rt", "utf-8")
    #for line in outfile:
    #    print line
    
    # Convert
    print >> sys.stderr, "Running Stanford conversion"
    StanfordParser.convert(os.path.join(workdir, "parser-output.txt"), os.path.join(workdir, "stanford-output.txt"))
    
    # Read Stanford results
    outfile = codecs.open(os.path.join(workdir, "stanford-output.txt"), "rt", "utf-8")
    treeFile = codecs.open(os.path.join(workdir, "parser-output.txt"), "rt", "utf-8")
    print >> sys.stderr, "Inserting parses"
    # Add output to sentences
    for sentence in corpusRoot.getiterator("sentence"):
        if sentence.get("id") in skipIds:
            print >> sys.stderr, "Skipping sentence", sentence.get("id")
            continue
        if requireEntities:
            if sentence.find("entity") == None:
                continue
        
        # Find or create container elements
        sentenceAnalyses = setDefaultElement(sentence, "sentenceAnalyses")
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
        treeLine = treeFile.readline()
        parse.set("pennstring", treeLine.strip())
        tokens, phrases = readPenn(treeLine)
        # Parser-generated tokens
        if tokenizationName == None:
            prevTokenizationIndex = 0
            for prevTokenization in tokenizations.findall("tokenization"):
                assert prevTokenization.get("tokenizer") != tokenizationName
                prevTokenizationIndex += 1
            tokenization = ET.Element("tokenization")
            tokenization.set("tokenizer", parseName)
            tokenizations.insert(prevTokenizationIndex, tokenization)
            insertTokens(tokens, tokenization)
        else:
            for tokenization in tokenizations:
                if tokenization.get("tokenizer") == tokenizationName:
                    break
            assert tokenization.get("tokenizer") == tokenizationName
            count = 0
            for token in tokenization.findall("token"):
                tokenByIndex[count] = token
                count += 1
            
        depCount = 1
        line = outfile.readline()
        while line.strip() != "":            
            # Add dependencies
            depType, rest = line.strip()[:-1].split("(")
            t1, t2 = rest.split(", ")
            t1Word, t1Index = t1.rsplit("-", 1)
            while not t1Index[-1].isdigit(): t1Index = t1Index[:-1] # invalid literal for int() with base 10: "7'"
            t1Index = int(t1Index)
            t2Word, t2Index = t2.rsplit("-", 1)
            while not t2Index[-1].isdigit(): t2Index = t2Index[:-1] # invalid literal for int() with base 10: "7'"
            t2Index = int(t2Index)
            # Make element
            dep = ET.Element("dependency")
            dep.set("id", "cjp_" + str(depCount))
            if tokenizationName != None:
                dep.set("t1", tokenByIndex[t1Index-1].get("id"))
                dep.set("t2", tokenByIndex[t2Index-1].get("id"))
            else:
                dep.set("t1", "cjt_" + str(t1Index))
                dep.set("t2", "cjt_" + str(t2Index))
            dep.set("type", depType)
            parse.append(dep)
            depCount += 1            
            line = outfile.readline()

        insertPhrases(phrases, parse, tokenization.findall("token"))
    
    outfile.close()
    # Remove work directory
    #shutil.rmtree(workdir)
        
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
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    parse(input=options.input, output=options.output, tokenizationName=options.tokenization)
    