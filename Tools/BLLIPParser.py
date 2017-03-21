import sys,os
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
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import Utils.Settings as Settings
import Utils.Download as Download
from Utils.ProgressCounter import ProgressCounter
import Tool
from Parser import Parser
import ProcessUtils

class BLLIPParser(Parser):
    ###########################################################################
    # Installation
    ###########################################################################
    def install(self, destDir=None, downloadDir=None, redownload=False, updateLocalSettings=False):
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
    
    ###########################################################################
    # Main Interface
    ###########################################################################
    
#     @classmethod
#     def parseCls(cls, input, output=None, tokenizationName=None, parseName="McCC", requireEntities=False, skipIds=[], skipParsed=True, timeout=600, makePhraseElements=True, debug=False, pathParser=None, pathBioModel="AUTO", timestamp=True):
#         parser = cls()
#         parser.parse(input, output, tokenizationName, parseName, requireEntities, skipIds, skipParsed, timeout, makePhraseElements, debug, pathParser, pathBioModel, timestamp)
    
    def parse(self, input, output=None, tokenizationName=None, parseName="McCC", requireEntities=False, skipIds=[], skipParsed=True, timeout=600, makePhraseElements=True, debug=False, pathParser=None, pathBioModel="AUTO", addTimeStamp=True):
        print >> sys.stderr, "BLLIP parser"
        corpusTree, corpusRoot = self.getCorpus(input)
        workdir = tempfile.mkdtemp()
        infileName, numCorpusSentences = self.makeInputFile(workdir, corpusRoot, requireEntities, skipIds, skipParsed, tokenizationName, debug)
        bllipOutput = self.runProcess(infileName, workdir, pathParser, pathBioModel, tokenizationName, timeout)        
        self.insertPennTrees(bllipOutput, corpusRoot, parseName, requireEntities, skipIds, skipParsed)
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        # Remove work directory
        if not debug:
            shutil.rmtree(workdir)
        else:
            print >> sys.stderr, "Parser IO files at", workdir
        return corpusTree
    
    ###########################################################################
    # Parser Process Control
    ###########################################################################
    
    def run(self, input, output, tokenizer=False, pathBioModel=None):
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
        
    def runProcess(self, infileName, workdir, pathParser, pathBioModel, tokenizationName, timeout):
        if pathParser == None:
            pathParser = Settings.BLLIP_PARSER_DIR
        print >> sys.stderr, "BLLIP parser at:", pathParser
        if pathBioModel == "AUTO":
            pathBioModel = Settings.MCCLOSKY_BIOPARSINGMODEL_DIR
        if pathBioModel != None:
            print >> sys.stderr, "Biomodel at:", pathBioModel
        #PARSERROOT=/home/smp/tools/McClosky-Charniak/reranking-parser
        #BIOPARSINGMODEL=/home/smp/tools/McClosky-Charniak/reranking-parser/biomodel
        #${PARSERROOT}/first-stage/PARSE/parseIt -K -l399 -N50 ${BIOPARSINGMODEL}/parser/ $* | ${PARSERROOT}/second-stage/programs/features/best-parses -l ${BIOPARSINGMODEL}/reranker/features.gz ${BIOPARSINGMODEL}/reranker/weights.gz
        
        # Run parser
        #print >> sys.stderr, "Running parser", pathParser + "/parse.sh"
        cwd = os.getcwd()
        os.chdir(pathParser)
        if tokenizationName == None:
            bllipOutput = ProcessUtils.runSentenceProcess(self.run, pathParser, infileName, workdir, False, "BLLIPParser", "Parsing", timeout=timeout, processArgs={"tokenizer":True, "pathBioModel":pathBioModel})   
        else:
            if tokenizationName == "PARSED_TEXT": # The sentence strings are already tokenized
                tokenizationName = None
            bllipOutput = ProcessUtils.runSentenceProcess(self.run, pathParser, infileName, workdir, False, "BLLIPParser", "Parsing", timeout=timeout, processArgs={"tokenizer":False, "pathBioModel":pathBioModel})   
    #    args = [charniakJohnsonParserDir + "/parse-50best-McClosky.sh"]
    #    #bioParsingModel = charniakJohnsonParserDir + "/first-stage/DATA-McClosky"
    #    #args = charniakJohnsonParserDir + "/first-stage/PARSE/parseIt -K -l399 -N50 " + bioParsingModel + "/parser | " + charniakJohnsonParserDir + "/second-stage/programs/features/best-parses -l " + bioParsingModel + "/reranker/features.gz " + bioParsingModel + "/reranker/weights.gz"
        os.chdir(cwd)
        return bllipOutput
    
    ###########################################################################
    # Parsing Process File IO
    ###########################################################################
    
    def makeInputFile(self, workdir, corpusRoot, requireEntities, skipIds, skipParsed, tokenizationName, debug):    
        if requireEntities:
            print >> sys.stderr, "Parsing only sentences with entities"
        # Write text to input file
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
            for sentence in self.getSentences(corpusRoot, requireEntities, skipIds, skipParsed):
                infile.write("<s> " + sentence.get("text").replace("\n", " ").replace("\r", " ").strip() + " </s>\n")
                numCorpusSentences += 1
        else: # Use existing tokenization
            print >> sys.stderr, "Using existing tokenization", tokenizationName 
            for sentence in self.getSentences(corpusRoot, requireEntities, skipIds, skipParsed):
                tokenization = IXMLUtils.getElementByAttrib(sentence.find("analyses"), "tokenization", {"tokenizer":tokenizationName})
                assert tokenization.get("tokenizer") == tokenizationName
                s = ""
                for token in tokenization.findall("token"):
                    s += token.get("text") + " "
                infile.write("<s> " + s + "</s>\n")
                numCorpusSentences += 1
        infile.close()
        return infileName, numCorpusSentences
    
#     ###########################################################################
#     # Serialized Parses
#     ###########################################################################
#     
#     def insertParses(self, input, parsePath, output=None, parseName="McCC", tokenizationName = None, makePhraseElements=True, extraAttributes={}):
#         import tarfile
#         from SentenceSplitter import openFile
#         """
#         Divide text in the "text" attributes of document and section 
#         elements into sentence elements. These sentence elements are
#         inserted into their respective parent elements.
#         """  
#         print >> sys.stderr, "Loading corpus", input
#         corpusTree = ETUtils.ETFromObj(input)
#         print >> sys.stderr, "Corpus file loaded"
#         corpusRoot = corpusTree.getroot()
#         
#         print >> sys.stderr, "Inserting parses from", parsePath
#         assert os.path.exists(parsePath)
#         if parsePath.find(".tar.gz") != -1:
#             tarFilePath, parsePath = parsePath.split(".tar.gz")
#             tarFilePath += ".tar.gz"
#             tarFile = tarfile.open(tarFilePath)
#             if parsePath[0] == "/":
#                 parsePath = parsePath[1:]
#         else:
#             tarFile = None
#         
#         docCount = 0
#         failCount = 0
#         numCorpusSentences = 0
#         sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
#         counter = ProgressCounter(len(sourceElements), "McCC Parse Insertion")
#         for document in sourceElements:
#             docCount += 1
#             origId = document.get("pmid")
#             if origId == None:
#                 origId = document.get("origId")
#             if origId == None:
#                 origId = document.get("id")
#             origId = str(origId)
#             counter.update(1, "Processing Documents ("+document.get("id")+"/" + origId + "): ")
#             docId = document.get("id")
#             if docId == None:
#                 docId = "CORPUS.d" + str(docCount)
#             
#             f = openFile(os.path.join(parsePath, origId + ".ptb"), tarFile)
#             if f == None: # file with BioNLP'11 extension not found, try BioNLP'09 extension
#                 f = openFile(os.path.join(parsePath, origId + ".pstree"), tarFile)
#                 if f == None: # no parse found
#                     continue
#             parseStrings = f.readlines()
#             f.close()
#             sentences = document.findall("sentence")
#             numCorpusSentences += len(sentences)
#             assert len(sentences) == len(parseStrings)
#             # TODO: Following for-loop is the same as when used with a real parser, and should
#             # be moved to its own function.
#             for sentence, treeLine in zip(sentences, parseStrings):
#                 if not self.insertPennTree(sentence, treeLine, makePhraseElements=makePhraseElements, extraAttributes=extraAttributes, docId=origId):
#                     failCount += 1
#         
#         if tarFile != None:
#             tarFile.close()
#         if output != None:
#             print >> sys.stderr, "Writing output to", output
#             ETUtils.write(corpusRoot, output)
#         return corpusTree
    
if __name__=="__main__":
    from optparse import OptionParser, OptionGroup
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
    
    parser = BLLIPParser()
    if options.install:
        parser.install(options.installDir, options.downloadDir, redownload=options.redownload)
    else:
        xml = parser.parse(input=options.input, output=options.output, tokenizationName=options.tokenization, pathParser=options.pathParser, pathBioModel=options.pathBioModel, timestamp=options.timestamp)
        if options.stanford:
            from StanfordParser import StanfordParser
            StanfordParser().convertXML(parser="McClosky", input=xml, output=options.output)
    