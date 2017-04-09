import sys, os
import itertools
import types
from Tools.ParseExporter import ParseExporter
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Utils.STFormat.STTools
import Utils.STFormat.ConvertXML
import Utils.STFormat.Equiv
import Utils.ElementTreeUtils as ETUtils
import Tools.GeniaSentenceSplitter
from Tools.BLLIPParser import BLLIPParser
from Tools.StanfordParser import StanfordParser
from Tools.SyntaxNetParser import SyntaxNetParser
from Tools.ParseConverter import ParseConverter
import Tools.BANNER
from ToolChain import ToolChain
from Detectors.StructureAnalyzer import StructureAnalyzer
import Utils.InteractionXML.DivideSets
import Utils.ProteinNameSplitter as ProteinNameSplitter
import Utils.FindHeads as FindHeads
#from Test.Pipeline import log
import Utils.Stream as Stream
import Utils.InteractionXML.DeleteElements
import Utils.InteractionXML.DeleteAttributes
import Utils.InteractionXML.MergeSentences
import Utils.InteractionXML.MergeSets
#import Utils.InteractionXML.ExportParse
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import Utils.Settings as Settings
import Utils.Convert.convertBioNLP

def clsStep(cls, method):
    return lambda *args, **kwargs: getattr(cls(), method)(*args, **kwargs)
    #return lambda *args, **kwargs: method(cls(), *args, **kwargs)

class Preprocessor(ToolChain):
    def __init__(self, steps=["PRESET-PREPROCESS-BIO"], parseName="McCC", requireEntities=False):
        #if constParser == "None": constParser = None
        #if depParser == "None": depParser = None
        #assert constParser in ("BLLIP", "BLLIP-BIO", "STANFORD", None), constParser
        #assert depParser in ("STANFORD", "STANFORD-CONVERT", "SYNTAXNET", None), depParser
        #self.constParser = constParser
        #self.depParser = depParser
        self.requireEntities = requireEntities
        self.parseName = parseName
        ToolChain.__init__(self)
        self.modelParameterStringName = "preprocessorParams"
        
        self.initSteps()
        self.initPresets()
        if steps != None:
            self.defineSteps(steps)
    
    def initSteps(self):
        self.initStepGroup("Corpus Conversion")
        self.initStep("CONVERT-BIONLP", Utils.Convert.convertBioNLP.convert, {"corpora":None, "outDir":None, "downloadDir":None, "redownload":False, "makeIntermediateFiles":False, "evaluate":False, "processEquiv":True, "analysisMode":"AUTO", "debug":False, "preprocessorSteps":None, "preprocessorParameters":None, "logPath":"AUTO"}, "convert-bionlp.xml", {"input":"corpora", "output":"outDir"})
        self.initStep("DOWNLOAD-CORPUS", Utils.Convert.convertBioNLP.convertCorpus, {"corpus":None, "outDir":None, "downloadDir":None, "redownload":False, "makeIntermediateFiles":False, "evaluate":False, "processEquiv":True, "analysisMode":"SKIP", "debug":False, "preprocessorSteps":None, "preprocessorParameters":None}, "download-bionlp.xml", {"input":"corpus", "output":"outDir"})
        self.initStepGroup("Loading")
        self.initStep("LOAD", self.load, {"dataSetNames":None, "corpusName":None, "extensions":None}, "load.xml")
        self.initStep("DOWNLOAD-PUBMED", self.downloadPubmed, {}, "pubmed.xml")
        self.initStep("CONVERT", self.convert, {"dataSetNames":None, "corpusName":None}, "convert.xml")
        self.initStep("MERGE-SETS", Utils.InteractionXML.MergeSets.mergeSets, {"corpusDir":None}, "merged-sets.xml")
        self.initStepGroup("Pre-parsing")
        self.initStep("REMOVE-HEADS", Utils.InteractionXML.DeleteAttributes.processCorpus, {"rules":{"entity":["headOffset"]}}, "remove-heads.xml")
        self.initStep("REMOVE-ANALYSES", Utils.InteractionXML.DeleteElements.processCorpus, {"rules":{"analyses":{}}, "reverse":False}, "remove-analyses.xml")
        self.initStep("MERGE-SENTENCES", Utils.InteractionXML.MergeSentences.mergeSentences, {}, "merge-sentences.xml")
        self.initStep("GENIA-SPLITTER", Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "split-sentences.xml")
        self.initStep("BANNER", Tools.BANNER.run, {"elementName":"entity", "processElement":"sentence", "debug":False, "splitNewlines":True}, "banner.xml")
        self.initStepGroup("Constituency Parsing")
        self.initStep("BLLIP-BIO", clsStep(BLLIPParser, "parse"), {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False, "pathBioModel":"AUTO"}, "bllip-bio-parse.xml")
        self.initStep("BLLIP", clsStep(BLLIPParser, "parse"), {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False, "pathBioModel":None}, "bllip-parse.xml")
        self.initStep("STANFORD-CONST", clsStep(StanfordParser, "parse"), {"parserName":self.parseName, "debug":False, "action":"penn"}, "stanford-const-parse.xml")
        self.initStepGroup("Dependency Parsing")
        self.initStep("STANFORD-DEP", clsStep(StanfordParser, "parse"), {"parserName":self.parseName, "debug":False, "action":"dep", "outputFormat":None}, "stanford-dependencies.xml")
        self.initStep("STANFORD-CONVERT", clsStep(StanfordParser, "parse"), {"parserName":self.parseName, "debug":False, "action":"convert", "outputFormat":None}, "stanford-convert-dependencies.xml")
        self.initStep("SYNTAXNET", clsStep(SyntaxNetParser, "parse"), {"parserName":self.parseName, "debug":False, "modelDir":None}, "syntaxnet-dependencies.xml")
        self.initStepGroup("Alternative Parsing")
        self.initStep("IMPORT-PARSE", clsStep(ParseConverter, "insertParses"), {"parseDir":None, "debug":False, "extensions":None, "subDirs":None, "docMatchKeys":None, "conllFormat":None, "splitting":True, "unescapeFormats":"all"}, "import-parse.xml")
        #self.allSteps["IMPORT-PARSE", clsStep(ParseConverter, ParseConverter.insertParses), {"parseDir":None, "debug":False}, "import-parse.xml"]
        #self.allSteps["IMPORT-PARSE", lambda *args, **kwargs: ParseConverter().insertParses(*args, **kwargs), {"parseDir":None, "debug":False}, "import-parse.xml"]        
        self.initStepGroup("Post-parsing")
        self.initStep("SPLIT-NAMES", ProteinNameSplitter.mainFunc, {"parseName":self.parseName, "removeOld":True}, "split-names.xml")
        self.initStep("FIND-HEADS", FindHeads.findHeads, {"parse":self.parseName, "removeExisting":True}, "heads.xml")
        self.initStep("REMOVE-DOCUMENT-TEXTS", Utils.InteractionXML.DeleteAttributes.processCorpus, {"rules":{"document":["text"]}}, "remove-document-texts.xml")
        self.initStep("ANALYZE-STRUCTURE", clsStep(StructureAnalyzer, "analyze"), {}, None)
        self.initStepGroup("Saving")
        self.initStep("DIVIDE-SETS", self.divideSets, {"saveCombined":False}, None)
        self.initStep("SAVE", self.save, {}, None)
        self.initStep("EXPORT", self.export, {"formats":None, "exportIds":None}, None)
        self.initStep("EXPORT-STFORMAT", Utils.STFormat.ConvertXML.toSTFormat, {"outputTag":"a2", "useOrigIds":False, "debug":False, "skipArgs":[], "validate":True, "writeExtra":False, "allAsRelations":False, "exportIds":None}, None)
    
    def initPresets(self):
        self.presets["PRESET-CONVERT-PARSE"] = ["LOAD", "EXPORT"]
        self.presets["PRESET-REPARSE-BIO-CORPUS"] = ["MERGE-SETS", "REMOVE-ANALYSES", "REMOVE-HEADS", "BLLIP-BIO", "STANFORD-CONVERT", "FIND-HEADS", "SPLIT-NAMES", "DIVIDE-SETS"]
        #self.presets["PRESET-PREPROCESS-BIO"] = ["CONVERT", "GENIA-SPLITTER", "BANNER", "BLLIP-BIO", "STANFORD-CONVERT", "SPLIT-NAMES", "FIND-HEADS", "DIVIDE-SETS"]
        #self.presets["PRESET-PARSE-BIO"] = ["CONVERT", "GENIA-SPLITTER", "BLLIP-BIO", "STANFORD-CONVERT", "SPLIT-NAMES", "FIND-HEADS", "DIVIDE-SETS"]
        #self.presets["PRESET-INSERT-PARSE"] = ["CONVERT", "REMOVE-ANALYSES", "IMPORT-PARSE", "DIVIDE-SETS"]
    
    def getHelpString(self):
        s = "==========" + " Available preprocessor steps " + "==========" + "\n"
        groupIndex = -1
        for step in self.allStepsList:
            if step["group"] != groupIndex:
                groupIndex = step["group"]
                #print >> sys.stderr, "*", preprocessor.groups[groupIndex], "*"
                s += "[" + self.groups[groupIndex] + "]" + "\n"
            s += " " + step["name"] + ": " + str(step["argDict"]) + "\n"
        s += "==========" + "Available preprocessor presets" + "==========" + "\n"
        for name in sorted(self.presets.keys()):
            s += name + ": " + ",".join(self.presets[name]) + "\n"
        return s
    
#     def getDefaultSteps(self):
#         steps = []
#         steps.append( ("CONVERT", self.convert, {"dataSetNames":None, "corpusName":None}, "documents.xml") )
#         steps.append( ("SPLIT-SENTENCES", Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "sentences.xml") )
#         steps.append( ("NER", Tools.BANNER.run, {"elementName":"entity", "processElement":"sentence", "debug":False, "splitNewlines":True}, "ner.xml") )
#         self.addParsingSteps(steps)
#         steps.append( ("SPLIT-NAMES", ProteinNameSplitter.mainFunc, {"parseName":self.parseName, "removeOld":True}, "split-names.xml") )
#         steps.append( ("FIND-HEADS", FindHeads.findHeads, {"parse":self.parseName, "removeExisting":True}, "heads.xml") )
#         steps.append( ("DIVIDE-SETS", self.divideSets, {"saveCombined":False}, "dummy.xml") )
#         return steps
#     
#     def addParsingSteps(self, steps):
#         # Add the constituency parser
#         if self.constParser == "BLLIP-BIO":
#             steps.append( (self.constParser + "-CONST", BLLIPParser.parseCls, {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False, "pathBioModel":"AUTO"}, "parse.xml") )
#         elif self.constParser == "BLLIP":
#             steps.append( (self.constParser + "-CONST", BLLIPParser.parseCls, {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False, "pathBioModel":None}, "parse.xml") )
#         elif self.constParser == "STANFORD":
#             steps.append( (self.constParser + "-CONST", StanfordParser.parseCls, {"parserName":self.parseName, "debug":False, "action":"penn"}, "parse.xml") )
#         # Add the dependency parser
#         if self.depParser == "STANFORD":
#             steps.append( (self.depParser + "-DEP", StanfordParser.parseCls, {"parserName":self.parseName, "debug":False, "action":"dep", "outputFormat":None}, "dependencies.xml") )
#         elif self.depParser == "STANFORD-CONVERT":
#             steps.append( (self.depParser + "-DEP", StanfordParser.parseCls, {"parserName":self.parseName, "debug":False, "action":"convert", "outputFormat":None}, "dependencies.xml") )
#         elif self.depParser == "SYNTAXNET":
#             steps.append( (self.depParser + "-DEP", SyntaxNetParser.parseCls, {"parserName":self.parseName, "debug":False, "modelDir":None}, "dependencies.xml") )
    
    def process(self, source, output=None, parameters=None, model=None, fromStep=None, toStep=None, omitSteps=None, logPath=None):
        if logPath == "AUTO":
            logPath = os.path.join(output.rstrip("/").rstrip("\\") + "-log.txt")
        if logPath not in (None, "None"):
            if not os.path.exists(os.path.dirname(logPath)):
                os.makedirs(os.path.dirname(logPath))
            Stream.openLog(logPath)
        print >> sys.stderr, "Preprocessor steps:", [x["name"] for x in self.steps]
        if len(self.steps) == 0:
            raise Exception("No preprocessing steps defined")
        #if omitSteps != None and((type(omitSteps) in types.StringTypes and omitSteps == "CONVERT") or "CONVERT" in omitSteps):
        #    raise Exception("Preprocessor step 'CONVERT' may not be omitted")
        #if isinstance(source, basestring) and os.path.basename(source).isdigit(): # PMID
        #    print >> sys.stderr, "Preprocessing PubMed abstract", os.path.basename(source)
        #    source = Utils.Download.getPubMed(int(source))   
        # Initialize variables and save existing default values
        #self.intermediateFileTag = corpusName
        #parameters = self.getParameters(parameters, model)
        #parameters["CONVERT.dataSetNames"] = sourceDataSetNames
        #parameters["CONVERT.corpusName"] = corpusName
        #convertSetNames = self.stepArgs("CONVERT")["dataSetNames"]
        #convertCorpusName = self.stepArgs("CONVERT")["corpusName"]
        #self.stepArgs("CONVERT")["dataSetNames"] = sourceDataSetNames
        #self.stepArgs("CONVERT")["corpusName"] = corpusName
        # Run the tool chain
        xml = ToolChain.process(self, source, output, parameters, model, fromStep, toStep, omitSteps)
        # Reset variables to saved default values
        #self.stepArgs("CONVERT")["dataSetNames"] = convertSetNames
        #self.stepArgs("CONVERT")["corpusName"] = convertCorpusName
        return xml
    
    ###########################################################################
    # Loading Steps
    ###########################################################################
    
    def load(self, input, dataSetNames=None, corpusName=None, output=None, extensions=None):
        if isinstance(input, basestring) and input.isdigit():
            return self.downloadPubmed(input, output)
        elif isinstance(input, basestring) and (os.path.isdir(input) or input.endswith(".tar.gz") or input.endswith(".txt") or "," in input):
            return self.convert(input, dataSetNames, corpusName, output, extensions=extensions)
        elif isinstance(input, basestring) and not os.path.exists(input):
            fullPath = os.path.join(Settings.CORPUS_DIR, input)
            print >> sys.stderr, "Loading installed corpus from", fullPath
            if os.path.exists(fullPath):
                return ETUtils.ETFromObj(fullPath)
            else:
                raise Exception("Cannot find input '" + str(input) + "'")
        else:
            print >> sys.stderr, "Processing source as interaction XML"
            return ETUtils.ETFromObj(input)
        
    def downloadPubmed(self, input, output=None):
        assert isinstance(input, basestring) and input.isdigit() # PMID
        print >> sys.stderr, "Preprocessing PubMed abstract", input
        txtPath = Utils.Download.getPubMed(int(input))
        documents = Utils.STFormat.STTools.loadSet(txtPath)
        return Utils.STFormat.ConvertXML.toInteractionXML(documents, "PubMed", output)
    
    def getSourceDirs(self, input, dataSetNames=None):
        # Get input file (or files)
        inputDirs = input
        if type(inputDirs) in types.StringTypes:
            dataSetDirs = inputDirs.split(",")
        # Get the list of "train", "devel" etc names for these sets
        if dataSetNames == None: 
            dataSetNames = []
        elif type(dataSetNames) in types.StringTypes:
            dataSetNames = dataSetNames.split(",")
        dirs = []
        for dataSetDir, dataSetName in itertools.izip_longest(dataSetDirs, dataSetNames, fillvalue=None):
            assert os.path.exists(dataSetDir)
            extensions = set([x.rsplit(".", 1)[-1] for x in os.listdir(dataSetDir) if "." in x])
            dirs.append({"dataset":dataSetName, "path":dataSetDir, "extensions":extensions})
        return dirs
        
    def convert(self, input, dataSetNames=None, corpusName=None, output=None, extensions=None):
        assert isinstance(input, basestring) and (os.path.isdir(input) or input.endswith(".tar.gz") or input.endswith(".txt") or "," in input)
        print >> sys.stderr, "Converting ST-format to Interaction XML"
        sourceDirs = self.getSourceDirs(input, dataSetNames)
        print >> sys.stderr, "Checking source directories:", sourceDirs
        if corpusName == None:
            corpusName = "TEES"
        # Convert all ST format input files into one corpus
        stExtensions = set(["txt", "a1", "a2", "rel"])
        if extensions != None:
            stExtensions = set([x for x in stExtensions if x in extensions])
        documents = []
        xml = None
        for sourceDir in sourceDirs:
            if len(stExtensions.intersection(sourceDir["extensions"])) > 0:
                print >> sys.stderr, "Reading", sourceDir["path"]
                docs = Utils.STFormat.STTools.loadSet(sourceDir["path"], sourceDir["dataset"])
                print >> sys.stderr, len(docs), "documents"
                documents.extend(docs)
        if len(documents) > 0:
            print >> sys.stderr, "Resolving equivalences"
            Utils.STFormat.Equiv.process(documents)
            xml = Utils.STFormat.ConvertXML.toInteractionXML(documents, corpusName, output)
        # Add parse files into the corpus
        parseExtensions = set(["sentences", "tok", "ptb", "sd", "conll", "conllx", "conllu", "epe"])
        if extensions != None:
            parseExtensions = set([x for x in parseExtensions if x in extensions])
        for sourceDir in sourceDirs:
            if len(parseExtensions.intersection(sourceDir["extensions"])) > 0:
                print >> sys.stderr, "Importing parses from", sourceDir["path"], "file types", sorted(sourceDir["extensions"])
                if xml == None:
                    xml = IXMLUtils.makeEmptyCorpus(corpusName)
                xml = ParseConverter().insertParses(sourceDir["path"], xml, output, "McCC", sourceDir["extensions"])
        return xml
    
    ###########################################################################
    # Saving Steps
    ###########################################################################
    
    def export(self, input, output, formats=None, exportIds=None):
        print >> sys.stderr, "Exporting formats:", formats
        exportedParses = False
        if formats == None:
            formats = []
        parseFormats = [x for x in formats if x in ["txt", "sentences", "tok", "ptb", "sd", "conll", "conllx", "conllu", "epe"]]
        stFormats = [x for x in formats if x in ["a1", "a2", "rel"]]
        if len(parseFormats) > 0:
            ParseExporter().export(input, output, "McCC", "McCC", toExport=formats, exportIds=exportIds, clear=True)
            exportedParses = True
        if len(stFormats) > 0:
            Utils.STFormat.ConvertXML.toSTFormat(input, output, files=formats, exportIds=exportIds, clear=not exportedParses)
        return input
    
    def divideSets(self, input, output, saveCombined=False):
        if output != None:
            print >> sys.stderr, "Dividing into sets"
            outDir, outputStem = os.path.split(output)
            if "-dummy.xml" in outputStem:
                outputStem = outputStem.split("-dummy.xml")[0]
            if outputStem.endswith(".xml"):
                outputStem = outputStem[:-4]
            Utils.InteractionXML.DivideSets.processCorpus(input, outDir, outputStem, ".xml", saveCombined=saveCombined)
        else:
            print >> sys.stderr, "No set division"
        return input

# if __name__=="__main__":
#     # Import Psyco if available
#     try:
#         import psyco
#         psyco.full()
#         print >> sys.stderr, "Found Psyco, using"
#     except ImportError:
#         print >> sys.stderr, "Psyco not installed"
#     from optparse import OptionParser, OptionGroup
#     optparser = OptionParser(description="A tool chain for making interaction XML, sentence splitting, NER and parsing")
#     optparser.add_option("-i", "--input", default=None, dest="input", help="The input argument for the first step")
#     optparser.add_option("-o", "--output", default=None, dest="output", help="The output argument for the last step")
#     optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Step parameters, a comma-separated list of 'STEP.parameter=value' definitions")
#     optparser.add_option("-s", "--steps", default=None, dest="steps", help="A comma separated list of steps or presets")
#     shortcuts = OptionGroup(optparser, "Preprocessing step parameter shortcuts", "")
#     shortcuts.add_option("-n", "--dataSetNames", default=None, dest="dataSetNames", help="CONVERT step dataset names")
#     shortcuts.add_option("-c", "--corpus", default=None, dest="corpus", help="CONVERT step XML corpus element name")
#     shortcuts.add_option("--requireEntities", default=False, action="store_true", dest="requireEntities", help="Default setting for parsing steps")
#     #optparser.add_option("--constParser", default="BLLIP-BIO", help="BLLIP, BLLIP-BIO or STANFORD")
#     #optparser.add_option("--depParser", default="STANFORD-CONVERT", help="STANFORD or STANFORD-CONVERT")
#     shortcuts.add_option("--parseName", default="McCC", help="Default setting for parsing steps")
#     shortcuts.add_option("--parseDir", default=None, help="IMPORT-PARSE step parse files directory")
#     optparser.add_option_group(shortcuts)
#     debug = OptionGroup(optparser, "Debug and Process Control Options", "")
#     debug.add_option("-f", "--fromStep", default=None, dest="fromStep", help="Continue from this step")
#     debug.add_option("-t", "--toStep", default=None, dest="toStep", help="Stop at after this step")
#     debug.add_option("--omitSteps", default=None, dest="omitSteps", help="Skip these steps")
#     debug.add_option("--logPath", default="AUTO", dest="logPath", help="AUTO, None, or a path")
#     debug.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="Save an intermediate file for each step")
#     debug.add_option("--debug", default=False, action="store_true", dest="debug", help="Set debug mode for all steps")
#     optparser.add_option_group(debug)
#     (options, args) = optparser.parse_args()
#     
#     #if options.steps == None and not options.listPresets:
#     #    raise Exception("No preprocessing steps defined")
#     if options.steps != None:
#         options.steps = [x.strip() for x in options.steps.split(",")]
#     if options.omitSteps != None:
#         options.omitSteps = options.omitSteps.split(",")
#         
#     preprocessor = Preprocessor(options.steps, options.parseName, options.requireEntities)
#     if options.steps == None:
#         print >> sys.stderr, "==========", "Available preprocessor steps", "=========="
#         groupIndex = -1
#         for step in preprocessor.allStepsList:
#             if step["group"] != groupIndex:
#                 groupIndex = step["group"]
#                 #print >> sys.stderr, "*", preprocessor.groups[groupIndex], "*"
#                 print >> sys.stderr, "[" + preprocessor.groups[groupIndex] + "]"
#             print >> sys.stderr, " ", step["name"] + ": " + str(step["argDict"])
#         print >> sys.stderr, "==========", "Available preprocessor presets", "=========="  
#         for name in sorted(preprocessor.presets.keys()):
#             print >> sys.stderr, name + ": " + ",".join(preprocessor.presets[name])
#     else:
#         #options.constParser = options.constParser if options.constParser != "None" else None
#         #options.depParser = options.depParser if options.depParser != "None" else None
#         
#         #if not options.noLog:
#         #    Stream.openLog(os.path.join(options.output + "-log.txt"))
#             #log(False, True, os.path.join(options.output, options.corpus + "-log.txt"))
#         preprocessor.setArgForAllSteps("debug", options.debug)
#         if preprocessor.hasStep("CONVERT"):
#             preprocessor.stepArgs("CONVERT")["corpusName"] = options.corpus
#             preprocessor.stepArgs("CONVERT")["dataSetNames"] = options.dataSetNames
#         if options.parseDir:
#             preprocessor.stepArgs("IMPORT-PARSE")["parseDir"] = options.parseDir
#         if options.intermediateFiles:
#             preprocessor.setIntermediateFiles(True)
#         #preprocessor.stepArgs("PARSE")["requireEntities"] = options.requireEntities
#         preprocessor.process(options.input, options.output, options.parameters, model=None, fromStep=options.fromStep, toStep=options.toStep, omitSteps=options.omitSteps, logPath=options.logPath)
