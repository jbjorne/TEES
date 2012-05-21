import sys, os, time, shutil
import subprocess
import tempfile
import tarfile
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../CommonUtils")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../GeniaChallenge/formatConversion")))
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import STFormat.Equiv
import STFormat.Validate
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
import InteractionXML.MixSets
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

import Utils.Settings as Settings
import urllib

urls = {}
urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/files/"
urls["GE_DEVEL"] = urlBase + "BioNLP-ST_2011_genia_devel_data_rev1.tar.gz" 
urls["GE_TRAIN"] = urlBase + "BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
urls["GE_TEST"] = urlBase + "BioNLP-ST_2011_genia_test_data.tar.gz"

urlBase = "http://weaver.nlplab.org/~bionlp-st/BioNLP-ST/downloads/support-files/"
urls["GE_DEVEL_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_train_data_rev1.tar.gz"
urls["GE_TRAIN_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
urls["GE_TEST_TOKENS"] = urlBase + "Tokenised-BioNLP-ST_2011_genia_test_data.tar.gz"
urls["GE_DEVEL_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_train_data_rev1.tar.gz" 
urls["GE_TRAIN_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_devel_data_rev1.tar.gz"
urls["GE_TEST_McCC"] = urlBase + "McCC-parses-BioNLP-ST_2011_genia_test_data.tar.gz"

moveBI = ["PMID-10333516-S3",
          "PMID-10503549-S4",
          "PMID-10788508-S10",
          "PMID-1906867-S3",
          "PMID-9555886-S6",
          "PMID-10075739-S13",
          "PMID-10400595-S1",
          "PMID-10220166-S12"]

def download(url, destPath, clear=False):
    if not os.path.exists(destPath):
        os.makedirs(destPath)
    destFileName = os.path.join(destPath, os.path.basename(url))
    if not os.path.exists(destFileName):
        print >> sys.stderr, "Downloading", url
        urllib.urlretrieve(url, destFileName)
    else:
        print >> sys.stderr, "Skipping already downloaded", url
    return destFileName

def downloadCorpus(corpus):
    downloaded = {}
    destPath = os.path.join(Settings.DATAPATH, "BioNLP11/original/corpus/")
    for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
        downloaded[corpus + setName] = download(urls[corpus + setName], destPath)
    destPath = os.path.join(Settings.DATAPATH, "BioNLP11/original/support/")
    for analysis in ["_TOKENS", "_McCC"]:
        for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
            downloaded[corpus + setName + analysis] = download(urls[corpus + setName + analysis], destPath)
    return downloaded

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def convert(outdir, corpus, files, intermediateFiles=True):
    global moveBI
    workdir = outdir + "/" + corpus + "-conversion"
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)
    
    # All datasets are processed as one XML, to ensure all the steps (parse modification etc.) are
    # applied equally
    datasets = ["devel", "train", "test"]
    bigfileName = os.path.join(outdir, corpus + "-" + "-and-".join(datasets))
    documents = []
    for setName in datasets:
        sourceFile = files[corpus + "_" + setName.upper()]
        print >> sys.stderr, "Reading", setName, "set from", sourceFile, "set,"
        sitesAreArguments = False
        if corpus == "EPI":
            sitesAreArguments = True
        docs = ST.loadSet(sourceFile, setName, "a2", sitesAreArguments=sitesAreArguments)
        print >> sys.stderr, "Read", len(docs), "documents"
        documents.extend(docs)
    
    print >> sys.stderr, "Resolving equivalences"
    STFormat.Equiv.process(documents)
    
    print >> sys.stderr, "Checking data validity"
    for doc in documents:
        STFormat.Validate.validate(doc.events, simulation=True, verbose=True, docId=doc.id)
    print >> sys.stderr, "Writing all documents to geniaformat"
    ST.writeSet(documents, os.path.join(workdir, "all-geniaformat"), resultFileTag="a2", debug=False, task=2, validate=False)
    
    if intermediateFiles:
        print >> sys.stderr, "Converting to XML, writing combined corpus to", bigfileName+"-documents.xml"
        xml = STConvert.toInteractionXML(documents, corpus, bigfileName+"-documents.xml")
    else:
        print >> sys.stderr, "Converting to XML"
        xml = STConvert.toInteractionXML(documents, corpus, None)
    
    if corpus == "BI":
        InteractionXML.MixSets.mixSets(xml, None, set(moveBI), "train", "devel")
    
    for setName in datasets:
        print >> sys.stderr, "Adding analyses for set", setName
        addAnalyses(xml, corpus, setName, files, bigfileName)
    if intermediateFiles:
        print >> sys.stderr, "Writing combined corpus", bigfileName+"-sentences.xml"
        ETUtils.write(xml, bigfileName+"-sentences.xml")
    processParses(xml)
    
    # Write out converted data
    if intermediateFiles:
        print >> sys.stderr, "Writing combined corpus", bigfileName+".xml"
        ETUtils.write(xml, bigfileName+".xml")
    #InteractionXML.MergeDuplicateEntities.mergeAll(xml, bigfileName+"-nodup.xml")
    #for sourceTag in ["", "-nodup"]:
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(bigfileName+".xml", outdir, corpus, ".xml")
    if "devel" in datasets:
        print >> sys.stderr, "Converting back"
        STConvert.toSTFormat(corpus + "-devel.xml", workdir + "/roundtrip/" + corpus + "-devel" + "-task1", outputTag="a2", task=1)
        STConvert.toSTFormat(corpus + "-devel.xml", workdir + "/roundtrip/" + corpus + "-devel" + "-task2", outputTag="a2", task=2)
        if corpusName == "GE":
            print >> sys.stderr, "Evaluating task 1 back-conversion"
            BioNLP11GeniaTools.evaluate(workdir + "roundtrip/" + corpusName + "-devel" + "-task1", corpus + ".1")
            print >> sys.stderr, "Evaluating task 2 back-conversion"
            BioNLP11GeniaTools.evaluate(workdir + "roundtrip/" + corpusName + "-devel" + "-task2", corpus + ".2")
        #print >> sys.stderr, "Creating empty devel set"
        #deletionRules = {"interaction":{},"entity":{"isName":"False"}}
        #InteractionXML.DeleteElements.processCorpus(corpusName + "-devel" + sourceTag + ".xml", corpusName + "-devel" + sourceTag + "-empty.xml", deletionRules)

def extract(filename, targetdir):
    print >> sys.stderr, "Extracting", filename, "to", targetdir
    f = tarfile.open(filename, 'r:gz')
    f.extractall(targetdir)
    f.close()

def addAnalyses(xml, corpus, setName, files, bigfileName):
    print >> sys.stderr, "Inserting", setName, "analyses"
    tempdir = tempfile.mkdtemp()
    extract(files[corpus + "_" + setName.upper() + "_TOKENS"], tempdir)
    extract(files[corpus + "_" + setName.upper() + "_McCC"], tempdir)
    print >> sys.stderr, "Making sentences"
    Tools.SentenceSplitter.makeSentences(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_TOKENS"])[:-len(".tar.gz")].split("-", 1)[-1] + "/tokenised", None)
    print >> sys.stderr, "Inserting McCC parses"
    Tools.CharniakJohnsonParser.insertParses(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCC"])[:-len(".tar.gz")].split("-", 2)[-1] + "/mccc/ptb", None)
    print >> sys.stderr, "Inserting Stanford conversions"
    Tools.StanfordParser.insertParses(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCC"])[:-len(".tar.gz")].split("-", 2)[-1] + "/mccc/sd_ccproc", None)
    print >> sys.stderr, "Removing temporary directory", tempdir
    shutil.rmtree(tempdir)

def processParses(xml, splitTarget="mccc-preparsed"):
    print >> sys.stderr, "Protein Name Splitting"
    ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
    print >> sys.stderr, "Head Detection"
    xml = FindHeads.findHeads(xml, "split-"+splitTarget, tokenization=None, output=None, removeExisting=True)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    from Utils.Parameters import *
    optparser = OptionParser(usage="%prog [options]\nBioNLP'11 Shared Task corpus conversion")
    optparser.add_option("-c", "--corpora", default="GE", dest="corpora", help="corpus names in a comma-separated list, e.g. \"GE,EPI,ID\"")
    optparser.add_option("-o", "--outdir", default=os.path.join(Settings.DATAPATH, "BioNLP11/corpora/"), dest="outdir", help="directory for output files")
    optparser.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="save intermediate corpus files")
    (options, args) = optparser.parse_args()
    
    if not os.path.exists(options.outdir):
        os.makedirs(options.outdir)
    
    log(False, True, os.path.join(options.outdir, "conversion-log.txt"))
    corpora = options.corpora.split(",")
    for corpus in corpora:
        print >> sys.stderr, "=======================", "Converting", corpus, "======================="
        downloaded = downloadCorpus(corpus)
        convert(options.outdir, corpus, downloaded, options.intermediateFiles)
