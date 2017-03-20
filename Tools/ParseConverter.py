import sys, os
import shutil
import subprocess
import tempfile
import codecs
import ProcessUtils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
import Utils.ElementTreeUtils as ETUtils
from Parser import Parser
import Utils.Settings as Settings

class ParseConverter(Parser):
    
    ###########################################################################
    # Main Interface
    ###########################################################################
    
    @classmethod
    def insertCls(cls, parserName, input, output=None, debug=False, reparse=False, syntaxNetDir=None, modelDir=None):
        parserObj = cls()
        parserObj.parse(parserName, input, output, debug, reparse, syntaxNetDir, modelDir)
    
    def loadParses(self, corpusRoot, parseInput, extensions=None):
        if not os.path.exists(parseInput):
            raise Exception("Cannot find parse input '" + str(parseInput) + "'")
        if os.path.isdir(parseInput):
            if extensions == None:
                extensions = ["ptb", "conll", "sd"]
            files = {}
            for filename in os.listdir(parseInput):
                if "." not in filename:
                    continue
                docName, ext = filename.rsplit(".", 1)
                if ext not in extensions:
                    continue
                if docName not in files:
                    files[docName] = {}
                files[docName][ext] = os.path.join(parseInput, filename)
            for document in corpusRoot.findall("document"):
                origId = document.get("origId")
                if origId not in files:
                    continue
                for ext in extensions:
                    if ext not in files[origId]:
                        continue
                    elif ext == "ptb":
                        self.insertPennTrees(files[origId][ext], document, addTimeStamp=False)
                    elif ext == "conll":
                        self.insertCoNLLParses(files[origId][ext], document, addTimeStamp=False)
                    elif ext == "sd":
                        self.insertDependencyParses(files[origId][ext], document, addTimeStamp=False)
                        
                
    
    def insert(self, parseInput, input, output=None, debug=False, reparse=False):
        corpusTree, corpusRoot = self.getCorpus(input)
        workdir = tempfile.mkdtemp()
        inPath = self.makeInputFile(corpusRoot, workdir)
        outPath = ProcessUtils.runSentenceProcess(self.run, syntaxNetDir, inPath, workdir, True, "SyntaxNetParser", "Parsing", processArgs={"modelDir":modelDir})
        self.insertCoNLLParses(outPath, corpusRoot, parserName)
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

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="SyntaxNet Parser Wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="Name of the parse element")
    optparser.add_option("-d", "--syntaxNetDir", default=None, dest="syntaxNetDir", help="SyntaxNet program directory")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    SyntaxNetParser.parseCls(options.parse, options.input, options.output, options.debug, False, options.syntaxNetDir)        