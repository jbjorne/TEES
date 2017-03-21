import sys, os
from collections import defaultdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
import Utils.ElementTreeUtils as ETUtils
from Parser import Parser
from Utils.ProgressCounter import ProgressCounter

class ParseConverter(Parser):    
#     @classmethod
#     def insertCls(cls, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKey="origId"):
#         parserObj = cls()
#         parserObj.insertParses(parseDir, input, output, parseName, extensions, subDirs, debug, skipParsed, docMatchKey)
    
    def readParses(self, parseDir, extensions, subDirs, counts):
        files = {}
        if subDirs == None:
            subDirs = ["ptb", "conll", "sd_ccproc"]
        directories = [parseDir] + [os.path.join(parseDir, x) for x in subDirs]
        for directory in directories:
            if not os.path.exists(directory):
                continue
            print >> sys.stderr, "Collecting parses from", directory
            for filename in os.listdir(parseDir):
                if "." not in filename:
                    continue
                docName, ext = filename.rsplit(".", 1)
                if ext not in extensions:
                    continue
                if docName not in files:
                    files[docName] = {}
                filePath = os.path.join(parseDir, filename)
                if ext in files[docName]:
                    print >> sys.stderr, "Multiple files for extension", ext, [files[docName][ext], filePath]
                files[docName][ext] = filePath
                counts[ext + "-read"] += 1
        return files
    
    def prepareSentences(self, document, sentences, sentObjs, splitting=False, counts=None):
        if not splitting:
            return sentences
        if len(sentObjs) > 0 and len(sentences) == 0:
            self.splitSentences(sentObjs, document, "Splitting Sentences", counts)
        return [x for x in document.findall("sentence")]
            
    def insertParses(self, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKey="origId", conllFormat=None, splitting=True):
        corpusTree, corpusRoot = self.getCorpus(input)
        if not os.path.exists(parseDir):
            raise Exception("Cannot find parse input '" + str(parseDir) + "'")
        if not os.path.isdir(parseDir):
            raise Exception("Parse input '" + str(parseDir) + "' is not a directory")
        if extensions == None:
            extensions = ["ptb", "sd", "conll", "conllx", "conllu"]
        print >> sys.stderr, "Inserting parses from file types:", extensions
        counts = defaultdict(int)
        files = self.readParses(parseDir, extensions, subDirs, counts)
        documents = [x for x in corpusRoot.findall("document")]
        counter = ProgressCounter(len(documents), "Parse Insertion")
        typeCounts = {x:defaultdict(int) for x in extensions}
        typeCounts["sentence-splitting"] = defaultdict(int)
        for document in corpusRoot.findall("document"):
            counts["document"] += 1
            docMatchValue = document.get(docMatchKey)
            counter.update(1, "Inserting parses for (" + document.get("id") + "/" + str(docMatchValue) + "): ")
            if docMatchValue not in files:
                continue
            counts["document-match"] += 1
            sentences = [x for x in self.getSentences(document, skipParsed=skipParsed)]
            for ext in extensions:
                if ext not in files[docMatchValue]:
                    continue
                counts[ext + "-match"] += 1
                if ext == "ptb":
                    sentObjs = self.readPennTrees(files[docMatchValue][ext])
                    sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
                    counts = self.insertElements(sentObjs, sentences, parseName, counts=typeCounts[ext])
                elif ext == "conll":
                    sentRows = self.readCoNLL(files[docMatchValue][ext], conllFormat=conllFormat)
                    sentObjs = self.processCoNLLSentences(sentRows)
                    sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
                    self.insertElements(sentObjs, sentences, parseName, "LINKED", counts=typeCounts[ext])
                elif ext == "sd":
                    sentObjs = self.readDependencies(files[docMatchValue][ext])
                    self.insertElements(sentObjs, sentences, parseName, parseName, counts=typeCounts[ext])
        print >> sys.stderr, "Counts", dict(counts)
        for ext in extensions:
            if len(typeCounts[ext]) > 0:
                print >> sys.stderr, "Counts for type '" + ext + "':", dict(typeCounts[ext])
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
    
    ParseConverter.insertCls(options.parseDir, options.input, options.output, parseName=options.parse, debug=options.debug)        