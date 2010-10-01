parse__version__ = "$Revision: 1.2 $"

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

def parse(input, output=None, tokenizationName="GeniaTagger-3.0.1", parseName="McClosky"):
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
            infile.write("<s> " + sentence.get("text") + " </s>\n")
    else: # Use existing tokenization
        for sentence in corpusRoot.getiterator("sentence"):
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
    for line in outfile:
        print line
    
    # Convert
    print >> sys.stderr, "Running Stanford conversion"
    StanfordParser.convert(os.path.join(workdir, "parser-output.txt"), os.path.join(workdir, "stanford-output.txt"))
    
    # Read Stanford results
    outfile = codecs.open(os.path.join(workdir, "stanford-output.txt"), "rt", "utf-8")
    print >> sys.stderr, "Inserting dependencies"
    # Add output to sentences
    for sentence in corpusRoot.getiterator("sentence"):
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
        parses.insert(prevParseIndex, parse)
        
        depCount = 0
        line = outfile.readline()
        while line.strip() != "":
            # Add tokens
            depType, rest = line.strip()[:-1].split("(")
            t1, t2 = rest.split(", ")
            t1Word, t1Index = t1.rsplit("-", 1)
            t1Index = int(t1Index)
            t2Word, t2Index = t2.rsplit("-", 1)
            t2Index = int(t2Index)
            # Make element
            dep = ET.Element("dependency")
            dep.set("id", "cjp_" + str(depCount))
            dep.set("t1", "clt_" + str(t1Index))
            dep.set("t2", "clt_" + str(t2Index))
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
    