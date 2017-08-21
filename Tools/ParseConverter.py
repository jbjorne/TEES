import sys, os
from collections import defaultdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
from Parser import Parser
from Utils.ProgressCounter import ProgressCounter

class ParseConverter(Parser):    
#     @classmethod
#     def insertCls(cls, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKey="origId"):
#         parserObj = cls()
#         parserObj.insertParses(parseDir, input, output, parseName, extensions, subDirs, debug, skipParsed, docMatchKey)
    
    def __init__(self):
        Parser.__init__(self)
        self.allExt = ["tok", "tt", "ptb", "sd", "conll", "conllx", "conllu", "corenlp", "epe"]
    
    def getParseFiles(self, parseDir, extensions, subDirs, counts, extMap=None, origIdType=None):
        files = {}
        if subDirs == None:
            subDirs = ["ptb", "conll", "sd_ccproc"]
        elif isinstance(subDirs, basestring):
            subDirs = subDirs.split(",")
        directories = [parseDir] + [os.path.join(parseDir, x) for x in subDirs]
        for directory in directories:
            fileCounts = defaultdict(int)
            if not os.path.exists(directory):
                continue
            print >> sys.stderr, "Collecting parses from", directory,
            for filename in os.listdir(directory):
                filePath = os.path.join(directory, filename)
                if "." not in filename or os.path.isdir(filePath):
                    continue
                ext = filename.rsplit(".", 1)[-1]
                docName = IXMLUtils.getOrigId(filePath, origIdType)
                if extMap and ext in extMap:
                    ext = extMap[ext]
                if ext not in extensions:
                    fileCounts["skipped:" + ext] += 1
                    continue
                if docName not in files:
                    files[docName] = {}
                if ext in files[docName]:
                    raise Exception("Error, multiple files for extension: " + str((ext, [files[docName][ext], filePath])))
                files[docName][ext] = filePath
                fileCounts[ext] += 1
                counts[ext + "-read"] += 1
            print >> sys.stderr, dict(fileCounts)
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
        #parseExtensions = set(["ptb", "conll", "conllx", "conllu"])
        counter = ProgressCounter(len(docNames), "Document Generation")
        for i in range(len(docNames)):
            docName = docNames[i]
            counter.update(1, "Making document element for document '" + str(docName) + "': ")
            #filePaths = files[docName]
            extensions = sorted(files[docName].keys())
            sentObjs = self.readParse(extensions[0], files[docName][extensions[0]], conllFormat)
            sentTexts = []
            for sentObj in sentObjs:
                if "tokens" in sentObj:
                    sentTexts.append(" ".join([x["text"] for x in sentObj["tokens"]]))
            docText = " ".join(sentTexts)
            ET.SubElement(corpusRoot, "document", id=corpusName + ".d" + str(i), origId=docName, text=docText)
        return [x for x in corpusRoot.findall("document")]
    
    def getUnescapeFormats(self, unescapeFormats=None):
        if unescapeFormats in (None, "None"):
            return set()
        if isinstance(unescapeFormats, basestring):
            if unescapeFormats == "ALL":
                unescapeFormats = set(self.allExt)
            elif unescapeFormats == "AUTO":
                unescapeFormats = set(["ptb", "sd"])
            else:
                unescapeFormats = set(unescapeFormats.split(","))
        for item in unescapeFormats:
            assert item in self.allExt, item
        return unescapeFormats
        
    def readParse(self, ext, filePath, conllFormat=None, unescapeFormats=None, tokenMerging=True, counts=None, sdFailedFormat="empty", posTags=None):
        unescapeFormats = self.getUnescapeFormats(unescapeFormats)
        #ext = filePath.rsplit(".", 1)[-1]
        if ext == "ptb":
            sentObjs = self.readPennTrees(filePath)
        elif ext in ("conll", "conllx", "conllu", "corenlp"):
            sentRows = self.readCoNLL(filePath, conllFormat=conllFormat)
            sentObjs = self.processCoNLLSentences(sentRows, unescaping=ext in unescapeFormats)
        elif ext == "sd":
            sentObjs = self.readStanfordDependencies(filePath, failedFormat=sdFailedFormat)
        elif ext == "epe":
            sentObjs = self.readEPE(filePath, posTags)
        elif ext == "tt":
            sentObjs = self.readTT(filePath)
        elif ext == "tok":
            sentObjs = self.readTok(filePath)
        else:
            raise Exception("Unknown extension '" + str(ext) + "'")
        if tokenMerging:
            self.mergeOverlappingTokens(sentObjs, counts=counts)
        return sentObjs
    
    def insertParse(self, document, sentences, ext, filePath, parseName, splitting, typeCounts, conllFormat=None, unescapeFormats=None, tokenMerging=True, sdFailedFormat="empty", posTags=None):
        #ext = filePath.rsplit(".", 1)[-1]
        extCounts = typeCounts[ext]
        sentObjs = self.readParse(ext, filePath, conllFormat, unescapeFormats=unescapeFormats, tokenMerging=tokenMerging, counts=extCounts, sdFailedFormat=sdFailedFormat, posTags=posTags)      
        if ext == "ptb":
            sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
            self.insertElements(sentObjs, sentences, parseName, counts=extCounts)
        elif ext in ("conll", "conllx", "conllu", "corenlp", "epe"):
            sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
            self.insertElements(sentObjs, sentences, parseName, "LINKED", counts=extCounts)
        elif ext == "sd":
            self.insertElements(sentObjs, sentences, parseName, parseName, counts=extCounts)
        elif ext in ("tt", "tok"):
            sentences = self.prepareSentences(document, sentences, sentObjs, splitting, typeCounts["sentence-splitting"])
            self.insertElements(sentObjs, sentences, parseName, parseName, counts=extCounts)
        else:
            raise Exception("Unknown extension '" + str(ext) + "'")
    
    def insertParses(self, parseDir, input, output=None, parseName="McCC", extensions=None, subDirs=None, debug=False, skipParsed=False, docMatchKeys=None, conllFormat=None, splitting=True, unescapeFormats="AUTO", tokenMerging=True, extMap=None, sdFailedFormat="empty", origIdType=None, posTags=None):
        corpusTree, corpusRoot = self.getCorpus(input)
        if not os.path.exists(parseDir):
            raise Exception("Cannot find parse input '" + str(parseDir) + "'")
        if not os.path.isdir(parseDir):
            raise Exception("Parse input '" + str(parseDir) + "' is not a directory")
        if extensions == None:
            extensions = self.allExt
        elif isinstance(extensions, basestring):
            extensions = extensions.split(",")
        extensions = [x for x in extensions if x in self.allExt]
        unescapeFormats = self.getUnescapeFormats(unescapeFormats)
        if docMatchKeys == None:
            docMatchKeys = ["origId", "pmid", "id"]
        elif isinstance(docMatchKeys, basestring):
            docMatchKeys = docMatchKeys.split(",")
        print >> sys.stderr, "Inserting parses from file types:", extensions
        counts = defaultdict(int)
        files = self.getParseFiles(parseDir, extensions, subDirs, counts, extMap=extMap, origIdType=origIdType)
        typeCounts = {x:defaultdict(int) for x in extensions}
        # Make document elements if needed
        documents = [x for x in corpusRoot.findall("document")]
        if len(documents) == 0:
            typeCounts["document-generation"] = defaultdict(int)
            documents = self.prepareDocuments(corpusRoot, files)
        counter = ProgressCounter(len(files), "Parse Insertion")
        # Insert parses and make sentence elements if needed
        typeCounts["sentence-splitting"] = defaultdict(int)
        print >> sys.stderr, "Inserting parses for", len(files), "out of total", len(documents), "documents"
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
                    for ext in extensions:
                        if ext not in files[docMatchValue]:
                            continue
                        counts[ext + "-match"] += 1
                        sentences = [x for x in self.getSentences(document, skipParsed=skipParsed)]
                        self.insertParse(document, sentences, ext, files[docMatchValue][ext], parseName, splitting, typeCounts, conllFormat, unescapeFormats=unescapeFormats, tokenMerging=tokenMerging, sdFailedFormat=sdFailedFormat, posTags=posTags)
            if not matchFound:
                counts["document-no-match"] += 1
        if len(typeCounts["sentence-splitting"]) > 0:
            print >> sys.stderr, "Sentence Splitting Counts", dict(typeCounts["sentence-splitting"])
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