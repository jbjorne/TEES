import sys, os
from collections import defaultdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
import Utils.ElementTreeUtils as ETUtils
from Parser import Parser

class ParseConverter(Parser):    
    @classmethod
    def insertCls(cls, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKey="origId"):
        parserObj = cls()
        parserObj.parse(parseDir, input, output, parseName, extensions, subDirs, debug, skipParsed, docMatchKey)
    
    def readParses(self, parseDir, extensions, subDirs, counts):
        files = {}
        for filename in os.listdir(parseDir):
            if "." not in filename:
                continue
            docName, ext = filename.rsplit(".", 1)
            if ext not in extensions:
                continue
            if docName not in files:
                files[docName] = {}
            files[docName][ext] = os.path.join(parseDir, filename)
            counts[ext + "-read"] += 1
            
    def insertParses(self, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKey="origId"):
        corpusTree, corpusRoot = self.getCorpus(input)
        if not os.path.exists(parseDir):
            raise Exception("Cannot find parse input '" + str(parseDir) + "'")
        if not os.path.isdir(parseDir):
            raise Exception("Parse input '" + str(parseDir) + "' is not a directory")
        if extensions == None:
            extensions = ["ptb", "conll", "sd"]
        print >> sys.stderr, "Inserting parses from file types:", extensions
        files = self.readParses(parseDir, extensions, subDirs, counts)
        counts = defaultdict(int)
        for filename in os.listdir(parseDir):
            if "." not in filename:
                continue
            docName, ext = filename.rsplit(".", 1)
            if ext not in extensions:
                continue
            if docName not in files:
                files[docName] = {}
            files[docName][ext] = os.path.join(parseDir, filename)
            counts[ext + "-read"] += 1
        for document in corpusRoot.findall("document"):
            counts["document"] += 1
            docMatchValue = document.get(docMatchKey)
            if docMatchValue not in files:
                continue
            counts["document-match"] += 1
            for ext in extensions:
                if ext not in files[docMatchValue]:
                    continue
                counts[ext + "-match"] += 1
                if ext == "ptb":
                    self.insertPennTrees(files[docMatchValue][ext], document, skipParsed=skipParsed, addTimeStamp=False)
                elif ext == "conll":
                    self.insertCoNLLParses(files[docMatchValue][ext], document, skipParsed=skipParsed, addTimeStamp=False)
                elif ext == "sd":
                    self.insertDependencyParses(files[docMatchValue][ext], document, skipParsed=skipParsed, addTimeStamp=False)
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
    optparser.add_option("-d", "--parseDir", default=None, dest="parseDir", help="Parse files directory")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="Name of the parse element")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    ParseConverter.insertCls(options.parse, options.input, options.output, options.debug, False, options.syntaxNetDir)        