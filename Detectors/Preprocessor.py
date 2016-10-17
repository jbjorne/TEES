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
import Tools.BANNER
from ToolChain import ToolChain
import Utils.InteractionXML.DivideSets
import Utils.ProteinNameSplitter as ProteinNameSplitter
import Utils.FindHeads as FindHeads
#from Test.Pipeline import log
import Utils.Stream as Stream

class Preprocessor(ToolChain):
    def __init__(self, constParser="BLLIP-BIO", depParser="STANFORD-CONVERT", parseName="McCC", requireEntities=False):
        assert constParser in ("BLLIP", "BLLIP-BIO", "STANFORD", None)
        assert depParser in ("STANFORD", "STANFORD-CONVERT", None)
        self.constParser = constParser
        self.depParser = depParser
        self.requireEntities = requireEntities
        self.parseName = parseName
        ToolChain.__init__(self)
        self.modelParameterStringName = "preprocessorParams"
    
    def getDefaultSteps(self):
        steps = []
        steps.append( ("CONVERT", self.convert, {"dataSetNames":None, "corpusName":None}, "documents.xml") )
        steps.append( ("SPLIT-SENTENCES", Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "sentences.xml") )
        steps.append( ("NER", Tools.BANNER.run, {"elementName":"entity", "processElement":"sentence", "debug":False, "splitNewlines":True}, "ner.xml") )
        self.addParsingSteps(steps)
        steps.append( ("SPLIT-NAMES", ProteinNameSplitter.mainFunc, {"parseName":self.parseName, "removeOld":True}, "split-names.xml") )
        steps.append( ("FIND-HEADS", FindHeads.findHeads, {"parse":self.parseName, "removeExisting":True}, "heads.xml") )
        steps.append( ("DIVIDE-SETS", self.divideSets, {"saveCombined":False}, "dummy.xml") )
        return steps
    
    def addParsingSteps(self, steps):
        # Add the constituency parser
        if self.constParser == "BLLIP-BIO" or self.constParser == "BLLIP":
            steps.append( (self.constParser + "-CONST", BLLIPParser.process, {"parseName":self.parseName, "requireEntities":self.requireEntities, "debug":False}, "parse.xml") )
        elif self.constParser == "STANFORD":
            steps.append( (self.constParser + "-CONST", StanfordParser.process, {"parser":self.parseName, "debug":False, "action":"penn"}, "parse.xml") )
        # Add the dependency parser
        if self.depParser == "STANFORD":
            steps.append( (self.depParser + "-DEP", StanfordParser.process, {"parser":self.parseName, "debug":False, "action":"dep"}, "dependencies.xml") )
        elif self.depParser == "STANFORD-CONVERT":
            steps.append( (self.depParser + "-DEP", StanfordParser.process, {"parser":self.parseName, "debug":False, "action":"convert"}, "dependencies.xml") )
    
    def process(self, source, output, parameters=None, model=None, sourceDataSetNames=None, fromStep=None, toStep=None, omitSteps=None):
        if omitSteps != None and((type(omitSteps) in types.StringTypes and omitSteps == "CONVERT") or "CONVERT" in omitSteps):
            raise Exception("Preprocessor step 'CONVERT' may not be omitted")
        if os.path.basename(source).isdigit(): # PMID
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
    optparser.add_option("-s", "--step", default=None, dest="step", help="")
    optparser.add_option("-t", "--toStep", default=None, dest="toStep", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("--requireEntities", default=False, action="store_true", dest="requireEntities", help="")
    optparser.add_option("--constParser", default="BLLIP_BIO", help="BLLIP, BLLIP_BIO or STANFORD")
    optparser.add_option("--depParser", default="STANFORD_CONVERT", help="STANFORD or STANFORD_CONVERT")
    optparser.add_option("--parseName", default="McCC")
    (options, args) = optparser.parse_args()
    if options.omitSteps != None:
        options.omitSteps = options.omitSteps.split(",")
    options.constParser = options.constParser if options.constParser != "None" else None
    options.depParser = options.depParser if options.depParser != "None" else None
    
    if not options.noLog:
        Stream.openLog(os.path.join(options.output + "-log.txt"))
        #log(False, True, os.path.join(options.output, options.corpus + "-log.txt"))
    preprocessor = Preprocessor(options.constParser, options.depParser, options.parseName, options.requireEntities)
    preprocessor.setArgForAllSteps("debug", options.debug)
    preprocessor.stepArgs("CONVERT")["corpusName"] = options.corpus
    #preprocessor.stepArgs("PARSE")["requireEntities"] = options.requireEntities
    preprocessor.process(options.input, options.output, options.parameters, None, options.inputNames, fromStep=options.step, toStep=options.toStep, omitSteps=options.omitSteps)
