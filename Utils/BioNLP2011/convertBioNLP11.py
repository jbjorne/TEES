import sys, os, time, shutil
import tempfile
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
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
import Utils.ElementTreeUtils as ETUtils
import Evaluators.BioNLP11GeniaTools as BioNLP11GeniaTools
import Utils.Download
import Utils.Settings as Settings

moveBI = ["PMID-10333516-S3", "PMID-10503549-S4", "PMID-10788508-S10", "PMID-1906867-S3",
          "PMID-9555886-S6", "PMID-10075739-S13", "PMID-10400595-S1", "PMID-10220166-S12"]

def downloadCorpus(corpus, destPath=None, downloadPath=None, clear=False):
    print >> sys.stderr, "---------------", "Downloading BioNLP Shared Task files", "---------------"
    downloaded = {}
    if destPath == None:
        finalDestPath = os.path.join(Settings.DATAPATH, "corpora/BioNLP11-original")
    else:
        finalDestPath = destPath
    for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
        downloaded[corpus + setName] = Utils.Download.download(Settings.URL[corpus + setName], finalDestPath, clear=clear)
    if corpus in ["REL", "REN", "CO"]:
        if destPath == None:
            finalDestPath = os.path.join(Settings.DATAPATH, "TEES-parses")
        else:
            finalDestPath = os.path.join(destPath, "TEES-parses")
        if downloadPath == None:
            downloadPath = os.path.join(Settings.DATAPATH, "download")
        Utils.Download.downloadAndExtract(Settings.URL["TEES_PARSES"], finalDestPath, downloadPath, redownload=clear)
        downloaded["TEES_PARSES"] = finalDestPath
    else:
        if corpus == "GE09":
            analyses = ["_ANALYSES"]
        else:
            analyses = ["_TOKENS", "_McCC"]
        for analysis in analyses:
            for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
                downloaded[corpus + setName + analysis] = Utils.Download.download(Settings.URL[corpus + setName + analysis], finalDestPath + "/support/", clear=clear)
    return downloaded

def convert(corpora, outDir, downloadDir=None, redownload=False, makeIntermediateFiles=True, evaluate=False):
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    else:
        assert os.path.isdir(outDir)
    count = 1
    for corpus in corpora:
        print >> sys.stderr, "=======================", "Converting BioNLP Shared Task", corpus, "corpus ("+str(count)+"/"+str(len(corpora))+")", "======================="
        logFileName = outDir + "/conversion/" + corpus + "-conversion-log.txt"
        Stream.openLog(logFileName)
        downloaded = downloadCorpus(corpus, downloadDir, outDir, redownload)
        convertDownloaded(outDir, corpus, downloaded, makeIntermediateFiles, evaluate)
        Stream.closeLog(logFileName)
        count += 1

def convertDownloaded(outdir, corpus, files, intermediateFiles=True, evaluate=True):
    global moveBI
    if evaluate:
        workdir = outdir + "/conversion/" + corpus
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir)
    
    print >> sys.stderr, "---------------", "Converting to XML", "---------------"
    # All datasets are processed as one XML, to ensure all the steps (parse modification etc.) are
    # applied equally
    datasets = ["devel", "train", "test"]
    bigfileName = os.path.join(outdir, corpus + "-" + "-and-".join(datasets))
    documents = []
    for setName in datasets:
        sourceFile = files[corpus + "_" + setName.upper()]
        print >> sys.stderr, "Reading", setName, "set from", sourceFile, "temp at ",
        sitesAreArguments = False
        if corpus == "EPI":
            sitesAreArguments = True
        docs = ST.loadSet(sourceFile, setName, "a2", sitesAreArguments=sitesAreArguments)
        print >> sys.stderr, "Read", len(docs), "documents"
        documents.extend(docs)
    
    print >> sys.stderr, "Resolving equivalences"
    STFormat.Equiv.process(documents)
    
    if evaluate:
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
    
    addAnalyses(xml, corpus, datasets, files, bigfileName)
    if intermediateFiles:
        print >> sys.stderr, "Writing combined corpus", bigfileName+"-sentences.xml"
        ETUtils.write(xml, bigfileName+"-sentences.xml")
    processParses(xml)
    
    print >> sys.stderr, "---------------", "Writing corpora", "---------------"
    # Write out converted data
    if intermediateFiles:
        print >> sys.stderr, "Writing combined corpus", bigfileName+".xml"
        ETUtils.write(xml, bigfileName+".xml")
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(xml, outdir, corpus, ".xml")
    
    if evaluate and "devel" in datasets:
        print >> sys.stderr, "---------------", "Evaluating conversion", "---------------"
        print >> sys.stderr, "Converting back"
        STConvert.toSTFormat(os.path.join(outdir, corpus + "-devel.xml"), workdir + "/roundtrip/" + corpus + "-devel" + "-task1", outputTag="a2", task=1)
        STConvert.toSTFormat(os.path.join(outdir, corpus + "-devel.xml"), workdir + "/roundtrip/" + corpus + "-devel" + "-task2", outputTag="a2", task=2)
        print >> sys.stderr, "Evaluating task 1 back-conversion"
        BioNLP11GeniaTools.evaluate(workdir + "/roundtrip/" + corpus + "-devel" + "-task1", corpus + ".1")
        print >> sys.stderr, "Evaluating task 2 back-conversion"
        BioNLP11GeniaTools.evaluate(workdir + "/roundtrip/" + corpus + "-devel" + "-task2", corpus + ".2")
        print >> sys.stderr, "Note! Evaluation of Task 2 back-conversion can be less than 100% due to site-argument mapping"

def addAnalyses(xml, corpus, datasets, files, bigfileName):
    if "TEES_PARSES" in files: # corpus for which no official parse exists
        print >> sys.stderr, "---------------", "Inserting TEES-generated analyses", "---------------"
        extractedFilename = files["TEES_PARSES"] + "/" + corpus
        print >> sys.stderr, "Making sentences"
        Tools.SentenceSplitter.makeSentences(xml, extractedFilename, None)
        print >> sys.stderr, "Inserting McCC parses"
        Tools.CharniakJohnsonParser.insertParses(xml, extractedFilename, None, extraAttributes={"source":"TEES-preparsed"})
        print >> sys.stderr, "Inserting Stanford conversions"
        Tools.StanfordParser.insertParses(xml, extractedFilename, None, extraAttributes={"stanfordSource":"TEES-preparsed"})
    elif corpus == "GE09": # the BioNLP'09 corpus
        for i in range(len(datasets)):
            print >> sys.stderr, "---------------", "Inserting analyses " + str(i+1) + "/" + str(len(datasets)), "---------------"
            setName = datasets[i]
            print >> sys.stderr, "Inserting", setName, "analyses"
            tempdir = tempfile.mkdtemp()
            analysesSetName = corpus + "_" + setName.upper() + "_ANALYSES"
            Utils.Download.extractPackage(files[analysesSetName], tempdir)
            print >> sys.stderr, "Making sentences"
            Tools.SentenceSplitter.makeSentences(xml, tempdir + "/" + os.path.basename(files[analysesSetName])[:-len(".tar.gz")] + "/tokenized", None)
            print >> sys.stderr, "Inserting McCC parses"
            Tools.CharniakJohnsonParser.insertParses(xml, tempdir + "/" + os.path.basename(files[analysesSetName])[:-len(".tar.gz")] + "/McClosky-Charniak/pstree", None, extraAttributes={"source":"BioNLP'09"})
            print >> sys.stderr, "Inserting Stanford conversions"
            Tools.StanfordParser.insertParses(xml, tempdir + "/" + os.path.basename(files[analysesSetName])[:-len(".tar.gz")] + "/McClosky-Charniak/dep", None, extraAttributes={"stanfordSource":"BioNLP'09"})
            print >> sys.stderr, "Removing temporary directory", tempdir
            shutil.rmtree(tempdir)
    else: # use official BioNLP'11 parses
        for i in range(len(datasets)):
            print >> sys.stderr, "---------------", "Inserting analyses " + str(i+1) + "/" + str(len(datasets)), "---------------"
            setName = datasets[i]
            print >> sys.stderr, "Inserting", setName, "analyses"
            tempdir = tempfile.mkdtemp()
            Utils.Download.extractPackage(files[corpus + "_" + setName.upper() + "_TOKENS"], tempdir)
            Utils.Download.extractPackage(files[corpus + "_" + setName.upper() + "_McCC"], tempdir)
            print >> sys.stderr, "Making sentences"
            Tools.SentenceSplitter.makeSentences(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_TOKENS"])[:-len(".tar.gz")].split("-", 1)[-1] + "/tokenised", None)
            print >> sys.stderr, "Inserting McCC parses"
            Tools.CharniakJohnsonParser.insertParses(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCC"])[:-len(".tar.gz")].split("-", 2)[-1] + "/mccc/ptb", None, extraAttributes={"source":"BioNLP'11"})
            print >> sys.stderr, "Inserting Stanford conversions"
            Tools.StanfordParser.insertParses(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCC"])[:-len(".tar.gz")].split("-", 2)[-1] + "/mccc/sd_ccproc", None, extraAttributes={"stanfordSource":"BioNLP'11"})
            print >> sys.stderr, "Removing temporary directory", tempdir
            shutil.rmtree(tempdir)

def processParses(xml, splitTarget="McCC"):
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
    optparser.add_option("-o", "--outdir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), dest="outdir", help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, dest="downloaddir", help="directory to download corpus files to")
    optparser.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="save intermediate corpus files")
    optparser.add_option("--forceDownload", default=False, action="store_true", dest="forceDownload", help="re-download all source files")
    (options, args) = optparser.parse_args()
    
    Stream.openLog(os.path.join(options.outdir, "conversion-log.txt"))
    convert(options.corpora.split(","), options.outdir, options.downloaddir, options.forceDownload, options.intermediateFiles)