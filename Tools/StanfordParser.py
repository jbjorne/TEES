import sys, os
import shutil
import subprocess
import tempfile
import tarfile
import codecs
from ProcessUtils import *
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
import Utils.ElementTreeUtils as ETUtils
import Utils.Settings as Settings
import Utils.Download as Download
import Utils.Settings as Settings
import Tool
#stanfordParserDir = "/home/jari/biotext/tools/stanford-parser-2010-08-20"
#stanfordParserDir = "/home/jari/temp_exec/stanford-parser-2010-08-20"
#stanfordParserDir = Settings.STANFORD_PARSER_DIR
#stanfordParserArgs = ["java", "-mx150m", "-cp", 
#    "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
#    "-CCprocessed", "-treeFile", "-keepPunct"]
#stanfordParserArgs = ["java", "-mx500m", "-cp", 
#    "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
#    "-CCprocessed", "-keepPunct", "-treeFile"]

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
    print >> sys.stderr, "Installing Stanford Parser"
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH, "tools/download/")
    if destDir == None:
        destDir = os.path.join(Settings.DATAPATH, "tools/")
    items = Download.downloadAndExtract(Settings.URL["STANFORD_PARSER"], destDir, downloadDir)
    stanfordPath = Download.getTopDir(destDir, items)
    Tool.finalizeInstall(["stanford-parser.jar"], 
                         {"stanford-parser.jar":"java -cp stanford-parser.jar edu.stanford.nlp.trees.EnglishGrammaticalStructure"},
                         stanfordPath, {"STANFORD_PARSER_DIR":stanfordPath}, updateLocalSettings)


#    url = URL["STANFORD_PARSER"]
#    packageName = url.split("/")[-1].split(".")[0]
#    # Download
#    if downloadDir == None:
#        downloadDir = os.path.join(Settings.DATAPATH, "tools/download/")
#    downloadFile = Download.download(url, downloadDir, clear=redownload)
#    # Prepare destination
#    if destDir == None:
#        destDir = os.path.join(Settings.DATAPATH, "tools/")
#    installDir =  os.path.join(destDir, packageName)
#    if os.path.exists(installDir):
#        print >> sys.stderr, "Removing existing installation at", installDir
#        shutil.rmtree(installDir)
#    # Unpack
#    print >> sys.stderr, "Extracting", downloadFile, "to", destDir
#    f = tarfile.open(downloadFile, 'r:gz')
#    f.extractall(destDir)
#    f.close()
#    
#    if test(destDir):
#        Settings.setLocal("STANFORD_PARSER_DIR", destDir, updateLocalSettings)

def runStanford(input, output, stanfordParserArgs):
    #global stanfordParserArgs
    ##args = ["java", "-mx150m", "-cp", "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", "-CCprocessed", "-treeFile", input]
    #args = ["java", "-mx500m", "-cp", "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", "-CCprocessed", "-treeFile", input] 
    #return subprocess.Popen(args, stdout=codecs.open(output, "wt", "utf-8"))
    return subprocess.Popen(stanfordParserArgs + [input], stdout=codecs.open(output, "wt", "utf-8"))
    #return subprocess.Popen(stanfordParserArgs + [input], stdout=codecs.open(output, "wt", "latin1", "replace"))

def getUnicode(string):
    try:
        string = string.encode('raw_unicode_escape').decode('utf-8') # fix latin1?
    except:
        pass
    return string

def addDependencies(outfile, parse, tokenByIndex=None, sentenceId=None, skipExtra=0):
    global escDict
    escSymbols = sorted(escDict.keys())
    
    # A list of tokens for debugging
    tokens = []
    for key in sorted(tokenByIndex):
        tokens.append(tokenByIndex[key].get("text"))

    depCount = 1
    line = outfile.readline()
    #line = line.encode('raw_unicode_escape').decode('utf-8') # fix latin1?
    line = getUnicode(line)
    deps = []
    # BioNLP'09 Shared Task GENIA uses _two_ newlines to denote a failed parse (usually it's one,
    # the same as the BLLIP parser. To survive this, skipExtra can be used to define the number
    # of lines to skip, if the first line of a dependency parse is empty (indicating a failed parse) 
    if line.strip() == "" and skipExtra > 0:
        for i in range(skipExtra):
            outfile.readline()
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
        #if depType == "root":
        #    assert t1Word == "ROOT"
        #    if tokenByIndex != None and t2Index-1 in tokenByIndex:
        #        tokenByIndex[t2Index-1].set("stanford-root", "True")
        if depType != "root":
            dep = ET.Element("dependency")
            dep.set("id", "sd_" + str(depCount))
            alignmentError = False
            if tokenByIndex != None:
                if t1Index-1 not in tokenByIndex:
                    print >> sys.stderr, "Token not found", (t1Word, depCount, sentenceId)
                    deps = []
                    while line.strip() != "": line = outfile.readline()
                    break
                if t2Index-1 not in tokenByIndex:
                    print >> sys.stderr, "Token not found", (t2Word, depCount, sentenceId)
                    deps = []
                    while line.strip() != "": line = outfile.readline()
                    break
                if t1Word != tokenByIndex[t1Index-1].get("text"):
                    print >> sys.stderr, "Alignment error", (t1Word, tokenByIndex[t1Index-1].get("text"), t1Index-1, depCount, sentenceId, tokens)
                    alignmentError = True
                    if parse.get("stanfordAlignmentError") == None:
                        parse.set("stanfordAlignmentError", t1Word)
                if t2Word != tokenByIndex[t2Index-1].get("text"):
                    print >> sys.stderr, "Alignment error", (t2Word, tokenByIndex[t2Index-1].get("text"), t2Index-1, depCount, sentenceId, tokens)
                    alignmentError = True
                    if parse.get("stanfordAlignmentError") == None:
                        parse.set("stanfordAlignmentError", t2Word)
                dep.set("t1", tokenByIndex[t1Index-1].get("id"))
                dep.set("t2", tokenByIndex[t2Index-1].get("id"))
            else:
                dep.set("t1", "bt_" + str(t1Index))
                dep.set("t2", "bt_" + str(t2Index))
            dep.set("type", depType)
            parse.insert(depCount-1, dep)
            depCount += 1
            if not alignmentError:
                deps.append(dep)
        line = outfile.readline()
        try:
            line = getUnicode(line)
            #line = line.encode('raw_unicode_escape').decode('utf-8') # fix latin1?
        except:
            print "Type", type(line)
            print "Repr", repr(line)
            print line
            raise
    return deps

#def convert(input, output=None):
#    global stanfordParserDir, stanfordParserArgs
#
#    workdir = tempfile.mkdtemp()
#    if output == None:
#        output = os.path.join(workdir, "stanford-output.txt")
#    
#    input = os.path.abspath(input)
#    numCorpusSentences = 0
#    inputFile = codecs.open(input, "rt", "utf-8")
#    for line in inputFile:
#        numCorpusSentences += 1
#    inputFile.close()
#    cwd = os.getcwd()
#    os.chdir(stanfordParserDir)
#    #args = ["java", "-mx150m", "-cp", 
#    #        "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
#    #        "-CCprocessed", "-treeFile", "-keepPunct",
#    #        input]
#    args = stanfordParserArgs + [input]
#    #subprocess.call(args,
#    process = subprocess.Popen(args, 
#        stdout=codecs.open(output, "wt", "utf-8"))
#    waitForProcess(process, numCorpusSentences, True, output, "StanfordParser", "Stanford Conversion")
#    os.chdir(cwd)
#
#    lines = None    
#    if output == None:
#        outFile = codecs.open(output, "rt", "utf-8")
#        lines = outFile.readlines()
#        outFile.close()
#    
#    shutil.rmtree(workdir)
#    return lines

def convertXML(parser, input, output=None, debug=False, reparse=False, stanfordParserDir=None, stanfordParserArgs=None):
    #global stanfordParserDir, stanfordParserArgs
    if stanfordParserDir == None:
        stanfordParserDir = Settings.STANFORD_PARSER_DIR
    if stanfordParserArgs == None:
        # not sure how necessary the "-mx500m" option is, and how exactly Java
        # options interact, but adding user defined options from Settings.JAVA
        # after the "-mx500m" hopefully works.
        stanfordParserArgs = Settings.JAVA.split()[0:1] + ["-mx500m"] + \
                             Settings.JAVA.split()[1:] + \
                             ["-cp", "stanford-parser.jar", 
                              "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
                              "-CCprocessed", "-keepPunct", "-treeFile"]
    print >> sys.stderr, "Running Stanford conversion"
    print >> sys.stderr, "Stanford tools at:", stanfordParserDir
    print >> sys.stderr, "Stanford tools arguments:", " ".join(stanfordParserArgs)
    parseTimeStamp = time.strftime("%d.%m.%y %H:%M:%S")
    print >> sys.stderr, "Stanford time stamp:", parseTimeStamp
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    workdir = tempfile.mkdtemp()
    if debug:
        print >> sys.stderr, "Stanford parser workdir", workdir
    stanfordInput = os.path.join(workdir, "input")
    stanfordInputFile = codecs.open(stanfordInput, "wt", "utf-8")
    
    # Put penn tree lines in input file
    existingCount = 0
    for sentence in corpusRoot.getiterator("sentence"):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            parses = setDefaultElement(sentenceAnalyses, "parses")
            parse = getElementByAttrib(parses, "parse", {"parser":parser})
        else:
            analyses = setDefaultElement(sentence, "analyses")
            parse = getElementByAttrib(analyses, "parse", {"parser":parser})
        if parse == None:
            continue
        if len(parse.findall("dependency")) > 0:
            if reparse: # remove existing stanford conversion
                for dep in parse.findall("dependency"):
                    parse.remove(dep)
                del parse.attrib["stanford"]
            else: # don't reparse
                existingCount += 1
                continue
        pennTree = parse.get("pennstring")
        if pennTree == None or pennTree == "":
            continue
        stanfordInputFile.write(pennTree + "\n")
    stanfordInputFile.close()
    if existingCount != 0:
        print >> sys.stderr, "Skipping", existingCount, "already converted sentences."
    
    # Run Stanford parser
    stanfordOutput = runSentenceProcess(runStanford, stanfordParserDir, stanfordInput, 
                                        workdir, True, "StanfordParser", 
                                        "Stanford Conversion", timeout=600,
                                        outputArgs={"encoding":"latin1", "errors":"replace"},
                                        processArgs={"stanfordParserArgs":stanfordParserArgs})   
    #stanfordOutputFile = codecs.open(stanfordOutput, "rt", "utf-8")
    stanfordOutputFile = codecs.open(stanfordOutput, "rt", "latin1", "replace")
    
    # Get output and insert dependencies
    noDepCount = 0
    failCount = 0
    sentenceCount = 0
    for document in corpusRoot.findall("document"):
        for sentence in document.findall("sentence"):
            # Get parse
            if sentence.find("sentenceanalyses") != None: # old format
                sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
                parses = setDefaultElement(sentenceAnalyses, "parses")
                parse = getElementByAttrib(parses, "parse", {"parser":parser})
            else:
                analyses = setDefaultElement(sentence, "analyses")
                parse = getElementByAttrib(analyses, "parse", {"parser":parser})
            if parse == None:
                parse = ET.SubElement(analyses, "parse")
                parse.set("parser", "None")
            if reparse:
                assert len(parse.findall("dependency")) == 0
            elif len(parse.findall("dependency")) > 0: # don't reparse
                continue
            pennTree = parse.get("pennstring")
            if pennTree == None or pennTree == "":
                parse.set("stanford", "no_penn")
                continue
            parse.set("stanfordSource", "TEES") # parser was run through this wrapper
            parse.set("stanfordDate", parseTimeStamp) # links the parse to the log file
            # Get tokens
            if sentence.find("analyses") != None:
                tokenization = getElementByAttrib(sentence.find("analyses"), "tokenization", {"tokenizer":parse.get("tokenizer")})
            else:
                tokenization = getElementByAttrib(sentence.find("sentenceanalyses").find("tokenizations"), "tokenization", {"tokenizer":parse.get("tokenizer")})
            assert tokenization != None
            count = 0
            tokenByIndex = {}
            for token in tokenization.findall("token"):
                tokenByIndex[count] = token
                count += 1
            # Insert dependencies
            origId = document.get("pmid")
            if origId == None:
                origId = document.get("origId")
            origId = str(origId)
            deps = addDependencies(stanfordOutputFile, parse, tokenByIndex, (sentence.get("id"), origId))
            if len(deps) == 0:
                parse.set("stanford", "no_dependencies")
                noDepCount += 1
                if parse.get("stanfordAlignmentError") != None:
                    failCount += 1
            else:
                parse.set("stanford", "ok")
                if parse.get("stanfordAlignmentError") != None:
                    failCount += 1
                    parse.set("stanford", "partial")
            sentenceCount += 1
    stanfordOutputFile.close()
    # Remove work directory
    if not debug:
        shutil.rmtree(workdir)
        
    print >> sys.stderr, "Stanford conversion was done for", sentenceCount, "sentences,", noDepCount, "had no dependencies,", failCount, "failed"
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

def insertParse(sentence, stanfordOutputFile, parser, extraAttributes={}, skipExtra=0):
    # Get parse
    analyses = setDefaultElement(sentence, "analyses")
    #parses = setDefaultElement(sentenceAnalyses, "parses")
    parse = getElementByAttrib(analyses, "parse", {"parser":parser})
    if parse == None:
        parse = ET.SubElement(analyses, "parse")
        parse.set("parser", "None")
    # Remove existing dependencies
    if len(parse.findall("dependency")) > 0:
        for dependency in parse.findall("dependency"):
            parse.remove(dependency)
    # If no penn tree exists, the stanford parsing can't have happened either
    pennTree = parse.get("pennstring")
    if pennTree == None or pennTree == "":
        parse.set("stanford", "no_penn")
    # Must not exit early, so that reading of the stanfordOutputFile stays in sync with the sentences
    #if len(parse.findall("dependency")) > 0: # don't reparse
    #    return True
    #pennTree = parse.get("pennstring")
    #if pennTree == None or pennTree == "":
    #    parse.set("stanford", "no_penn")
    #    return False
    for attr in sorted(extraAttributes.keys()):
        parse.set(attr, extraAttributes[attr])
    # Get tokens
    tokenByIndex = {}
    tokenization = getElementByAttrib(sentence.find("analyses"), "tokenization", {"tokenizer":parse.get("tokenizer")})
    if tokenization != None:
        count = 0
        for token in tokenization.findall("token"):
            tokenByIndex[count] = token
            count += 1
    # Insert dependencies
    deps = addDependencies(stanfordOutputFile, parse, tokenByIndex, (sentence.get("id"), sentence.get("origId")), skipExtra=skipExtra)
    if len(deps) == 0:
        parse.set("stanford", "no_dependencies")
    else:
        parse.set("stanford", "ok")
    return True

def insertParses(input, parsePath, output=None, parseName="McCC", extraAttributes={}, skipExtra=0):
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
    sentenceCount = 0
    docsWithStanford = 0
    sentencesCreated = 0
    sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
    counter = ProgressCounter(len(sourceElements), "McCC Parse Insertion")
    for document in sourceElements:
        docCount += 1
        docId = document.get("id")
        origId = document.get("pmid")
        if origId == None:
            origId = document.get("origId")
        if origId == None:
            origId = document.get("id")
        origId = str(origId)
        if docId == None:
            docId = "CORPUS.d" + str(docCount)
        
        f = openFile(os.path.join(parsePath, origId + ".sd"), tarFile)
        if f == None: # file with BioNLP'11 extension not found, try BioNLP'09 extension
            f = openFile(os.path.join(parsePath, origId + ".dep"), tarFile)
        if f == None: # file with BioNLP'09 extension not found, try BioNLP'13 extension
            f = openFile(os.path.join(parsePath, origId + ".sdepcc"), tarFile)
        if f == None: # file with BioNLP'09 extension not found, try BioNLP'13 extension
            f = openFile(os.path.join(parsePath, origId + ".sdep"), tarFile)
        if f != None:
            sentences = document.findall("sentence")
            # TODO: Following for-loop is the same as when used with a real parser, and should
            # be moved to its own function.
            for sentence in sentences:
                sentenceCount += 1
                counter.update(0, "Processing Documents ("+sentence.get("id")+"/" + origId + "): ")
                if not insertParse(sentence, f, parseName, extraAttributes={}, skipExtra=skipExtra):
                    failCount += 1
            f.close()
        counter.update(1, "Processing Documents ("+document.get("id")+"/" + origId + "): ")
    
    if tarFile != None:
        tarFile.close()
    #print >> sys.stderr, "Sentence splitting created", sentencesCreated, "sentences"
    #print >> sys.stderr, docsWithSentences, "/", docCount, "documents have stanford parses"

    print >> sys.stderr, "Stanford conversion was inserted to", sentenceCount, "sentences" #, failCount, "failed"
        
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

    optparser = OptionParser(description="Stanford Parser dependency converter wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Name of parse element.")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--reparse", default=False, action="store_true", dest="reparse", help="")
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
        convertXML(input=options.input, output=options.output, parser=options.parse, debug=options.debug, reparse=options.reparse)
        