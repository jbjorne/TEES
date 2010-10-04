parse__version__ = "$Revision: 1.3 $"

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

charniakJohnsonParserDir = "/home/jari/biotext/tools/reranking-parser"

def parse(input, output=None, tokenizationName=None, parseName="McClosky", requireEntities=False):
    global charniakJohnsonParserDir
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    infile = codecs.open(os.path.join(workdir, "parser-input.txt"), "wt", "utf-8")
    if tokenizationName == None: # Parser does tokenization
        for sentence in corpusRoot.getiterator("sentence"):
            if requireEntities:
                if sentence.find("entity") == None:
                    continue
            infile.write("<s> " + sentence.get("text") + " </s>\n")
    else: # Use existing tokenization
        for sentence in corpusRoot.getiterator("sentence"):
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
    infile.close()
    
    # Run parser
    print >> sys.stderr, "Running parser", charniakJohnsonParserDir + "/parse.sh"
    cwd = os.getcwd()
    os.chdir(charniakJohnsonParserDir)
    args = [charniakJohnsonParserDir + "/parse.sh"]
    subprocess.call(args, 
        stdin=codecs.open(os.path.join(workdir, "parser-input.txt"), "rt", "utf-8"),
        stdout=codecs.open(os.path.join(workdir, "parser-output.txt"), "wt", "utf-8"))
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
    print >> sys.stderr, "Inserting dependencies"
    # Add output to sentences
    for sentence in corpusRoot.getiterator("sentence"):
        if requireEntities:
            if sentence.find("entity") == None:
                continue
        
        # Find or create container elements
        sentenceAnalyses = sentence.find("sentenceAnalyses")
        if sentenceAnalyses == None:
            sentenceAnalyses = ET.Element("sentenceAnalyses")
            sentence.append(sentenceAnalyses)
        parses = sentenceAnalyses.find("parses")
        if parses == None:
            parses = ET.Element("parses")
            sentenceAnalyses.append(parses)
        prevParseIndex = 0
        for prevParse in parses.findall("parse"):
            assert prevParse.get("parser") != parseName
            prevParseIndex += 1
        parse = ET.Element("parse")
        parse.set("parse", parseName)
        if tokenizationName == None:
            parse.set("tokenizer", parseName)
        else:
            parse.set("tokenizer", tokenizationName)
        parses.insert(prevParseIndex, parse)
        
        # Parser-generated tokens
        if tokenizationName == None:
            tokenizations = sentenceAnalyses.find("tokenizations")
            if tokenizations == None:
                tokenizations = ET.Element("tokenizations")
                sentenceAnalyses.append(tokenizations)
            prevTokenizationIndex = 0
            for prevTokenization in tokenizations.findall("tokenization"):
                assert prevTokenization.get("tokenizer") != tokenizationName
                prevTokenizationIndex += 1
            tokenization = ET.Element("tokenization")
            tokenization.set("tokenizer", parseName)
            tokenizations.insert(prevTokenizationIndex, tokenization)
        
            treeLine = treeFile.readline()
            if treeLine.strip() != "":
                # Add tokens
                prevSplit = None
                tokens = []
                posTags = []
                for split in treeLine.split():
                    if split[0] != "(":
                        tokenText = split
                        while tokenText[-1] == ")":
                            tokenText = tokenText[:-1]
                        if tokenText == "-LRB-":
                            tokenText = "("
                        elif tokenText == "-RRB-":
                            tokenText = ")"
                        tokens.append(tokenText)
                        
                        posText = prevSplit
                        while posText[0] == "(":
                            posText = posText[1:]
                        if posText == "-LRB-":
                            posText = "("
                        elif posText == "-RRB-":
                            posText = ")"
                        posTags.append(posText)
                    prevSplit = split
                
                tokenCount = 0
                start = 0
                for tokenText in tokens:
                    sText = sentence.get("text")
                    # Determine offsets
                    cStart = sText.find(tokenText, start)
                    assert cStart != -1, (tokenText, tokens, posTags, treeLine, start, sText)
                    cEnd = cStart + len(tokenText)
                    start = cStart + len(tokenText)
                    # Make element
                    token = ET.Element("token")
                    token.set("id", "cjt_" + str(tokenCount + 1))
                    token.set("text", tokenText)
                    token.set("POS", posTags[tokenCount])
                    token.set("charOffset", str(cStart) + "-" + str(cEnd - 1)) # NOTE: check
                    tokenization.append(token)
                    tokenCount += 1
        
        depCount = 0
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
            dep.set("t1", "cjt_" + str(t1Index))
            dep.set("t2", "cjt_" + str(t2Index))
            dep.set("type", depType)
            parse.append(dep)
            depCount += 1            
            line = outfile.readline()
    
    outfile.close()
    # Remove work directory
    shutil.rmtree(workdir)
        
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
    (options, args) = optparser.parse_args()
    
    parse(input=options.input, output=options.output)
    