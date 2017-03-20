import sys, os
import itertools
import types
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
import Utils.InteractionXML.DivideSets
import Utils.ProteinNameSplitter as ProteinNameSplitter
import Utils.FindHeads as FindHeads
#from Test.Pipeline import log
import Utils.Stream as Stream
import Utils.InteractionXML.DeleteElements

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
    
    def defineSteps(self, steps):
        steps = self.expandPresets(steps)
        for step in steps:
            if step not in self.allSteps:
                raise Exception("Unknown preprocessor step '" + str(step) + "'")
            self.addStep(*([step] + self.allSteps[step]))
    
    def expandPresets(self, steps):
        newSteps = []
        for step in steps:
            if step.startswith("PRESET-"):
                assert step in self.presets
                newSteps.extend(self.presets[step])
            else:
                newSteps.append(step)
        return newSteps
    
    def initSteps(self):
        self.allSteps = {}
        # Pre-parsing steps
        self.allSteps["CONVERT"] = [self.convert, {"dataSetNames":None, "corpusName":None}, "documents.xml"]
        self.allSteps["REMOVE-ANALYSES"] = [Utils.InteractionXML.DeleteElements.processCorpus, {"rules":{"analyses":{}}, "reverse":False}, "remove-analyses.xml"]
        #self.allSteps["REMOVE-SENTENCES"] = [Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "sentences.xml"]
        self.allSteps["GENIA-SPLITTER"] = [Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "sentences.xml"]
        self.allSteps["BANNER"] = [Tools.BANNER.run, {"elementName":"entity", "processElement":"sentence", "debug":False, "splitNewlines":True}, "ner.xml"]
        # Constituency parsing steps
        self.allSteps["BLLIP-BIO"] = [BLLIPParser.parseCls, {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False, "pathBioModel":"AUTO"}, "parse.xml"]
        self.allSteps["BLLIP"] = [BLLIPParser.parseCls, {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False, "pathBioModel":None}, "parse.xml"]
        self.allSteps["STANFORD-CONST"] = [StanfordParser.parseCls, {"parserName":self.parseName, "debug":False, "action":"penn"}, "parse.xml"]
        # Dependency parsing steps
        self.allSteps["STANFORD-DEP"] = [StanfordParser.parseCls, {"parserName":self.parseName, "debug":False, "action":"dep", "outputFormat":None}, "dependencies.xml"]
        self.allSteps["STANFORD-CONVERT"] = [StanfordParser.parseCls, {"parserName":self.parseName, "debug":False, "action":"convert", "outputFormat":None}, "dependencies.xml"]
        self.allSteps["SYNTAXNET"] = [SyntaxNetParser.parseCls, {"parserName":self.parseName, "debug":False, "modelDir":None}, "dependencies.xml"]
        # Parse import steps
        self.allSteps["IMPORT-PARSE"] = [ParseConverter.insertCls, {"parseName":self.parseName, "debug":False}, "import-parse.xml"]        
        # Post-parsing steps
        self.allSteps["SPLIT-NAMES"] = [ProteinNameSplitter.mainFunc, {"parseName":self.parseName, "removeOld":True}, "split-names.xml"]
        self.allSteps["FIND-HEADS"] = [FindHeads.findHeads, {"parse":self.parseName, "removeExisting":True}, "heads.xml"]
        self.allSteps["DIVIDE-SETS"] = [self.divideSets, {"saveCombined":False}, "dummy.xml"]
    
    def initPresets(self):
        self.presets = {}
        self.presets["PRESET-PREPROCESS-BIO"] = ["CONVERT", "GENIA-SPLITTER", "BANNER", "BLLIP-BIO", "STANFORD-CONVERT", "SPLIT-NAMES", "FIND-HEADS", "DIVIDE-SETS"]
        self.presets["PRESET-PARSE-BIO"] = ["CONVERT", "GENIA-SPLITTER", "BLLIP-BIO", "STANFORD-CONVERT", "SPLIT-NAMES", "FIND-HEADS", "DIVIDE-SETS"]
        self.presets["PRESET-INSERT-PARSE"] = ["CONVERT", "REMOVE-ANALYSES", "IMPORT-PARSE", "DIVIDE-SETS"]
    
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
    
    def process(self, source, output, parameters=None, model=None, sourceDataSetNames=None, fromStep=None, toStep=None, omitSteps=None):
        print >> sys.stderr, "Preprocessor steps:", [x[0] for x in self.steps]
        if omitSteps != None and((type(omitSteps) in types.StringTypes and omitSteps == "CONVERT") or "CONVERT" in omitSteps):
            raise Exception("Preprocessor step 'CONVERT' may not be omitted")
        if isinstance(source, basestring) and os.path.basename(source).isdigit(): # PMID
            print >> sys.stderr, "Preprocessing PubMed abstract", os.path.basename(source)
            source = Utils.Download.getPubMed(int(source))   
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
        
    def convert(self, input, dataSetNames=None, corpusName=None, output=None):
        if isinstance(input, basestring) and (os.path.isdir(input) or input.endswith(".tar.gz") or input.endswith(".txt") or "," in input):
            print >> sys.stderr, "Converting ST-format to Interaction XML"
            # Get input file (or files)
            dataSetDirs = input
            documents = []
            if type(dataSetDirs) in types.StringTypes:
                dataSetDirs = dataSetDirs.split(",")
            # Get the list of "train", "devel" etc names for these sets
            if dataSetNames == None: 
                dataSetNames = []
            elif type(dataSetNames) in types.StringTypes:
                dataSetNames = dataSetNames.split(",")
            # Convert all input files into one corpus
            for dataSetDir, dataSetName in itertools.izip_longest(dataSetDirs, dataSetNames, fillvalue=None):
                print >> sys.stderr, "Reading", dataSetDir, "set,",
                docs = Utils.STFormat.STTools.loadSet(dataSetDir, dataSetName)
                print >> sys.stderr, len(docs), "documents"
                documents.extend(docs)
            print >> sys.stderr, "Resolving equivalences"
            Utils.STFormat.Equiv.process(documents)
            if corpusName == None:
                corpusName = "TEES"
            self.xml = Utils.STFormat.ConvertXML.toInteractionXML(documents, corpusName, output)
        else:
            print >> sys.stderr, "Processing source as interaction XML"
            self.xml = ETUtils.ETFromObj(input)
        return self.xml
    
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

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser(description="A tool chain for making interaction XML, sentence splitting, NER and parsing")
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-n", "--inputNames", default=None, dest="inputNames", help="")
    optparser.add_option("-c", "--corpus", default=None, dest="corpus", help="corpus name")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="preprocessing parameters")
    optparser.add_option("-s", "--steps", default=None, dest="steps", help="")
    optparser.add_option("-f", "--fromStep", default=None, dest="fromStep", help="")
    optparser.add_option("-t", "--toStep", default=None, dest="toStep", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--requireEntities", default=False, action="store_true", dest="requireEntities", help="")
    #optparser.add_option("--constParser", default="BLLIP-BIO", help="BLLIP, BLLIP-BIO or STANFORD")
    #optparser.add_option("--depParser", default="STANFORD-CONVERT", help="STANFORD or STANFORD-CONVERT")
    optparser.add_option("--parseName", default="McCC")
    optparser.add_option("--noIntermediateFiles", default=False, action="store_true", dest="noIntermediateFiles", help="")
    optparser.add_option("--listPresets", default=False, action="store_true", dest="listPresets", help="")
    (options, args) = optparser.parse_args()
    
    if options.steps == None and not options.listPresets:
        raise Exception("No preprocessing steps defined")
    if options.steps != None:
        options.steps = [x.strip() for x in options.steps.split(",")]
    if options.omitSteps != None:
        options.omitSteps = options.omitSteps.split(",")
        
    preprocessor = Preprocessor(options.steps, options.parseName, options.requireEntities)
    if options.listPresets:
        for preset in sorted(preprocessor.presets.keys()):
            print >> sys.stderr, preset + ": " + ",".join(preprocessor.presets[preset])
    else:
        #options.constParser = options.constParser if options.constParser != "None" else None
        #options.depParser = options.depParser if options.depParser != "None" else None
        
        if not options.noLog:
            Stream.openLog(os.path.join(options.output + "-log.txt"))
            #log(False, True, os.path.join(options.output, options.corpus + "-log.txt"))
        preprocessor.setArgForAllSteps("debug", options.debug)
        preprocessor.stepArgs("CONVERT")["corpusName"] = options.corpus
        if options.noIntermediateFiles:
            preprocessor.setNoIntermediateFiles()
        #preprocessor.stepArgs("PARSE")["requireEntities"] = options.requireEntities
        preprocessor.process(options.input, options.output, options.parameters, None, options.inputNames, fromStep=options.fromStep, toStep=options.toStep, omitSteps=options.omitSteps)
