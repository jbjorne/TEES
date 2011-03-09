import sys, os, time
import subprocess
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import STFormat.Equiv
import STFormat.Validate
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
import InteractionXML.MixSets
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../../../../GeniaChallenge/formatConversion")))
import ProteinNameSplitter
import Utils.Stream as Stream
import Utils.FindHeads as FindHeads
import Tools.SentenceSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import InteractionXML.CopyParse
import InteractionXML.DeleteElements
import InteractionXML.MergeDuplicateEntities
import cElementTreeUtils as ETUtils

import Evaluators.BioNLP11GeniaTools as BioNLP11GeniaTools

#BindTo: 4 + 2
#PromoterDependence
#PromoterOf
#SiteOf
#RegulonMember
#RegulonDependence

moveBI = ["PMID-10333516-S3",
          "PMID-10503549-S4",
          "PMID-10788508-S10",
          "PMID-1906867-S3",
          "PMID-9555886-S6",
          "PMID-10075739-S13",
          "PMID-10400595-S1",
          "PMID-10220166-S12"]

def evaluateB(sourceDir, corpusName):
    if corpusName == "BI":
        subprocess.call("java -jar /home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_bacteria_interactions_evaluation_software/BioNLP-ST_2011_bacteria_interactions_evaluation_software.jar /home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_bacteria_interactions_dev_data_rev1-remixed/ " + sourceDir, shell=True)
    elif corpusName == "BB":
        subprocess.call("java -jar /home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software.jar /home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1 " + sourceDir, shell=True)
    else:
        assert False, corpusName

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def convert(datasets, analysisTags, analysisPath, corpusName):
    global moveBI
    
    bigfileName = corpusName + "-" + "-and-".join([x[0] for x in datasets])
    documents = []
    for pair in datasets:
        print >> sys.stderr, "Reading", pair[0], "set,",
        sitesAreArguments = False
        if corpusName == "EPI":
            sitesAreArguments = True
        docs = ST.loadSet(pair[1], pair[0], "a2", sitesAreArguments=sitesAreArguments)
        print >> sys.stderr, len(docs), "documents"
        documents.extend(docs)
    
    print >> sys.stderr, "Resolving equivalences"
    STFormat.Equiv.process(documents)
    
    print >> sys.stderr, "Checking data validity"
    for doc in documents:
        STFormat.Validate.validate(doc.events, simulation=True, verbose=True, docId=doc.id)
    print >> sys.stderr, "Writing all documents to geniaformat"
    ST.writeSet(documents, "all-geniaformat", resultFileTag="a2", makePackage=False, debug=False, task=2, validate=False)

    print >> sys.stderr, "Converting to", bigfileName+"-documents.xml"
    xml = STConvert.toInteractionXML(documents, corpusName, bigfileName+"-documents.xml")
    
    if corpusName == "BI":
        InteractionXML.MixSets.mixSets(xml, None, set(moveBI), "train", "devel")
    
    for pair in datasets:
        if True: #corpusName != "BI":
            print >> sys.stderr, "Adding analyses for set", pair[0]
            addAnalyses(xml, analysisTags[pair[0]], analysisPath, bigfileName)
    ETUtils.write(xml, bigfileName+"-sentences.xml")
    processParses(corpusName, xml)
    
    # Write out converted data
    ETUtils.write(xml, bigfileName+".xml")
    InteractionXML.MergeDuplicateEntities.mergeAll(xml, bigfileName+"-nodup.xml")
    for sourceTag in ["", "-nodup"]:
        print >> sys.stderr, "Dividing into sets"
        InteractionXML.DivideSets.processCorpus(bigfileName+sourceTag+".xml", "./", corpusName + "-", sourceTag + ".xml", [("devel", "train")])
        if "devel" in [x[0] for x in datasets]:
            print >> sys.stderr, "Converting back"
            STConvert.toSTFormat(corpusName + "-devel" + sourceTag + ".xml", "roundtrip/" + corpusName + "-devel" + sourceTag + "-task2", outputTag="a2", task=2)
            STConvert.toSTFormat(corpusName + "-devel" + sourceTag + ".xml", "roundtrip/" + corpusName + "-devel" + sourceTag + "-task1", outputTag="a2", task=1)
            if corpusName == "GE":
                print >> sys.stderr, "Evaluating task 2 back-conversion"
                BioNLP11GeniaTools.evaluate("roundtrip/" + corpusName + "-devel" + sourceTag + "-task2", task=2, verbose=True, debug=False)
                print >> sys.stderr, "Evaluating task 1 back-conversion"
                BioNLP11GeniaTools.evaluate("roundtrip/" + corpusName + "-devel" + sourceTag + "-task1", task=1, verbose=True, debug=False)
            elif corpusName in ["BI", "BB"]:
                print >> sys.stderr, "Evaluating task 2 back-conversion"
                evaluateB("roundtrip/" + corpusName + "-devel" + sourceTag + "-task2", corpusName)
                print >> sys.stderr, "Evaluating task 1 back-conversion"
                evaluateB("roundtrip/" + corpusName + "-devel" + sourceTag + "-task1", corpusName)
            print >> sys.stderr, "Creating empty devel set"
            deletionRules = {"interaction":{},"entity":{"isName":"False"}}
            InteractionXML.DeleteElements.processCorpus(corpusName + "-devel" + sourceTag + ".xml", corpusName + "-devel" + sourceTag + "-empty.xml", deletionRules)
        # Roundtrip
        #if not os.path.exists("roundtrip"):
        #    os.makedirs("roundtrip")
        #for dataSet in [x[0] for x in datasets]:
        #    STConvert.toSTFormat(corpusName + "-devel" + sourceTag + ".xml", "roundtrip/" + corpusName + "-devel" + sourceTag, outputTag="a2")

def addAnalyses(xml, analysisTag, analysisPath, bigfileName):
    print >> sys.stderr, "Inserting", analysisTag, "analyses"
    print >> sys.stderr, "Making sentences"
    Tools.SentenceSplitter.makeSentences(xml, analysisPath + "Tokenised/Tokenised-" + analysisTag + ".tar.gz/" + analysisTag + "/tokenised", None)
    print >> sys.stderr, "Inserting McCC parses"
    Tools.CharniakJohnsonParser.insertParses(xml, analysisPath + "McCC/McCC-parses-" + analysisTag + ".tar.gz/" + analysisTag + "/mccc/ptb", None)
    print >> sys.stderr, "Inserting Stanford conversions"
    Tools.StanfordParser.insertParses(xml, analysisPath + "McCC/McCC-parses-" + analysisTag + ".tar.gz/" + analysisTag + "/mccc/sd_ccproc", None)
#    print >> sys.stderr, "Parsing"
#    Tools.CharniakJohnsonParser.parse(bigfileName+"-sentences.xml", bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False)
#    print >> sys.stderr, "Stanford Conversion"
#    Tools.StanfordParser.convertXML("McClosky", bigfileName+"-parsed.xml", bigfileName+"-stanford.xml")

def processParses(corpusName, xml, splitTarget="mccc-preparsed"):
    if corpusName != "BI":
        print >> sys.stderr, "Protein Name Splitting"
        #splitterCommand = "python /home/jari/cvs_checkout/JariSandbox/GeniaChallenge/formatConversion/ProteinNameSplitter.py -f " + bigfileName+"-sentences.xml" + " -o " + bigfileName+"-split.xml" + " -p " + splitTarget + " -t " + splitTarget + " -s split-"+splitTarget + " -n split-"+splitTarget
        #subprocess.call(splitterCommand, shell=True)
        ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(xml, "split-"+splitTarget, tokenization=None, output=None, removeExisting=True)
    else:
        ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(xml, "split-"+splitTarget, tokenization=None, output=None, removeExisting=True)
        #xml = FindHeads.findHeads(xml, "gold", tokenization=None, output=None, removeExisting=True)

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
                      ("train", dataPath+"BioNLP-ST_2011_genia_train_data_rev1"),
                      ("test", dataPath+"BioNLP-ST_2011_genia_test_data")]
    datasets["EPI"] = [("devel", dataPath+"BioNLP-ST_2011_Epi_and_PTM_development_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_Epi_and_PTM_training_data_rev1"),
                      ("test", dataPath+"BioNLP-ST_2011_Epi_and_PTM_test_data")]
    datasets["ID"] = [("devel", dataPath+"BioNLP-ST_2011_Infectious_Diseases_development_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_Infectious_Diseases_training_data_rev1"),
                      ("test", dataPath+"BioNLP-ST_2011_Infectious_Diseases_test_data")]
    datasets["BB"] = [("devel", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1"),
                      ("test", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_test_data")]
    datasets["BI"] = [("devel", dataPath+"BioNLP-ST_2011_bacteria_interactions_dev_data_rev1"), 
                      ("train", dataPath+"BioNLP-ST_2011_bacteria_interactions_train_data_rev1"),
                      ("test", dataPath+"BioNLP-ST_2011_bacteria_interactions_test_data")]
    
    analysisTags = {}
    analysisPath = "/home/jari/data/BioNLP11SharedTask/analyses/"
    analysisTags["GE"] =  {"devel":"BioNLP-ST_2011_genia_devel_data_rev1",
                           "train":"BioNLP-ST_2011_genia_train_data_rev1",
                           "test":"BioNLP-ST_2011_genia_test_data"}
    analysisTags["EPI"] = {"devel":"BioNLP-ST_2011_Epi_and_PTM_development_data",
                           "train":"BioNLP-ST_2011_Epi_and_PTM_training_data",
                           "test":"BioNLP-ST_2011_Epi_and_PTM_test_data"}
    analysisTags["ID"] =  {"devel":"BioNLP-ST_2011_Infectious_Diseases_development_data",
                           "train":"BioNLP-ST_2011_Infectious_Diseases_training_data",
                           "test":"BioNLP-ST_2011_Infectious_Diseases_test_data"}
    analysisTags["BB"] =  {"devel":"BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1",
                           "train":"BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1",
                           "test":"BioNLP-ST_2011_Bacteria_Biotopes_test_data"}
    analysisTags["BI"] = {"devel":"BioNLP-ST_2011_bacteria_interactions_dev_data",
                           "train":"BioNLP-ST_2011_bacteria_interactions_train_data",
                           "test":"BioNLP-ST_2011_bacteria_interactions_test_data"}
    
    for dataset in ["BB"]: #sorted(datasets.keys()):
        cwd = os.getcwd()
        currOutDir = outDir + dataset
        if not os.path.exists(currOutDir):
            os.makedirs(currOutDir)
        os.chdir(currOutDir)
        log(False, False, dataset + "-conversion-log.txt")
        print >> sys.stderr, "Processing dataset", dataset
        convert(datasets[dataset], analysisTags[dataset], analysisPath, dataset)
        os.chdir(cwd)