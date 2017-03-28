import sys, os
from collections import defaultdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
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
            self.splitSentences(sentObjs, document, counts=counts)
        return [x for x in document.findall("sentence")]
    
    def prepareDocuments(self, corpusRoot, files, conllFormat=None, counts=None):
        print >> sys.stderr, "Generating document elements from the parses"
        docNames = sorted(files.keys())
        corpusName = corpusRoot.get("source", "CORPUS")
        #parseExtensions = set(("ptb", "conll", "conllx", "conllu"))
        counter = ProgressCounter(len(docNames), "Document Generation")
        for i in range(len(docNames)):
            docName = docNames[i]
            counter.update(1, "Making document element for document '" + str(docName) + "': ")
            #filePaths = files[docName]
            extensions = sorted(files[docName].keys())
            sentObjs = self.readParse(files[docName][extensions[0]], conllFormat)
            sentTexts = []
            for sentObj in sentObjs:
                if "tokens" in sentObj:
                    sentTexts.append(" ".join([x["text"] for x in sentObj["tokens"]]))
            docText = " ".join(sentTexts)
            ET.SubElement(corpusRoot, "document", id=corpusName + ".d" + str(i), origId=docName, text=docText)
        return [x for x in corpusRoot.findall("document")]
        
    def readParse(self, filePath, conllFormat=None):
        ext = filePath.rsplit(".", 1)[-1]
        if ext == "ptb":
            sentObjs = self.readPennTrees(filePath)
        elif ext in ("conll", "conllx", "conllu"):
            sentRows = self.readCoNLL(filePath, conllFormat=conllFormat)
            sentObjs = self.processCoNLLSentences(sentRows)
        elif ext == "sd":
            sentObjs = self.readDependencies(filePath)
        elif ext == "epe":
            sentObjs = self.readEPE(filePath)
        else:
            raise Exception("Unknown extension '" + str(ext) + "'")
        return sentObjs
    
    def insertParse(self, document, sentences, filePath, parseName, splitting, typeCounts, conllFormat=None):
        ext = filePath.rsplit(".", 1)[-1]
        sentObjs = self.readParse(filePath, conllFormat)      
        if ext == "ptb":
            sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
            self.insertElements(sentObjs, sentences, parseName, counts=typeCounts[ext])
        elif ext in ("conll", "conllx", "conllu", "epe"):
            sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
            self.insertElements(sentObjs, sentences, parseName, "LINKED", counts=typeCounts[ext])
        elif ext == "sd":
            self.insertElements(sentObjs, sentences, parseName, parseName, counts=typeCounts[ext])
        else:
            raise Exception("Unknown extension '" + str(ext) + "'")
            
    def insertParses(self, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKeys=None, conllFormat=None, splitting=True):
        corpusTree, corpusRoot = self.getCorpus(input)
        if not os.path.exists(parseDir):
            raise Exception("Cannot find parse input '" + str(parseDir) + "'")
        if not os.path.isdir(parseDir):
            raise Exception("Parse input '" + str(parseDir) + "' is not a directory")
        if extensions == None:
            extensions = ["ptb", "sd", "conll", "conllx", "conllu", "epe"]
        if docMatchKeys == None:
            docMatchKeys = ["origId", "pmid", "id"]
        elif isinstance(docMatchKeys, basestring):
            docMatchKeys = docMatchKeys.split(",")
        print >> sys.stderr, "Inserting parses from file types:", extensions
        counts = defaultdict(int)
        files = self.readParses(parseDir, extensions, subDirs, counts)
        typeCounts = {x:defaultdict(int) for x in extensions}
        # Make document elements if needed
        documents = [x for x in corpusRoot.findall("document")]
        if len(documents) == 0:
            typeCounts["document-generation"] = defaultdict(int)
            documents = self.prepareDocuments(corpusRoot, files)
        counter = ProgressCounter(len(documents), "Parse Insertion")
        # Insert parses and make sentence elements if needed
        typeCounts["sentence-splitting"] = defaultdict(int)
        print >> sys.stderr, "Inserting parses for", len(documents), "documents"
        for document in documents:
            counts["document"] += 1
            matchFound = False
            for docMatchValue in [document.get(x) for x in docMatchKeys if document.get(x) != None]:
                if docMatchValue in files:
                    if matchFound:
                        raise Exception("Multiple matching parses for document " + str(document.attrib) + " using keys " + str(docMatchKeys))
                    matchFound = True
                    counter.update(1, "Inserting parses for (" + document.get("id") + "/" + str(docMatchValue) + "): ")
                    counts["document-match"] += 1
                    sentences = [x for x in self.getSentences(document, skipParsed=skipParsed)]
                    for ext in extensions:
                        if ext not in files[docMatchValue]:
                            continue
                        counts[ext + "-match"] += 1
                        self.insertParse(document, sentences, files[docMatchValue][ext], parseName, splitting, typeCounts, conllFormat)
            if not matchFound:
                counts["document-no-match"] += 1
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