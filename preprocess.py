import sys
from Detectors.Preprocessor import Preprocessor

if __name__=="__main__":
    from optparse import OptionParser, OptionGroup
    optparser = OptionParser(description="A tool chain for making interaction XML, sentence splitting, NER and parsing")
    optparser.add_option("-i", "--input", default=None, dest="input", help="The input argument for the first step")
    optparser.add_option("-o", "--output", default=None, dest="output", help="The output argument for the last step")
    #optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Step parameters, a comma-separated list of 'STEP.parameter=value' definitions")
    optparser.add_option("-s", "--steps", default=None, dest="steps", help="A comma separated list of steps or presets")
    shortcuts = OptionGroup(optparser, "Preprocessing step parameter shortcuts", "")
    shortcuts.add_option("-n", "--dataSetNames", default=None, dest="dataSetNames", help="CONVERT step dataset names")
    shortcuts.add_option("-c", "--corpus", default=None, dest="corpus", help="CONVERT step XML corpus element name")
    shortcuts.add_option("--requireEntities", default=False, action="store_true", dest="requireEntities", help="Default setting for parsing steps")
    #optparser.add_option("--constParser", default="BLLIP-BIO", help="BLLIP, BLLIP-BIO or STANFORD")
    #optparser.add_option("--depParser", default="STANFORD-CONVERT", help="STANFORD or STANFORD-CONVERT")
    shortcuts.add_option("--parseName", default="McCC", help="Default setting for parsing steps")
    shortcuts.add_option("--parseDir", default=None, help="IMPORT-PARSE step parse files directory")
    shortcuts.add_option("--importFormats", default=None, help="LOAD/IMPORT-PARSE format options")
    shortcuts.add_option("--exportFormats", default=None, help="EXPORT format options")
    optparser.add_option_group(shortcuts)
    debug = OptionGroup(optparser, "Debug and Process Control Options", "")
#    debug.add_option("-f", "--fromStep", default=None, dest="fromStep", help="Continue from this step")
#    debug.add_option("-t", "--toStep", default=None, dest="toStep", help="Stop at after this step")
#    debug.add_option("--omitSteps", default=None, dest="omitSteps", help="Skip these steps")
    debug.add_option("--logPath", default="AUTO", dest="logPath", help="AUTO, None, or a path")
    #debug.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="Save an intermediate file for each step")
    debug.add_option("--debug", default=False, action="store_true", dest="debug", help="Set debug mode for all steps")
    optparser.add_option_group(debug)
    (options, args) = optparser.parse_args()
    
#     if options.steps != None:
#         options.steps = [x.strip() for x in options.steps.split(",")]
#     if options.omitSteps != None:
#         options.omitSteps = options.omitSteps.split(",")
#         
    preprocessor = Preprocessor(options.steps, options.parseName, options.requireEntities)
    if options.steps == None:
        print >> sys.stderr, preprocessor.getHelpString()
    else:
        preprocessor.setArgForAllSteps("debug", options.debug)
        if preprocessor.hasStep("CONVERT"):
            if options.corpus != None:
                preprocessor.getStep("CONVERT").setArg("corpusName", options.corpus)
            if options.dataSetNames != None:
                preprocessor.getStep("CONVERT").setArg("dataSetNames", options.dataSetNames)
        if options.parseDir:
            preprocessor.getStep("IMPORT_PARSE").setArg("parseDir", options.parseDir)
        if options.exportFormats and preprocessor.hasStep("EXPORT"):
            preprocessor.getStep("EXPORT").setArg("formats", options.exportFormats.split(","))
        if options.importFormats:
            if preprocessor.hasStep("LOAD"):
                preprocessor.getStep("LOAD").setArg("extensions", options.importFormats.split(","))
            if preprocessor.hasStep("IMPORT_PARSE"):
                preprocessor.getStep("IMPORT_PARSE").setArg("extensions", options.importFormats.split(","))
        #if options.intermediateFiles:
        #    preprocessor.setIntermediateFiles(True)
        preprocessor.process(options.input, options.output, model=None, logPath=options.logPath)