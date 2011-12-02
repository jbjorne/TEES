import sys, os
import itertools
import STFormat.STTools
import STFormat.ConvertXML
import Tools.GeniaSentenceSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import Tools.BANNER
from Detector import Detector
import InteractionXML.DivideSets

class Preprocessor(Detector):
    def __init__(self):
        Detector.__init__(self)
        # Settings
        self.STATE_PREPROCESS = "PREPROCESS"
        self.namedEntityElementName = "entity"
        self.requireEntities = False
        self.parseName = "McClosky"
        self._preprocessingSteps = ["CONVERT", "SPLIT-SENTENCES", "NER", "PARSE", "CONVERT-PARSE", "SPLIT-NAMES", "FIND-HEADS", "DIVIDE-SETS"]
        self._intermediateFiles = {}
        for step in self._preprocessingSteps[:-1]:
            self._intermediateFiles[step] = None
        self.setIntermediateFile("CONVERT", "documents.xml")
        self.setIntermediateFile("SPLIT-SENTENCES", "sentences.xml")
        self.setIntermediateFile("NER", "ner.xml")
        self.setIntermediateFile("PARSE", "parse.xml")
        self.setIntermediateFile("CONVERT-PARSE", "converted-parse.xml")
        self.setIntermediateFile("SPLIT-NAMES", "split-names.xml")
        self.setIntermediateFile("FIND-HEADS", "heads.xml")
        # Tools
        self.sentenceSplitter = Tools.GeniaSentenceSplitter
        self.namedEntityRecognizer = Tools.BANNER
        self.parser = Tools.CharniakJohnsonParser
        self.parseConverter = Tools.StanfordParser
        self.proteinNameSplitter = ProteinNameSplitter
        self.headDetector = FindHeads
    
    def setIntermediateFile(self, step, filename):
        assert step in self._preprocessingSteps, (step, self._preprocessingSteps)
        self._intermediateFiles[step] = filename
    
    def setNoIntermediateFiles(self):
        for key in self._intermediateFiles.keys():
            self._intermediateFiles[key] = None
    
    def getCurrentOutput(self):
        if self._intermediateFiles[self.select.currentStep] != None:
            return os.path.join(self.outDir, corpusName + "-" + self._intermediateFiles[self.select.currentStep])
        else:
            return None
    
    def process(self, source, corpusName, outDir, sourceDataSetNames=None, fromStep=None, toStep=None, omitSteps=None):
        self.initVariables(source=source, sourceDataSetNames=sourceDataSetNames, outDir=outDir, corpusName=corpusName, xml=source)
        self.enterState(self.STATE_PREPROCESS, self._preprocessingSteps, fromStep, toStep, omitSteps)
        if self.checkStep("CONVERT"):
            if os.path.isdir(source):
                self.xml = self.convert(self.source, self.sourceDataSetNames, output=self.getCurrentOutput())
            else:
                print >> sys.stderr, "Processing source as interaction XML"
        if self.checkStep("NER"):
            self.detectEntities(self.xml, self.namedEntityElementName, output=self.getCurrentOutput())
        if self.checkStep("SPLIT-SENTENCES"):
            self.splitSentences(self.xml, output=self.getCurrentOutput())
        if self.checkStep("PARSE"):
            self.parseCJ(self.xml, output=self.getCurrentOutput())
        if self.checkStep("CONVERT-PARSE"):
            self.stanfordConvert(self.xml, self.requireEntities, output=self.getCurrentOutput())
        if self.checkStep("SPLIT-NAMES"):
            self.splitNames(self.xml, output=self.getCurrentOutput())
        if self.checkStep("FIND-HEADS"):
            self.findHeads(self.xml, output=self.getCurrentOutput())
        if self.checkStep("DIVIDE-SETS"):
            self.splitNames(self.xml, self.corpusName + "-")
        xml = self.xml # state-specific member variable self.xml will be removed when exiting state
        self.exitState()
        if self.state == None:
            return xml
    
    def convert(self, dataSetDirs, dataSetNames=None, output=None):
        print >> sys.stderr, "Converting ST-format to Interaction XML"
        documents = []
        if dataSetNames == None: dataSetNames = []
        for dataSetDir, dataSetName in itertools.izip_longest(dataSetDirs, dataSetNames, fillValue=None):
            print >> sys.stderr, "Reading", dataSetDir, "set,",
            docs = STFormat.STTools.loadSet(dataSetDir, dataSetName)
            print >> sys.stderr, len(docs), "documents"
            documents.extend(docs)
        return STFormat.ConvertXML.toInteractionXML(documents, corpusName, output)
    
    def splitSentences(self, xml, output=None):
        print >> sys.stderr, "Splitting document-elements to sentence-elements"
        self.sentenceSplitter.makeSentences(xml, output)
    
    def detectEntities(self, xml, elementName="entity", output=None):
        print >> sys.stderr, "Running named entity recognition"
        self.namedEntityRecognizer.run(input, output=None, elementName=self.namedEntityElementName)
    
    def parseCJ(self, xml, parseName="McClosky", requireEntities=False, output=None):
        print >> sys.stderr, "Parsing sentence-elements"
        self.parser.parse(xml, output, tokenizationName=None, parseName=parseName, requireEntities=requireEntities)
    
    def stanfordConvert(self, xml, parseName="McClosky", output=None):
        print >> sys.stderr, "Runnign Stanford Conversion on parse", parseName
        self.parseConverter.convertXML(parseName, xml, output)
    
    def splitNames(self, input, parseName, newParseName=None, output=None):
        print >> sys.stderr, "Splitting multiple-named-entity tokens"
        if newParseName == None:
            newParseName = "split-" + parseName
        self.proteinNameSplitter.mainFunc(xml, output, parseName, parseName, newParseName, newParseName)
    
    def findHeads(self, parseName="split-McClosky", output=None):
        print >> sys.stderr, "Detecting entity syntactic heads"
        xml = self.headDetector.findHeads(xml, parseName, tokenization=None, output=output, removeExisting=True)
    
    def divideSets(self, input, outputStem):
        print >> sys.stderr, "Dividing into sets"
        outDir, outputStem = os.path.split(outputStem)
        InteractionXML.DivideSets.processCorpus(input, outDir, outputStem, ".xml")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-i", "--inputNames", default=None, dest="input", help="")
    optparser.add_option("-c", "--corpus", default=None, dest="corpus", help="corpus name")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-f", "--fromStep", default=None, dest="fromStep", help="")
    optparser.add_option("-t", "--toStep", default=None, dest="toStep", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("-n", "--noLog", default=True, action="store_false", dest="log", help="")
    (options, args) = optparser.parse_args()
    if options.omitSteps != None:
        options.omitSteps = options.omitSteps.split(",")
    
    cwd = os.getcwd()
    options.output = os.path.abspath(options.output)
    if not os.path.exists(options.output): os.makedirs(options.output)
    os.chdir(options.output)
    if not options.noLog:
        log(False, False, os.path.join(options.output, options.corpus + "-log.txt"))
    preprocessor = Preprocessor()
    preprocessor.process(options.input, options.corpus, options.output, options.fromStep, options.toStep, options.omitSteps)
    os.chdir(cwd)
