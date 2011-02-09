import sys, os, time
import subprocess
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.Stream as Stream
import Utils.FindHeads as FindHeads
import Tools.SentenceSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import InteractionXML.CopyParse
import InteractionXML.DeleteElements
import cElementTreeUtils as ETUtils

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def convert(datasets, analysisTags, analysisPath, corpusName):
    bigfileName = corpusName + "-" + "-and-".join([x[0] for x in datasets])
    documents = []
    for pair in datasets:
        print >> sys.stderr, "Reading", pair[0], "set,",
        docs = ST.loadSet(pair[1], pair[0], "a2")
        print >> sys.stderr, len(docs), "documents"
        documents.extend(docs)

    print >> sys.stderr, "Converting to", bigfileName+"-documents.xml"
    xml = STConvert.toInteractionXML(documents, corpusName, bigfileName+"-documents.xml")
    for pair in datasets:
        if corpusName != "BI":
            addAnalyses(xml, analysisTags[pair[0]], analysisPath, bigfileName)
    ETUtils.write(xml, bigfileName+"-sentences.xml")
    processParses(corpusName, bigfileName)
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(bigfileName+".xml", "./", corpusName + "-", ".xml", [("devel", "train")])
    if "devel" in [x[0] for x in datasets]:
        print >> sys.stderr, "Creating empty devel set"
        deletionRules = {"interaction":{},"entity":{"isName":"False"}}
        InteractionXML.DeleteElements.processCorpus(corpusName + "-devel.xml", corpusName + "-devel-empty.xml", deletionRules)

def addAnalyses(xml, analysisTag, analysisPath, bigfileName):
    print >> sys.stderr, "Inserting", analysisTag, "analyses"
    print >> sys.stderr, "Making sentences"
    Tools.SentenceSplitter.makeSentences(xml, analysisPath + "Tokenised/Tokenised-" + analysisTag + ".tar.gz/" + analysisTag + "/tokenised", None)
    print >> sys.stderr, "Inserting McCC parses"
    Tools.CharniakJohnsonParser.insertParses(xml, analysisPath + "McCC/McCC-parses-" + analysisTag + ".tar.gz/" + analysisTag + "/mccc/ptb", bigfileName+"-mccc.xml")
    print >> sys.stderr, "Inserting Stanford conversions"
    Tools.StanfordParser.insertParses(xml, analysisPath + "McCC/McCC-parses-" + analysisTag + ".tar.gz/" + analysisTag + "/mccc/sd_ccproc", None)
#    print >> sys.stderr, "Parsing"
#    Tools.CharniakJohnsonParser.parse(bigfileName+"-sentences.xml", bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False)
#    print >> sys.stderr, "Stanford Conversion"
#    Tools.StanfordParser.convertXML("McClosky", bigfileName+"-parsed.xml", bigfileName+"-stanford.xml")

def processParses(corpusName, bigfileName, splitTarget="mccc"):
    if corpusName != "BI":
        print >> sys.stderr, "Protein Name Splitting"
        splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + bigfileName+"-sentences.xml" + " -o " + bigfileName+"-split.xml" + " -p " + splitTarget + " -t " + splitTarget + " -s split-"+splitTarget + " -n split-"+splitTarget
        subprocess.call(splitterCommand, shell=True)
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(bigfileName+"-split.xml", "split-"+splitTarget, tokenization=None, output=bigfileName+".xml", removeExisting=True)
    else:
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(bigfileName+".xml", "gold", tokenization=None, output=bigfileName+".xml", removeExisting=True)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    outDir = "/usr/share/biotext/BioNLP2011/data/main-tasks/"
    #everythingXML = outDir + "rel-everything-with-unconnected.xml"
    #everythingXMLNoUnconnected = outDir + "rel-everything.xml"
    
    datasets = {}
    dataPath = "/home/jari/data/BioNLP11SharedTask/main-tasks/"
    #trainSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_training_data"
    #develSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_development_data"
    #testSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_test_data"
    #datasets["GE"] = [("devel", develSet), ("train", trainSet), ("test", testSet)]
    #datasets["GE"] = [("devel", dataPath+"BioNLP-ST_2011_GENIA_devel_data"), 
    #                  ("train", dataPath+"BioNLP-ST_2011_GENIA_train_data")]
    datasets["GE"] = [("devel", dataPath+"BioNLP-ST_2011_genia_devel_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_genia_train_data_rev1")]
    datasets["EPI"] = [("devel", dataPath+"BioNLP-ST_2011_Epi_and_PTM_development_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_Epi_and_PTM_training_data_rev1")]
    datasets["ID"] = [("devel", dataPath+"BioNLP-ST_2011_Infectious_Diseases_development_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_Infectious_Diseases_training_data_rev1")]
    datasets["BB"] = [("devel", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1")]
    datasets["BI"] = [("devel", dataPath+"BioNLP-ST_2011_bacteria_interactions_dev_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_bacteria_interactions_train_data_rev1")]
    
    analysisTags = {}
    analysisPath = "/home/jari/data/BioNLP11SharedTask/analyses/"
    analysisTags["GE"] =  {"devel":"BioNLP-ST_2011_genia_devel_data_rev1",
                           "train":"BioNLP-ST_2011_genia_train_data_rev1"}
    analysisTags["EPI"] = {"devel":"BioNLP-ST_2011_Epi_and_PTM_development_data",
                           "train":"BioNLP-ST_2011_Epi_and_PTM_training_data"}
    analysisTags["ID"] =  {"devel":"BioNLP-ST_2011_Infectious_Diseases_development_data",
                           "train":"BioNLP-ST_2011_Infectious_Diseases_training_data"}
    analysisTags["BB"] =  {"devel":"BioNLP-ST_2011_Bacteria_Biotopes_dev_data",
                           "train":"BioNLP-ST_2011_Bacteria_Biotopes_train_data"}
    analysisTags["BI"] = None
    
    for dataset in ["BB"]: #["GE", "EPI", "ID"]: #sorted(datasets.keys()):
        cwd = os.getcwd()
        currOutDir = outDir + dataset
        if not os.path.exists(currOutDir):
            os.makedirs(currOutDir)
        os.chdir(currOutDir)
        log(False, False, dataset + "-conversion-log.txt")
        print >> sys.stderr, "Processing dataset", dataset
        convert(datasets[dataset], analysisTags[dataset], analysisPath, dataset)
        os.chdir(cwd)