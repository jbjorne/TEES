import sys, os
import shutil
import subprocess
import tempfile
import codecs
from ProcessUtils import *
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

stanfordParserDir = "/home/jari/biotext/tools/stanford-parser-2010-08-20"

escDict={"-LRB-":"(",
         "-RRB-":")",
         "-LCB-":"{",
         "-RCB-":"}",
         "-LSB-":"[",
         "-RSB-":"]",
         "``":"\"",
         "''":"\""}

def runStanford(input, output):
    args = ["java", "-mx150m", "-cp", "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", "-CCprocessed", "-treeFile", input] 
    return subprocess.Popen(args, stdout=codecs.open(output, "wt", "utf-8"))

def addDependencies(outfile, parse, tokenByIndex=None, sentenceId=None):
    global escDict
    escSymbols = sorted(escDict.keys())
    
    depCount = 1
    line = outfile.readline()
    deps = []
    while line.strip() != "":            
        # Add dependencies
        depType, rest = line.strip()[:-1].split("(")
        t1, t2 = rest.split(", ")
        t1Word, t1Index = t1.rsplit("-", 1)
        for escSymbol in escSymbols:
            t1Word = t1Word.replace(escSymbol, escDict[escSymbol])
        while not t1Index[-1].isdigit(): t1Index = t1Index[:-1] # invalid literal for int() with base 10: "7'"
        t1Index = int(t1Index)
        t2Word, t2Index = t2.rsplit("-", 1)
        for escSymbol in escSymbols:
            t2Word = t2Word.replace(escSymbol, escDict[escSymbol])
        while not t2Index[-1].isdigit(): t2Index = t2Index[:-1] # invalid literal for int() with base 10: "7'"
        t2Index = int(t2Index)
        # Make element
        dep = ET.Element("dependency")
        dep.set("id", "cjp_" + str(depCount))
        if tokenByIndex != None:
            assert t1Word == tokenByIndex[t1Index-1].get("text"), (t1Word, tokenByIndex[t1Index-1].get("text"), t1Index-1, depCount, sentenceId)
            assert t2Word == tokenByIndex[t2Index-1].get("text"), (t2Word, tokenByIndex[t2Index-1].get("text"), t2Index-1, depCount, sentenceId)
            dep.set("t1", tokenByIndex[t1Index-1].get("id"))
            dep.set("t2", tokenByIndex[t2Index-1].get("id"))
        else:
            dep.set("t1", "cjt_" + str(t1Index))
            dep.set("t2", "cjt_" + str(t2Index))
        dep.set("type", depType)
        parse.append(dep)
        depCount += 1
        deps.append(dep)
        line = outfile.readline()
    return deps

def convert(input, output=None):
    global stanfordParserDir

    workdir = tempfile.mkdtemp()
    if output == None:
        output = os.path.join(workdir, "stanford-output.txt")
    
    input = os.path.abspath(input)
    numCorpusSentences = 0
    inputFile = codecs.open(input, "rt", "utf-8")
    for line in inputFile:
        numCorpusSentences += 1
    inputFile.close()
    cwd = os.getcwd()
    os.chdir(stanfordParserDir)
    args = ["java", "-mx150m", "-cp", "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", "-CCprocessed", "-treeFile", input] 
    #subprocess.call(args,
    process = subprocess.Popen(args, 
        stdout=codecs.open(output, "wt", "utf-8"))
    waitForProcess(process, numCorpusSentences, True, output, "StanfordParser", "Stanford Conversion")
    os.chdir(cwd)

    lines = None    
    if output == None:
        outFile = codecs.open(output, "rt", "utf-8")
        lines = outFile.readlines()
        outFile.close()
    
    shutil.rmtree(workdir)
    return lines

def convertXML(parser, input, output):
    global stanfordParserDir
    print >> sys.stderr, "Running Stanford conversion"
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    workdir = tempfile.mkdtemp()
    stanfordInput = os.path.join(workdir, "input")
    stanfordInputFile = codecs.open(stanfordInput, "wt", "utf-8")
    
    # Put penn tree lines in input file
    for sentence in corpusRoot.getiterator("sentence"):
        sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
        parses = setDefaultElement(sentenceAnalyses, "parses")
        parse = getElementByAttrib(parses, "parse", {"parser":parser})
        if parse == None:
            continue
        pennTree = parse.get("pennstring")
        if pennTree == None or pennTree == "":
            continue
        stanfordInputFile.write(pennTree + "\n")
    stanfordInputFile.close()
    
    # Run Stanford parser
    stanfordOutput = runSentenceProcess(runStanford, stanfordParserDir, stanfordInput, workdir, True, "StanfordParser", "Stanford Conversion", timeout=600)   
    stanfordOutputFile = codecs.open(stanfordOutput, "rt", "utf-8")
    
    # Get output and insert dependencies
    for sentence in corpusRoot.getiterator("sentence"):
        # Get parse
        sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
        parses = setDefaultElement(sentenceAnalyses, "parses")
        parse = getElementByAttrib(parses, "parse", {"parser":parser})
        if parse == None:
            parse = ET.SubElement(parses, "parse")
            parse.set("parser", "None")
        pennTree = parse.get("pennstring")
        if pennTree == None or pennTree == "":
            parse.set("stanford", "no_penn")
            continue
        # Get tokens
        tokenization = getElementByAttrib(sentence.find("sentenceanalyses").find("tokenizations"), "tokenization", {"tokenizer":parse.get("tokenizer")})
        assert tokenization != None
        count = 0
        tokenByIndex = {}
        for token in tokenization.findall("token"):
            tokenByIndex[count] = token
            count += 1
        # Insert dependencies
        deps = addDependencies(stanfordOutputFile, parse, tokenByIndex, sentence.get("id"))
        if len(deps) == 0:
            parse.set("stanford", "no_dependencies")
        else:
            parse.set("stanford", "ok")
    stanfordOutputFile.close()
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
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Name of parse element.")
    (options, args) = optparser.parse_args()
    
    convertXML(input=options.input, output=options.output, parser=options.parse)
        