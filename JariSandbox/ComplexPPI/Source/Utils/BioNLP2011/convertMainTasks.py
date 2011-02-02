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
import Tools.GeniaSentenceSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import InteractionXML.CopyParse
import InteractionXML.DeleteElements

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def convert(datasets, outdir, corpusName):
    bigfileName = corpusName + "-" + "-and-".join([x[0] for x in datasets])
    documents = []
    for pair in datasets:
        print >> sys.stderr, "Reading", pair[0], "set,",
        docs = ST.loadSet(pair[1], pair[0], "a1")
        print >> sys.stderr, len(docs), "documents"
        documents.extend(docs)

    print >> sys.stderr, "Converting to", bigfileName+"-documents.xml"
    xml = STConvert.toInteractionXML(documents, corpusName, bigfileName+"-documents.xml")
    print >> sys.stderr, "Making sentences"
    xml = Tools.GeniaSentenceSplitter.makeSentences(xml, bigfileName+"-sentences.xml", postProcess=False)
    print >> sys.stderr, "Parsing"
    Tools.CharniakJohnsonParser.parse(bigfileName+"-sentences.xml", bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False)
    print >> sys.stderr, "Stanford Conversion"
    Tools.StanfordParser.convertXML("McClosky", bigfileName+"-parsed.xml", bigfileName+"-stanford.xml")
    print >> sys.stderr, "Protein Name Splitting"
    splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + bigfileName+"-stanford.xml" + " -o " + bigfileName+"-split.xml" + " -p " + "McClosky" + " -t " + "McClosky" + " -s split-McClosky" + " -n split-McClosky"
    subprocess.call(splitterCommand, shell=True)
    print >> sys.stderr, "Head Detection"
    xml = FindHeads.findHeads(bigfileName+"-split.xml", "split-McClosky", tokenization=None, output=bigfileName+".xml", removeExisting=True)
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(bigfileName+".xml", outDir, corpusName + "-", ".xml", [("devel", "train")])
    #if "devel" in [x[0] for x in datasets]:
    #    print >> sys.stderr, "Creating empty devel set"
    #    deletionRules = {"interaction":{},"entity":{"isName":"False"}}
    #    InteractionXML.DeleteElements.processCorpus(corpusName + "-devel.xml", corpusName + "-devel-empty.xml", deletionRules)
    #return xml

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    outDir = "/usr/share/biotext/BioNLP2011/data/"
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
    datasets["EPI"] = [("devel", dataPath+"BioNLP-ST_2011_Epi_and_PTM_development_data"), 
                      ("train", dataPath+"BioNLP-ST_2011_Epi_and_PTM_training_data")]
    datasets["ID"] = [("devel", dataPath+"BioNLP-ST_2011_Infectious_Diseases_development_data"), 
                      ("train", dataPath+"BioNLP-ST_2011_Infectious_Diseases_training_data")]
    datasets["BB"] = [("devel", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_dev_data"), 
                      ("train", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_train_data")]
    datasets["BI"] = [("devel", dataPath+"BioNLP-ST_2011_bacteria_interactions_dev_data"), 
                      ("train", dataPath+"BioNLP-ST_2011_bacteria_interactions_train_data")]
    
    for dataset in ["BB"]: #["GE"]: #sorted(datasets.keys()):
        cwd = os.getcwd()
        currOutDir = outDir + dataset
        if not os.path.exists(currOutDir):
            os.makedirs(currOutDir)
        os.chdir(currOutDir)
        log(False, False, dataset + "-conversion-log.txt")
        convert(datasets[dataset], outDir, dataset)
        os.chdir(cwd)