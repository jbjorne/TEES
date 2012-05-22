import sys, os
import itertools
import types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../CommonUtils")))
import STFormat.STTools
import STFormat.ConvertXML
import STFormat.Equiv
import cElementTreeUtils as ETUtils
import Tools.GeniaSentenceSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import Tools.BANNER
from ToolChain import ToolChain
import InteractionXML.DivideSets
import GeniaChallenge.formatConversion.ProteinNameSplitter as ProteinNameSplitter
import Utils.FindHeads as FindHeads
from Test.Pipeline import log

class Preprocessor(ToolChain):
    def __init__(self):
        ToolChain.__init__(self)
        # Steps
        self.addStep("CONVERT", self.convert, {"dataSetNames":None, "corpusName":None} , "documents.xml")
        self.addStep("SPLIT-SENTENCES", Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "sentences.xml")
        self.addStep("NER", Tools.BANNER.run, {"elementName":"entity", "processElement":"sentence", "debug":False, "splitNewlines":True}, "ner.xml")
        self.addStep("PARSE", Tools.CharniakJohnsonParser.parse, {"parseName":"McCC", "requireEntities":False, "debug":False}, "parse.xml")
        self.addStep("CONVERT-PARSE", Tools.StanfordParser.convertXML, {"parser":"McCC", "debug":False}, "converted-parse.xml")
        self.addStep("SPLIT-NAMES", ProteinNameSplitter.mainFunc, {"parseName":"McCC"}, "split-names.xml")
        self.addStep("FIND-HEADS", FindHeads.findHeads, {"parse":"McCC", "removeExisting":True}, "heads.xml")
        self.addStep("DIVIDE-SETS", self.divideSets, {"outputStem":None, "saveCombined":True})
    
    def preprocess(self, source, corpusName, outDir, sourceDataSetNames=None, fromStep=None, toStep=None, omitSteps=None):
        self.intermediateFileTag = corpusName
        convertSetNames = self.stepArgs("CONVERT")["dataSetNames"]
        convertCorpusName = self.stepArgs("CONVERT")["corpusName"]
        self.stepArgs("CONVERT")["dataSetNames"] = sourceDataSetNames
        self.stepArgs("CONVERT")["corpusName"] = corpusName
        xml = self.process(source, outDir, fromStep, toStep, omitSteps)
        self.stepArgs("CONVERT")["dataSetNames"] = convertSetNames
        self.stepArgs("CONVERT")["corpusName"] = convertCorpusName
        return xml
        
    def convert(self, input, dataSetNames=None, corpusName=None, output=None):
        if os.path.isdir(input) or input.endswith(".tar.gz") or "," in input:
            print >> sys.stderr, "Converting ST-format to Interaction XML"
            dataSetDirs = input
            documents = []
            if type(dataSetDirs) in types.StringTypes:
                dataSetDirs = dataSetDirs.split(",")
            if dataSetNames == None: 
                dataSetNames = []
            elif type(dataSetNames) in types.StringTypes:
                dataSetNames = dataSetNames.split(",")
            for dataSetDir, dataSetName in itertools.izip_longest(dataSetDirs, dataSetNames, fillvalue=None):
                print >> sys.stderr, "Reading", dataSetDir, "set,",
                docs = STFormat.STTools.loadSet(dataSetDir, dataSetName)
                print >> sys.stderr, len(docs), "documents"
                documents.extend(docs)
            print >> sys.stderr, "Resolving equivalences"
            STFormat.Equiv.process(documents)
            self.xml = STFormat.ConvertXML.toInteractionXML(documents, self.intermediateFileTag, output)
        else:
            print >> sys.stderr, "Processing source as interaction XML"
            self.xml = ETUtils.ETFromObj(input)
        return self.xml
    
    def divideSets(self, input, outputStem, saveCombined=True):
        if outputStem != None:
            print >> sys.stderr, "Dividing into sets"
            outDir, outputStem = os.path.split(outputStem)
            InteractionXML.DivideSets.processCorpus(input, outDir, outputStem, ".xml", saveCombined=saveCombined)
        else:
            print >> sys.stderr, "No set division"

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
    optparser.add_option("-n", "--inputNames", default=None, dest="inputNames", help="")
    optparser.add_option("-c", "--corpus", default=None, dest="corpus", help="corpus name")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-f", "--fromStep", default=None, dest="fromStep", help="")
    optparser.add_option("-t", "--toStep", default=None, dest="toStep", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--requireEntities", default=False, action="store_true", dest="requireEntities", help="")
    (options, args) = optparser.parse_args()
    if options.omitSteps != None:
        options.omitSteps = options.omitSteps.split(",")
    
    cwd = os.getcwd()
    options.output = os.path.abspath(options.output)
    if not os.path.exists(options.output): os.makedirs(options.output)
    os.chdir(options.output)
    if not options.noLog:
        log(False, True, os.path.join(options.output, options.corpus + "-log.txt"))
    preprocessor = Preprocessor()
    preprocessor.setArgForAllSteps("debug", options.debug)
    preprocessor.stepArgs("PARSE")["requireEntities"] = options.requireEntities
    preprocessor.preprocess(options.input, options.corpus, options.output, options.inputNames, fromStep=options.fromStep, toStep=options.toStep, omitSteps=options.omitSteps)
    os.chdir(cwd)
