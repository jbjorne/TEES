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
from Utils.ProgressCounter import ProgressCounter
from Utils.FileUtils import openWithExt, getTarFilePath
import Tool
from Parser import Parser

class SyntaxNetParser(Parser):    
    ###########################################################################
    # Main Interface
    ###########################################################################
    
    @classmethod
    def parseCls(cls, parserName, input, output=None, debug=False, reparse=False, syntaxNetDir=None):
        parserObj = cls()
        parserObj.parse(parserName, input, output, debug, reparse, syntaxNetDir)
    
    def parse(self, parserName, input, output=None, debug=False, reparse=False, syntaxNetDir=None):
        # Run the parser process
        corpusTree, corpusRoot = self.getCorpus(input)
        workdir = tempfile.mkdtemp()
        inPath = self.makeInputFile(corpusRoot, workdir, parserName, reparse, action, debug)
        outPath = self.runProcess(stanfordParserArgs, stanfordParserDir, inPath, workdir, action)
        self.printStderr(outPath)
        # Insert the parses    
        if action in ("convert", "dep"):
            self.insertDependencyParses(outPath, corpusRoot, parserName, {"stanford-mode":action}, addTimeStamp=True, skipExtra=0, removeExisting=True)
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

    def run(self, input, output):
        parserEval = "bazel-bin/syntaxnet/parser_eval"
        modelDir = "syntaxnet/models/parsey_mcparseface"
        
        taggerArgs = ["--input", "stdin"
                      "--output", "stdout-conll",
                      "--hidden_layer_sizes", "64",
                      "--arg_prefix", "brain_tagger",
                      "--graph_builder", "structured",
                      "--task_context", os.path.join(modelDir, "context.pbtxt"),
                      "--model_path", os.path.join(modelDir, "tagger-params"),
                      "--slim_model",
                      "--batch_size", "1024",
                      "--alsologtostderr"]

      $PARSER_EVAL \
  --input=stdin-conll \
  --output=stdout-conll \
  --hidden_layer_sizes=512,512 \
  --arg_prefix=brain_parser \
  --graph_builder=structured \
  --task_context=$MODEL_DIR/context.pbtxt \
  --model_path=$MODEL_DIR/parser-params \
  --slim_model \
  --batch_size=1024 \
  --alsologtostderr

        if pathBioModel != None:
            assert os.path.exists(pathBioModel), pathBioModel
        if tokenizer:
            print >> sys.stderr, "Running BLLIP parser with tokenization"
            firstStageArgs = ["first-stage/PARSE/parseIt", "-l999", "-N50"]
        else:
            print >> sys.stderr, "Running BLLIP parser without tokenization"
            firstStageArgs = ["first-stage/PARSE/parseIt", "-l999", "-N50" , "-K"]
        secondStageArgs = ["second-stage/programs/features/best-parses", "-l"]
        if pathBioModel != None:
            firstStageArgs += [pathBioModel+"/parser/"]
            secondStageArgs += [pathBioModel+"/reranker/features.gz", pathBioModel+"/reranker/weights.gz"]
        else:
            firstStageArgs += ["first-stage/DATA/EN/"]
            secondStageArgs += ["second-stage/models/ec50spfinal/features.gz", "second-stage/models/ec50spfinal/cvlm-l1c10P1-weights.gz"]
        print >> sys.stderr, "1st Stage arguments:", firstStageArgs
        print >> sys.stderr, "2nd Stage arguments:", secondStageArgs 
        firstStage = subprocess.Popen(firstStageArgs,
                                      stdin=codecs.open(input, "rt", "utf-8"),
                                      stdout=subprocess.PIPE)
        secondStage = subprocess.Popen(secondStageArgs,
                                       stdin=firstStage.stdout,
                                       stdout=codecs.open(output, "wt", "utf-8"))
        return ProcessUtils.ProcessWrapper([firstStage, secondStage])
        
    def runProcess(self, stanfordParserArgs, stanfordParserDir, stanfordInput, workdir, action="convert"):
        if stanfordParserArgs == None:
            # not sure how necessary the "-mx500m" option is, and how exactly Java
            # options interact, but adding user defined options from Settings.JAVA
            # after the "-mx500m" hopefully works.
            stanfordParserArgs = Settings.JAVA.split()[0:1] + ["-mx500m"] + Settings.JAVA.split()[1:]
            if action == "convert":
                stanfordParserArgs += ["-cp", "stanford-parser.jar", 
                                      "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
                                      "-encoding", "utf8", 
                                      "-CCprocessed", "-keepPunct", "-treeFile"]
                print >> sys.stderr, "Running Stanford conversion"
            else:
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
                    stanfordParserArgs += ["-tokenizerOptions", tokenizerOptions,
                                           #"-tokenized",
                                           #"-escaper", "edu.stanford.nlp.process.PTBEscapingProcessor",
                                           #"-tokenizerFactory", "edu.stanford.nlp.process.WhitespaceTokenizer",
                                           #"-tokenizerMethod", "newCoreLabelTokenizerFactory",
                                           "-outputFormat", "typedDependencies"]
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
                # Sentences with no parse (from the constituency step) are skipped in converter mode
                if parse == None:
                    continue
                # Both the 'convert' and 'dep' actions rely on tokens generated from the penn tree
                pennTree = parse.get("pennstring")
                if pennTree == None or pennTree == "":
                    continue
                # Check for existing dependencies
                if len(parse.findall("dependency")) > 0:
                    if reparse: # remove existing stanford conversion
                        for dep in parse.findall("dependency"):
                            parse.remove(dep)
                        del parse.attrib["stanford"]
                    else: # don't reparse
                        existingCount += 1
                        continue
                # Generate the input
                if action == "convert": # Put penn tree lines in input file
                    stanfordInputFile.write(pennTree + "\n")
                else: # action == "dep"
                    #tokenization = IXMLUtils.getTokenizationElement(sentence, parserName, addIfNotExist=False)
                    #if tokenization != None:
                    #    tokenized = " ".join([x.get("text") for x in tokenization.findall("token")])
                    #    stanfordInputFile.write(tokenized.replace("\n", " ").replace("\r", " ").strip() + "\n")
                    #else:
                    stanfordInputFile.write(sentence.get("text").replace("\n", " ").replace("\r", " ").strip() + "\n")
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

    ###########################################################################
    # Serialized Parses
    ###########################################################################
    
    def insertParses(self, input, parsePath, output=None, parseName="McCC", extraAttributes={}, skipExtra=0):
        """
        Divide text in the "text" attributes of document and section 
        elements into sentence elements. These sentence elements are
        inserted into their respective parent elements.
        """  
        corpusTree, corpusRoot = self.getCorpus(input)
        
        print >> sys.stderr, "Inserting parses from", parsePath
        assert os.path.exists(parsePath)
        tarFilePath, parsePath = getTarFilePath(parsePath)
        tarFile = None
        if tarFilePath != None:
            tarFile = tarfile.open(tarFilePath)
        
        counts = defaultdict(int) #counts = {"fail":0, "no_dependencies":0, "sentences":0, "documents":0, "existing":0, "no_penn":0}
        sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
        counter = ProgressCounter(len(sourceElements), "McCC Parse Insertion")
        for document in sourceElements:
            counts["document"] += 1
            docId = document.get("id")
            origId = self.getDocumentOrigId(document)
            if docId == None:
                docId = "CORPUS.d" + str(counts["document"])
            
            f = openWithExt(os.path.join(parsePath, origId), ["sd", "dep", "sdepcc", "sdep"]) # Extensions for BioNLP 2011, 2009, and 2013
            if f != None:
                for sentence in document.findall("sentence"):
                    counts["sentences"] += 1
                    counter.update(0, "Processing Documents ("+sentence.get("id")+"/" + origId + "): ")
                    self.insertDependencyParse(sentence, f, parseName, parseName, extraAttributes, counts, skipExtra, removeExisting=False)
                    #self.insertParse(sentence, f, parseName, True, None, counts, skipExtra, origId)
                f.close()
            counter.update(1, "Processing Documents ("+document.get("id")+"/" + origId + "): ")        
        if tarFile != None:
            tarFile.close()
        print >> sys.stderr, "Stanford conversion was inserted to", counts["sentences"], "sentences" #, failCount, "failed"
            
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        return corpusTree

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
        