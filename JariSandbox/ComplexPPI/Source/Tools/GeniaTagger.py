__version__ = "$Revision: 1.3 $"

import sys,os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

import shutil
import subprocess
import tempfile
import codecs
import time

from ProcessUtils import *
"""
A wrapper for the Joachims SVM Multiclass classifier.
"""

geniaTaggerDir = "/home/jari/biotext/tools/geniatagger-3.0.1"

def tokenize(input, output=None, tokenizationName="GeniaTagger-3.0.1", extraFields=["base", "chunk", "NE"]):
    global geniaTaggerDir
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    infile = codecs.open(os.path.join(workdir, "tagger-input.txt"), "wt", "utf-8")
    numCorpusSentences = 0
    for sentence in corpusRoot.getiterator("sentence"):
        infile.write(sentence.get("text") + "\n")
        numCorpusSentences += 1
    infile.close()
    
    # Run tagger
    cwd = os.getcwd()
    os.chdir(geniaTaggerDir)
    args = [geniaTaggerDir + "/geniatagger"]
    #args += [ "<", os.path.join(workdir, "tagger-input.txt")]
    #args += [ ">", os.path.join(workdir, "tagger-output.txt")]
    #subprocess.call(args,
    process = subprocess.Popen(args, 
        stdin=codecs.open(os.path.join(workdir, "tagger-input.txt"), "rt", "utf-8"),
        stdout=codecs.open(os.path.join(workdir, "tagger-output.txt"), "wt", "utf-8"))
    waitForProcess(process, numCorpusSentences, True, os.path.join(workdir, "tagger-output.txt"), "GeniaTagger", "Tokenizing Sentences")
    os.chdir(cwd)
    
    # Read tokenization
    outfile = codecs.open(os.path.join(workdir, "tagger-output.txt"), "rt", "utf-8")
    # Add output to sentences
    for sentence in corpusRoot.getiterator("sentence"):
        # Find or create container elements
        sentenceAnalyses = sentence.find("sentenceAnalyses")
        if sentenceAnalyses == None:
            sentenceAnalyses = ET.Element("sentenceAnalyses")
            sentence.append(sentenceAnalyses)
        tokenizations = sentenceAnalyses.find("tokenizations")
        if tokenizations == None:
            tokenizations = ET.Element("tokenizations")
            sentenceAnalyses.append(tokenizations)
        prevTokenizationIndex = 0
        for prevTokenization in tokenizations.findall("tokenization"):
            assert prevTokenization.get("tokenizer") != tokenizationName
            prevTokenizationIndex += 1
        tokenization = ET.Element("tokenization")
        tokenization.set("tokenizer", tokenizationName)
        tokenizations.insert(prevTokenizationIndex, tokenization)
        
        sText = sentence.get("text")
        start = 0
        tokenCount = 0
        line = outfile.readline()
        while line.strip() != "":
            # Add tokens
            splits = line.strip().split("\t")
            # Determine offsets
            cStart = sText.find(splits[0], start)
            if cStart == -1:
                if splits[0] == "``":
                    splits[0] = "\""
                if splits[0] == "''":
                    splits[0] = "\""           
                cStart = sText.find(splits[0], start)
            assert cStart != -1, (sentence.get("id"), sText, line, tokenCount)
            cEnd = cStart + len(splits[0])
            start = cStart + len(splits[0])
            # Make element
            token = ET.Element("token")
            token.set("id", "gt_" + str(tokenCount+1))
            token.set("text", splits[0])
            if "base" in extraFields:
                token.set("base", splits[1])
            token.set("POS", splits[2])
            if "chunk" in extraFields:
                token.set("chunk", splits[3])
            if "NE" in extraFields:
                token.set("NE", splits[4])
            token.set("charOffset", str(cStart) + "-" + str(cEnd - 1)) # NOTE: check
            tokenization.append(token)
            tokenCount += 1
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
    
    tokenize(input=options.input, output=options.output)
    