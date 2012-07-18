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
import Tools.BLLIPParser
import Tools.StanfordParser
import Tools.BANNER
from ToolChain import ToolChain
import Utils.InteractionXML.DivideSets
import Utils.ProteinNameSplitter as ProteinNameSplitter
import Utils.FindHeads as FindHeads
#from Test.Pipeline import log
import Utils.Stream as Stream

class Preprocessor(ToolChain):
    def __init__(self):
        ToolChain.__init__(self)
        self.modelParameterStringName = "preprocessorParams"
    
    def getDefaultSteps(self):
        steps = []
        steps.append( ("CONVERT", self.convert, {"dataSetNames":None, "corpusName":None}, "documents.xml") )
        steps.append( ("SPLIT-SENTENCES", Tools.GeniaSentenceSplitter.makeSentences, {"debug":False, "postProcess":True}, "sentences.xml") )
        steps.append( ("NER", Tools.BANNER.run, {"elementName":"entity", "processElement":"sentence", "debug":False, "splitNewlines":True}, "ner.xml") )
        steps.append( ("PARSE", Tools.BLLIPParser.parse, {"parseName":"McCC", "requireEntities":False, "debug":False}, "parse.xml") )
        steps.append( ("CONVERT-PARSE", Tools.StanfordParser.convertXML, {"parser":"McCC", "debug":False}, "converted-parse.xml") )
        steps.append( ("SPLIT-NAMES", ProteinNameSplitter.mainFunc, {"parseName":"McCC", "removeOld":True}, "split-names.xml") )
        steps.append( ("FIND-HEADS", FindHeads.findHeads, {"parse":"McCC", "removeExisting":True}, "heads.xml") )
        steps.append( ("DIVIDE-SETS", self.divideSets, {"outputStem":None, "saveCombined":True}) )
        return steps
    
    def process(self, source, output, parameters=None, model=None, sourceDataSetNames=None, fromStep=None, toStep=None, omitSteps=None):
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
        if os.path.isdir(input) or input.endswith(".tar.gz") or input.endswith(".txt") or "," in input:
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
    
    def divideSets(self, input, outputStem, saveCombined=True):
        if outputStem != None:
            print >> sys.stderr, "Dividing into sets"
            outDir, outputStem = os.path.split(outputStem)
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
    (options, args) = optparser.parse_args()
    if options.omitSteps != None:
        options.omitSteps = options.omitSteps.split(",")
    
    if not options.noLog:
        Stream.openLog(os.path.join(options.output + "-log.txt"))
        #log(False, True, os.path.join(options.output, options.corpus + "-log.txt"))
    preprocessor = Preprocessor()
    preprocessor.setArgForAllSteps("debug", options.debug)
    preprocessor.stepArgs("CONVERT")["corpusName"] = options.corpus
    preprocessor.stepArgs("PARSE")["requireEntities"] = options.requireEntities
    preprocessor.process(options.input, options.output, options.parameters, None, options.inputNames, fromStep=options.step, toStep=options.toStep, omitSteps=options.omitSteps)
