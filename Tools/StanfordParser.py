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
import Tool
from Parser import Parser

class StanfordParser(Parser):
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

    def runStanford(self, input, output, stanfordParserArgs):
        return subprocess.Popen(stanfordParserArgs + [input], stdout=codecs.open(output, "wt", "utf-8"))
    
    @classmethod
    def process(cls, parser, input, output=None, debug=False, reparse=False, stanfordParserDir=None, stanfordParserArgs=None, action="convert"):
        parserObj = cls()
        parserObj.parse(parser, input, output, debug, reparse, stanfordParserDir, stanfordParserArgs)
    
    def _makeStanfordInputFile(self, corpusRoot, workdir, parser, reparse=False, action="convert", debug=False):
        if debug:
            print >> sys.stderr, "Stanford parser workdir", workdir
        stanfordInput = os.path.join(workdir, "input")
        stanfordInputFile = codecs.open(stanfordInput, "wt", "utf-8")
        
        existingCount = 0
        for sentence in corpusRoot.getiterator("sentence"):
            if action == "convert": # Put penn tree lines in input file
                parse = self.getAnalysis(sentence, "parse", {"parser":parser}, "parses")
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
            else: # action in ("penn", "dep")
                stanfordInputFile.write(sentence.get("text").replace("\n", " ").replace("\r", " ").strip() + "\n")
        stanfordInputFile.close()
        if existingCount != 0:
            print >> sys.stderr, "Skipping", existingCount, "already converted sentences."
        return stanfordInput
    
    def _runStanfordProcess(self, stanfordParserArgs, stanfordParserDir, stanfordInput, workdir, action="convert"):
        if stanfordParserArgs == None:
            # not sure how necessary the "-mx500m" option is, and how exactly Java
            # options interact, but adding user defined options from Settings.JAVA
            # after the "-mx500m" hopefully works.
            stanfordParserArgs = Settings.JAVA.split()[0:1] + ["-mx500m"] + Settings.JAVA.split()[1:]
            if action == "convert":
                stanfordParserArgs += ["-cp", "stanford-parser.jar", 
                                      "edu.stanford.nlp.trees.EnglishGrammaticalStructure", 
                                      "-encoding", "utf8", "-CCprocessed", "-keepPunct", "-treeFile"]
                print >> sys.stderr, "Running Stanford conversion"
            else:
                stanfordParserArgs += ["-cp", "./*",
                                      "edu.stanford.nlp.parser.lexparser.LexicalizedParser", 
                                      "-outputFormat", "typedDependencies" if action == "dep" else "penn",
                                      "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"]
                print >> sys.stderr, "Running Stanford parsing for target", action
        print >> sys.stderr, "Stanford tools at:", stanfordParserDir
        print >> sys.stderr, "Stanford tools arguments:", " ".join(stanfordParserArgs)
        # Run Stanford parser
        return runSentenceProcess(self.runStanford, stanfordParserDir, stanfordInput, 
            workdir, True, "StanfordParser", "Stanford (" + action + ")", timeout=600,
            outputArgs={"encoding":"latin1", "errors":"replace"},
            processArgs={"stanfordParserArgs":stanfordParserArgs})
        
    def parse(self, parser, input, output=None, debug=False, reparse=False, stanfordParserDir=None, stanfordParserArgs=None, action="convert"):
        #global stanfordParserDir, stanfordParserArgs
        assert action in ("convert", "penn", "dep")
        if stanfordParserDir == None:
            stanfordParserDir = Settings.STANFORD_PARSER_DIR
        
        corpusTree, corpusRoot = self.getCorpus(input)
        workdir = tempfile.mkdtemp()
        stanfordInput = self._makeStanfordInputFile(corpusRoot, workdir, parser, reparse, action, debug)
        stanfordOutput = self._runStanfordProcess(stanfordParserArgs, stanfordParserDir, stanfordInput, workdir, action)
        if action == "convert":
            self.insertConversion(corpusRoot, stanfordOutput, workdir, parser, reparse, debug)
        
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        return corpusTree
    
    def insertConversion(self, corpusRoot, stanfordOutput, workdir, parser, reparse, debug):
        #stanfordOutputFile = codecs.open(stanfordOutput, "rt", "utf-8")
        #stanfordOutputFile = codecs.open(stanfordOutput, "rt", "latin1", "replace")
        stanfordOutputFile = codecs.open(stanfordOutput, "rt", "utf-8") 
        # Get output and insert dependencies
        parseTimeStamp = time.strftime("%d.%m.%y %H:%M:%S")
        print >> sys.stderr, "Stanford time stamp:", parseTimeStamp
        noDepCount = 0
        failCount = 0
        sentenceCount = 0
        for document in corpusRoot.findall("document"):
            for sentence in document.findall("sentence"):
                # Get parse
                parse = self.getAnalysis(sentence, "parse", {"parser":parser}, "parses")
                if parse == None:
                    parse = self.addAnalysis(sentence, "parse", "parses")
                    parse.set("parser", "None")
                if reparse:
                    assert len(parse.findall("dependency")) == 0
                elif len(parse.findall("dependency")) > 0: # don't reparse
                    continue
                if parse.get("pennstring") in (None, ""):
                    parse.set("stanford", "no_penn")
                    continue
                parse.set("stanfordSource", "TEES") # parser was run through this wrapper
                parse.set("stanfordDate", parseTimeStamp) # links the parse to the log file
                # Get tokens
                tokenization = self.getAnalysis(sentence, "tokenization", {"tokenizer":parse.get("tokenizer")}, "tokenizations")
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
                deps = self.insertDependencies(stanfordOutputFile, parse, tokenByIndex, (sentence.get("id"), origId))
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
    
    def insertParse(self, sentence, stanfordOutputFile, parser, extraAttributes={}, skipExtra=0):
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
        deps = self.insertDependencies(stanfordOutputFile, parse, tokenByIndex, (sentence.get("id"), sentence.get("origId")), skipExtra=skipExtra)
        if len(deps) == 0:
            parse.set("stanford", "no_dependencies")
        else:
            parse.set("stanford", "ok")
        return True
    
    def insertParses(self, input, parsePath, output=None, parseName="McCC", extraAttributes={}, skipExtra=0):
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
                    if not self.insertParse(sentence, f, parseName, extraAttributes={}, skipExtra=skipExtra):
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
    
    parser = StanfordParser()
    if options.install:
        parser.install(options.installDir, options.downloadDir, redownload=options.redownload)
    else:
        parser.convertXML(input=options.input, output=options.output, parser=options.parse, debug=options.debug, reparse=options.reparse)
        