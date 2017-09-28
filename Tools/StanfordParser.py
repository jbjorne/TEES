import sys, os
import shutil
import subprocess
import tempfile
import tarfile
import codecs
import time
import ProcessUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
from collections import defaultdict
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
import Utils.ElementTreeUtils as ETUtils
import Utils.Settings as Settings
import Utils.Download as Download
# from Utils.ProgressCounter import ProgressCounter
# from Utils.FileUtils import openWithExt, getTarFilePath
import Tool
from Parser import Parser

class StanfordParser(Parser):
    ###########################################################################
    # Installation
    ###########################################################################
    def install(self, destDir=None, downloadDir=None, redownload=False, updateLocalSettings=False):
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
    
    ###########################################################################
    # Main Interface
    ###########################################################################
    
#     @classmethod
#     def parseCls(cls, parserName, input, output=None, debug=False, reparse=False, stanfordParserDir=None, stanfordParserArgs=None, action="convert", outputFormat=None):
#         parserObj = cls()
#         parserObj.parse(parserName, input, output, debug, reparse, stanfordParserDir, stanfordParserArgs, action, outputFormat)
    
    def parse(self, parserName, input, output=None, debug=False, reparse=False, stanfordParserDir=None, stanfordParserArgs=None, action="convert", outputFormat=None, memory=None):
        #global stanfordParserDir, stanfordParserArgs
        assert action in ("convert", "penn", "dep")
        if stanfordParserDir == None:
            stanfordParserDir = Settings.STANFORD_PARSER_DIR
        # Run the parser process
        corpusTree, corpusRoot = self.getCorpus(input)
        workdir = tempfile.mkdtemp()
        inPath = self.makeInputFile(corpusRoot, workdir, parserName, reparse, action, debug)
        outPath = self.runProcess(stanfordParserArgs, stanfordParserDir, inPath, workdir, action, outputFormat, memory)
        self.printStderr(outPath)
        # Insert the parses    
        if action in ("convert", "dep"):
            #self.insertDependencyParses(outPath, corpusRoot, parserName, {"stanford-mode":action}, addTimeStamp=True, skipExtra=0, removeExisting=True)
            self.insertStanfordDependencyParses(outPath, corpusRoot, parserName, skipParsed=reparse, removeExisting=reparse)
        elif action == "penn":
            self.insertPennTrees(outPath, corpusRoot, parserName)
        # Remove work directory
        if not debug:
            shutil.rmtree(workdir)
        else:
            print >> sys.stderr, "Parser IO files at", workdir
        # Write the output XML file
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        return corpusTree
    
    ###########################################################################
    # Parser Process Control
    ###########################################################################
    
    def getStderrPath(self, outputFilePath):
        return os.path.join(os.path.dirname(outputFilePath), "stderr.log")
    
    def printStderr(self, outputFilePath):
        stderrPath = self.getStderrPath(outputFilePath)
        s = ""
        with codecs.open(stderrPath, "rt", "utf-8") as stderrFile:
            for line in stderrFile:
                line = line.strip()
                if line != "" and not line.startswith("Parsing [sent."):
                    s += line + "\n"
        if s != "":
            print >> sys.stderr, "Parser output from", stderrPath + ":"
            print >> sys.stderr, "---\n", s, "---"

    def run(self, input, output, stanfordParserArgs):
        return subprocess.Popen(stanfordParserArgs + [input], stdout=codecs.open(output, "wt", "utf-8"), stderr=codecs.open(self.getStderrPath(output), "wt", "utf-8"))
        
    def runProcess(self, stanfordParserArgs, stanfordParserDir, stanfordInput, workdir, action="convert", outputFormat=None, memory=None):
        if stanfordParserArgs == None:
            # not sure how necessary the "-mx500m" option is, and how exactly Java
            # options interact, but adding user defined options from Settings.JAVA
            # after the "-mx500m" hopefully works.
            stanfordParserArgs = Settings.JAVA.split()[0:1] + ["-mx" + str(memory if memory != None else 500) + "m"] + Settings.JAVA.split()[1:]
            if action == "convert":
                if outputFormat == None: 
                    outputFormat = "CCprocessed"
                stanfordParserArgs += ["-cp", "stanford-parser.jar", 
                                      "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
                                      "-encoding", "utf8", 
                                      "-" + outputFormat, "-keepPunct", "-treeFile"]
                print >> sys.stderr, "Running Stanford conversion"
            else: # action in ("penn", "dep")
                stanfordParserArgs += ["-cp", "./*",
                                      "edu.stanford.nlp.parser.lexparser.LexicalizedParser",
                                      "-encoding", "utf8",
                                      "-sentences", "newline"] #"-escaper", "edu.stanford.nlp.process.PTBEscapingProcessor"]                
                # Add action specific options
                tokenizerOptions = "untokenizable=allKeep"
                if action == "penn":
                    # Add tokenizer options
                    #for normalization in ("Space", "AmpersandEntity", "Currency", "Fractions", "OtherBrackets"):
                    #    tokenizerOptions += ",normalize" + normalization + "=false"
                    #for tokOpt in ("americanize", "asciiQuotes", "latexQuotes", "unicodeQuotes", "ptb3Ellipsis", "ptb3Dashes", "escapeForwardSlashAsterisk"):
                    #    tokenizerOptions += "," + tokOpt + "=false"
                    stanfordParserArgs += ["-tokenizerOptions", tokenizerOptions]
                    stanfordParserArgs += ["-outputFormat", "oneline"]
                else: # action == "dep"
                    if outputFormat == None: 
                        outputFormat = "typedDependenciesCollapsed"
                    stanfordParserArgs += ["-tokenizerOptions", tokenizerOptions,
                                           #"-tokenized",
                                           #"-escaper", "edu.stanford.nlp.process.PTBEscapingProcessor",
                                           #"-tokenizerFactory", "edu.stanford.nlp.process.WhitespaceTokenizer",
                                           #"-tokenizerMethod", "newCoreLabelTokenizerFactory",
                                           "-outputFormat", outputFormat]
                stanfordParserArgs += ["edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"]
                print >> sys.stderr, "Running Stanford parsing for target", action
        print >> sys.stderr, "Stanford tools at:", stanfordParserDir
        print >> sys.stderr, "Stanford tools arguments:", " ".join(stanfordParserArgs)
        # Run Stanford parser
        return ProcessUtils.runSentenceProcess(self.run, stanfordParserDir, stanfordInput, 
            workdir, False if action == "penn" else True, 
            "StanfordParser", "Stanford (" + action + ")", timeout=600,
            outputArgs={"encoding":"latin1", "errors":"replace"},
            processArgs={"stanfordParserArgs":stanfordParserArgs})
    
    ###########################################################################
    # Parsing Process File IO
    ###########################################################################
    
    def makeInputFile(self, corpusRoot, workdir, parserName, reparse=False, action="convert", debug=False):
        if debug:
            print >> sys.stderr, "Stanford parser workdir", workdir
        stanfordInput = os.path.join(workdir, "input")
        stanfordInputFile = codecs.open(stanfordInput, "wt", "utf-8")
        
        existingCount = 0
        for sentence in corpusRoot.getiterator("sentence"):
            if action in ("convert", "dep"):
                parse = IXMLUtils.getParseElement(sentence, parserName, addIfNotExist=(action == "dep"))
                pennTree = ""
                # Sentences with no parse (from the constituency step) are skipped in converter mode
                if parse != None:
                    # Both the 'convert' and 'dep' actions rely on tokens generated from the penn tree
                    pennTree = parse.get("pennstring", "")
                    # Check for existing dependencies
                    if len(parse.findall("dependency")) > 0:
                        if reparse: # remove existing stanford conversion
                            for dep in parse.findall("dependency"):
                                parse.remove(dep)
                            del parse.attrib["stanford"]
                        else: # don't reparse
                            existingCount += 1
                            pennTree = ""
                # Generate the input
                if action == "convert": # Put penn tree lines in input file
                    inputString = pennTree
                    if inputString == "":
                        inputString = "(S1 (S (NN DUMMYINPUTTOKEN)))"
                else: # action == "dep"
                    #tokenization = IXMLUtils.getTokenizationElement(sentence, parserName, addIfNotExist=False)
                    #if tokenization != None:
                    #    tokenized = " ".join([x.get("text") for x in tokenization.findall("token")])
                    #    stanfordInputFile.write(tokenized.replace("\n", " ").replace("\r", " ").strip() + "\n")
                    #else:
                    inputString = sentence.get("text").replace("\n", " ").replace("\r", " ").strip()
                inputString = inputString.strip()
                if inputString == "":
                    inputString = "DUMMYINPUTTOKEN" # The parser skips empty lines
                stanfordInputFile.write(inputString  + "\n")
            else: # action == "penn"
                stanfordInputFile.write(sentence.get("text").replace("\n", " ").replace("\r", " ").strip() + "\n")
        stanfordInputFile.close()
        if existingCount != 0:
            print >> sys.stderr, "Skipping", existingCount, "already converted sentences."
        return stanfordInput
    
#     def insertDependencyOutput(self, corpusRoot, parserOutputPath, workdir, parserName, reparse, action, debug):
#         #stanfordOutputFile = codecs.open(stanfordOutput, "rt", "utf-8")
#         #stanfordOutputFile = codecs.open(stanfordOutput, "rt", "latin1", "replace")
#         parserOutputFile = codecs.open(parserOutputPath, "rt", "utf-8") 
#         # Get output and insert dependencies
#         parseTimeStamp = time.strftime("%d.%m.%y %H:%M:%S")
#         print >> sys.stderr, "Stanford time stamp:", parseTimeStamp
#         counts = defaultdict(int)
#         extraAttributes={"stanfordSource":"TEES", # parser was run through this wrapper
#                          "stanfordDate":parseTimeStamp, # links the parse to the log file
#                          "depParseType":action
#                         }
#         for document in corpusRoot.findall("document"):
#             for sentence in document.findall("sentence"):
#                 self.insertDependencyParse(sentence, parserOutputFile, parserName, parserName, extraAttributes, counts, skipExtra=0, removeExisting=reparse)
#         parserOutputFile.close()
#         # Remove work directory
#         if not debug:
#             shutil.rmtree(workdir)
#         else:
#             print >> sys.stderr, "Parser IO files at", workdir

#     ###########################################################################
#     # Serialized Parses
#     ###########################################################################
#     
#     def insertParses(self, input, parsePath, output=None, parseName="McCC", extraAttributes={}, skipExtra=0):
#         """
#         Divide text in the "text" attributes of document and section 
#         elements into sentence elements. These sentence elements are
#         inserted into their respective parent elements.
#         """  
#         corpusTree, corpusRoot = self.getCorpus(input)
#         
#         print >> sys.stderr, "Inserting parses from", parsePath
#         assert os.path.exists(parsePath)
#         tarFilePath, parsePath = getTarFilePath(parsePath)
#         tarFile = None
#         if tarFilePath != None:
#             tarFile = tarfile.open(tarFilePath)
#         
#         counts = defaultdict(int) #counts = {"fail":0, "no_dependencies":0, "sentences":0, "documents":0, "existing":0, "no_penn":0}
#         sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
#         counter = ProgressCounter(len(sourceElements), "McCC Parse Insertion")
#         for document in sourceElements:
#             counts["document"] += 1
#             docId = document.get("id")
#             origId = self.getDocumentOrigId(document)
#             if docId == None:
#                 docId = "CORPUS.d" + str(counts["document"])
#             
#             f = openWithExt(os.path.join(parsePath, origId), ["sd", "dep", "sdepcc", "sdep"]) # Extensions for BioNLP 2011, 2009, and 2013
#             if f != None:
#                 for sentence in document.findall("sentence"):
#                     counts["sentences"] += 1
#                     counter.update(0, "Processing Documents ("+sentence.get("id")+"/" + origId + "): ")
#                     self.insertDependencyParse(sentence, f, parseName, parseName, extraAttributes, counts, skipExtra, removeExisting=False)
#                     #self.insertParse(sentence, f, parseName, True, None, counts, skipExtra, origId)
#                 f.close()
#             counter.update(1, "Processing Documents ("+document.get("id")+"/" + origId + "): ")        
#         if tarFile != None:
#             tarFile.close()
#         print >> sys.stderr, "Stanford conversion was inserted to", counts["sentences"], "sentences" #, failCount, "failed"
#             
#         if output != None:
#             print >> sys.stderr, "Writing output to", output
#             ETUtils.write(corpusRoot, output)
#         return corpusTree

if __name__=="__main__":
    from optparse import OptionParser, OptionGroup
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
    
    parser = StanfordParser()
    if options.install:
        parser.install(options.installDir, options.downloadDir, redownload=options.redownload)
    else:
        parser.convertXML(input=options.input, output=options.output, parser=options.parse, debug=options.debug, reparse=options.reparse)
        