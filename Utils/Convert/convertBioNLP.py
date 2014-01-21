import sys, os, time, shutil
import tempfile
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.STFormat.STTools as ST
import Utils.STFormat.ConvertXML as STConvert
import Utils.STFormat.Equiv
import Utils.STFormat.Validate
#import Utils.InteractionXML.RemoveUnconnectedEntities
import Utils.InteractionXML.DivideSets
import Utils.InteractionXML.MixSets
import Utils.InteractionXML.DeleteElements
import Utils.ProteinNameSplitter as ProteinNameSplitter
import Utils.Stream as Stream
import Utils.FindHeads as FindHeads
import Tools.SentenceSplitter
import Tools.BLLIPParser
import Tools.StanfordParser
import Utils.ElementTreeUtils as ETUtils
import Evaluators.BioNLP11GeniaTools as BioNLP11GeniaTools
import Utils.Download
import Utils.Settings as Settings
from Detectors.StructureAnalyzer import StructureAnalyzer

moveBI = ["PMID-10333516-S3", "PMID-10503549-S4", "PMID-10788508-S10", "PMID-1906867-S3",
          "PMID-9555886-S6", "PMID-10075739-S13", "PMID-10400595-S1", "PMID-10220166-S12"]
bioNLP13AnalysesTempDir = None

def installPreconverted(url="BIONLP_CORPORA", destPath=None, downloadPath=None, redownload=False, updateLocalSettings=False):
    print >> sys.stderr, "---------------", "Downloading preconverted corpora", "---------------"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "corpora")
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "corpora/download")
    Utils.Download.downloadAndExtract(Settings.URL[url], destPath, downloadPath, redownload=redownload)
    Settings.setLocal("CORPUS_DIR", destPath, updateLocalSettings)

def installEvaluators(destPath=None, downloadPath=None, redownload=False, updateLocalSettings=False):
    print >> sys.stderr, "---------------", "Downloading BioNLP Shared Task evaluators", "---------------"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "tools/evaluators")
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "tools/download")
    Utils.Download.downloadAndExtract(Settings.URL["BIONLP11_EVALUATORS"], destPath, downloadPath, redownload=redownload)
    Settings.setLocal("BIONLP_EVALUATOR_DIR", destPath, updateLocalSettings)
    Settings.setLocal("BIONLP_EVALUATOR_GOLD_DIR", os.path.join(destPath, "gold"), updateLocalSettings)
    
def downloadCorpus(corpus, destPath=None, downloadPath=None, clear=False):
    print >> sys.stderr, "---------------", "Downloading BioNLP Shared Task files", "---------------"
    downloaded = {}
    if destPath == None:
        finalDestPath = os.path.join(Settings.DATAPATH, "corpora/BioNLP11-original")
    else:
        finalDestPath = destPath
    for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
        identifier = corpus + setName
        parentIdentifier = identifier.replace("BB13T2", "BB13").replace("BB13T3", "BB13")
        if parentIdentifier in Settings.URL:
            downloaded[identifier] = Utils.Download.download(Settings.URL[parentIdentifier], downloadPath, clear=clear)
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "download")
    if corpus in ["REL11", "REN11", "CO11"]:
        if destPath == None:
            teesParseFinalDestPath = os.path.join(Settings.DATAPATH, "TEES-parses")
        else:
            teesParseFinalDestPath = os.path.join(destPath, "TEES-parses")
        Utils.Download.downloadAndExtract(Settings.URL["TEES_PARSES"], teesParseFinalDestPath, downloadPath, redownload=clear)
        downloaded["TEES_PARSES"] = teesParseFinalDestPath
    elif corpus == "GE09" or corpus.endswith("11"):
        if corpus == "GE09":
            analyses = ["_ANALYSES"]
        else:
            analyses = ["_TOKENS", "_McCC"]
        for analysis in analyses:
            for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
                identifier = corpus + setName + analysis
                if identifier in Settings.URL:
                    downloaded[identifier] = Utils.Download.download(Settings.URL[identifier], downloadPath + "/support/", clear=clear)
    else:
        assert corpus.endswith("13") or corpus.endswith("13T2") or corpus.endswith("13T3")
        for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
            cTag = corpus.replace("13T2", "13").replace("13T3","13")
            downloaded[corpus + setName + "_McCCJ"] = Utils.Download.download(Settings.URL[cTag + setName + "_McCCJ"], downloadPath + "/support/", clear=clear)
            downloaded[corpus + setName + "_TOK"] = Utils.Download.download(Settings.URL[cTag + setName + "_TOK"], downloadPath + "/support/", clear=clear)
    return downloaded

def convert(corpora, outDir=None, downloadDir=None, redownload=False, makeIntermediateFiles=True, evaluate=False, processEquiv=True, addAnalyses=True):
    global bioNLP13AnalysesTempDir
    
    if outDir == None:
        os.path.normpath(Settings.DATAPATH + "/corpora")
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    else:
        assert os.path.isdir(outDir)
    count = 1
    for corpus in corpora:
        print >> sys.stderr, "=======================", "Converting BioNLP Shared Task", corpus, "corpus ("+str(count)+"/"+str(len(corpora))+")", "======================="
        logFileName = outDir + "/conversion/" + corpus + "-conversion-log.txt"
        Stream.openLog(logFileName)
        downloaded = downloadCorpus(corpus, outDir, downloadDir, redownload)
        packageSubPath = None
        if corpus == "BB13T2":
            packageSubPath = "task_2"
        elif corpus == "BB13T3":
            packageSubPath = "task_3"
        convertDownloaded(outDir, corpus, downloaded, makeIntermediateFiles, evaluate, processEquiv=processEquiv, addAnalyses=addAnalyses, packageSubPath=packageSubPath)
        Stream.closeLog(logFileName)
        count += 1
    
    if bioNLP13AnalysesTempDir != None:
        shutil.rmtree(bioNLP13AnalysesTempDir)
        bioNLP13AnalysesTempDir = None

def corpusRENtoASCII(xml):
    print >> sys.stderr, "Converting REN11 corpus to ASCII"
    for document in xml.getiterator("document"):
        text = document.get("text")
        text = text.replace(u"\xc3\xb6", u"a")
        text = text.replace(u"\xc3\xa4", u"a")
        text = text.replace(u"\xc3\xa9", u"e")
        text = text.replace("and Wikstram, M. (1991) Eur. J. Biochem. 197", "and Wikstrom, M. (1991) Eur. J. Biochem. 197")
        document.set("text", text)

def checkAttributes(xml):
    for element in xml.getiterator():
        for key in element.attrib.keys():
            assert element.get(key) != None, (element.tag, key, element.attrib)

def convertDownloaded(outdir, corpus, files, intermediateFiles=True, evaluate=True, processEquiv=True, addAnalyses=True, packageSubPath=None):
    global moveBI
    if evaluate:
        workdir = outdir + "/conversion/" + corpus
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir)
    
    print >> sys.stderr, "---------------", "Converting to XML", "---------------"
    # All datasets are processed as one XML, to ensure all the steps (parse modification etc.) are
    # applied equally
    #print corpus, files
    datasets = []
    for setName in ["devel", "train", "test"]:
        if corpus + "_" + setName.upper() in files:
            datasets.append(setName)
    bigfileName = os.path.join(outdir, corpus + "-" + "-and-".join(datasets))
    documents = []
    for setName in datasets:
        sourceFile = files[corpus + "_" + setName.upper()]
        print >> sys.stderr, "Reading", setName, "set from", sourceFile
        docs = ST.loadSet(sourceFile, setName, "a2", subPath=packageSubPath)
        print >> sys.stderr, "Read", len(docs), "documents"
        documents.extend(docs)
        
    if len(docs) > 0 and docs[0].license != None:
        licenseFile = open(os.path.join(outdir, corpus + "-LICENSE"), "wt")
        licenseFile.write(docs[0].license)
        licenseFile.close()
    
    if processEquiv:
        print >> sys.stderr, "Resolving equivalences"
        Utils.STFormat.Equiv.process(documents)
    else:
        print >> sys.stderr, "Skipping resolving of equivalences"
    
    if evaluate:
        #print >> sys.stderr, "Checking data validity"
        #for doc in documents:
        #    Utils.STFormat.Validate.validate(doc.events, simulation=True, verbose=True, docId=doc.id)
        print >> sys.stderr, "Writing all documents to geniaformat"
        ST.writeSet(documents, os.path.join(workdir, "all-geniaformat"), resultFileTag="a2", debug=False)
    
    if intermediateFiles:
        print >> sys.stderr, "Converting to XML, writing combined corpus to", bigfileName+"-documents.xml"
        xml = STConvert.toInteractionXML(documents, corpus, bigfileName+"-documents.xml")
    else:
        print >> sys.stderr, "Converting to XML"
        xml = STConvert.toInteractionXML(documents, corpus, None)
    
    if corpus == "BI11":
        Utils.InteractionXML.MixSets.mixSets(xml, None, set(moveBI), "train", "devel")
    if corpus == "REN11":
        corpusRENtoASCII(xml)
    
    if addAnalyses:
        insertAnalyses(xml, corpus, datasets, files, bigfileName, packageSubPath=packageSubPath)
    else:
        print >> sys.stderr, "Skipping adding analyses"
    if intermediateFiles:
        print >> sys.stderr, "Writing combined corpus", bigfileName+"-sentences.xml"
        ETUtils.write(xml, bigfileName+"-sentences.xml")
    processParses(xml)
    
    # A hack for GRN13 task that breaks the official BioNLP Shared Task convention of trigger and event having the same type.
    # Let's remove the unused triggers, so that there won't be an unusable node class. There is no clean way to fix this,
    # as the GRN13 task not following the official rules introduces yet another mechanism into the Shared Task format,
    # and supporting this would require rewriting everything.
    if corpus == "GRN13":
        Utils.InteractionXML.DeleteElements.processCorpus(xml, None, {"entity":{"type":["Action"]}})
    
    print >> sys.stderr, "---------------", "Writing corpora", "---------------"
    checkAttributes(xml)
    # Write out converted data
    if intermediateFiles:
        print >> sys.stderr, "Writing combined corpus", bigfileName+".xml"
        ETUtils.write(xml, bigfileName+".xml")
    print >> sys.stderr, "Dividing into sets"
    Utils.InteractionXML.DivideSets.processCorpus(xml, outdir, corpus, ".xml")
    
    if evaluate and "devel" in datasets:
        print >> sys.stderr, "---------------", "Evaluating conversion", "---------------"
        if corpus != "REL11": # Task 1 (removal of Entity-entities) cannot work for REL
            print >> sys.stderr, "Evaluating task 1 back-conversion"
            STConvert.toSTFormat(os.path.join(outdir, corpus + "-devel.xml"), workdir + "/roundtrip/" + corpus + "-devel" + "-task1", outputTag="a2", skipArgs=["Site"])
            BioNLP11GeniaTools.evaluate(workdir + "/roundtrip/" + corpus + "-devel" + "-task1", corpus + ".1")
        print >> sys.stderr, "Evaluating task 2 back-conversion"
        STConvert.toSTFormat(os.path.join(outdir, corpus + "-devel.xml"), workdir + "/roundtrip/" + corpus + "-devel" + "-task2", outputTag="a2")
        BioNLP11GeniaTools.evaluate(workdir + "/roundtrip/" + corpus + "-devel" + "-task2", corpus + ".2")
        print >> sys.stderr, "Note! Evaluation of Task 2 back-conversion can be less than 100% due to site-argument mapping"
    
    # Check what was produced by the conversion
    print >> sys.stderr, "---------------", "Corpus Structure Analysis", "---------------"
    analyzer = StructureAnalyzer()
    analyzer.analyze([xml])
    print >> sys.stderr, analyzer.toString()

def insertAnalyses(xml, corpus, datasets, files, bigfileName, packageSubPath=None):
    global bioNLP13AnalysesTempDir
    
    if packageSubPath != None:
        packageSubPath = "/" + packageSubPath
    else:
        packageSubPath = ""
    if "TEES_PARSES" in files: # corpus for which no official parse exists
        print >> sys.stderr, "---------------", "Inserting TEES-generated analyses", "---------------"
        extractedFilename = files["TEES_PARSES"] + "/" + corpus #[:-2]
        print >> sys.stderr, "Making sentences"
        Tools.SentenceSplitter.makeSentences(xml, extractedFilename, None)
        print >> sys.stderr, "Inserting McCC parses"
        Tools.BLLIPParser.insertParses(xml, extractedFilename, None, extraAttributes={"source":"TEES-preparsed"})
        print >> sys.stderr, "Inserting Stanford conversions"
        Tools.StanfordParser.insertParses(xml, extractedFilename, None, extraAttributes={"stanfordSource":"TEES-preparsed"})
    elif corpus == "GE09": # the BioNLP'09 corpus
        for i in range(len(datasets)):
            print >> sys.stderr, "---------------", "Inserting analyses " + str(i+1) + "/" + str(len(datasets)), "---------------"
            setName = datasets[i]
            print >> sys.stderr, "Inserting", setName, "analyses"
            tempdir = tempfile.mkdtemp()
            analysesSetName = corpus + "_" + setName.upper() + "_ANALYSES"
            packagePath = Utils.Download.getTopDir(tempdir, Utils.Download.extractPackage(files[analysesSetName], tempdir))
            print >> sys.stderr, "Making sentences"
            Tools.SentenceSplitter.makeSentences(xml, packagePath + "/tokenized", None, escDict=Tools.BLLIPParser.escDict)
            print >> sys.stderr, "Inserting McCC parses"
            Tools.BLLIPParser.insertParses(xml, packagePath + "/McClosky-Charniak/pstree", None, extraAttributes={"source":"BioNLP'09"})
            print >> sys.stderr, "Inserting Stanford conversions"
            Tools.StanfordParser.insertParses(xml, packagePath + "/McClosky-Charniak/dep", None, skipExtra=1, extraAttributes={"stanfordSource":"BioNLP'09"})
            print >> sys.stderr, "Removing temporary directory", tempdir
            shutil.rmtree(tempdir)
    elif corpus.endswith("11"): # use official BioNLP'11 parses
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
            Tools.BLLIPParser.insertParses(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCC"])[:-len(".tar.gz")].split("-", 2)[-1] + "/mccc/ptb", None, extraAttributes={"source":"BioNLP'11"})
            print >> sys.stderr, "Inserting Stanford conversions"
            Tools.StanfordParser.insertParses(xml, tempdir + "/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCC"])[:-len(".tar.gz")].split("-", 2)[-1] + "/mccc/sd_ccproc", None, extraAttributes={"stanfordSource":"BioNLP'11"})
            print >> sys.stderr, "Removing temporary directory", tempdir
            shutil.rmtree(tempdir)
    else: # use official BioNLP'13 parses
        for i in range(len(datasets)):
            print >> sys.stderr, "---------------", "Inserting analyses " + str(i+1) + "/" + str(len(datasets)), "---------------"
            setName = datasets[i]
            print >> sys.stderr, "Inserting", setName, "analyses"
            tempdir = tempfile.mkdtemp()
            Utils.Download.extractPackage(files[corpus + "_" + setName.upper() + "_TOK"], tempdir + "/tok")
            Utils.Download.extractPackage(files[corpus + "_" + setName.upper() + "_McCCJ"], tempdir + "/parse")
            subPath = ""
            if corpus.endswith("T2"):
                subPath = "/task_2"
            if corpus.endswith("T3"):
                subPath = "/task_3"
            print >> sys.stderr, "Making sentences"
            Tools.SentenceSplitter.makeSentences(xml, tempdir + "/tok/" + os.path.basename(files[corpus + "_" + setName.upper() + "_TOK"]).rsplit("_", 2)[0] + subPath, None)
            print >> sys.stderr, "Inserting McCC parses"
            Tools.BLLIPParser.insertParses(xml, tempdir + "/parse/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCCJ"]).rsplit("_", 2)[0] + subPath, None, extraAttributes={"source":"BioNLP'13"})
            print >> sys.stderr, "Inserting Stanford conversions"
            Tools.StanfordParser.insertParses(xml, tempdir + "/parse/" + os.path.basename(files[corpus + "_" + setName.upper() + "_McCCJ"]).rsplit("_", 2)[0] + subPath, None, extraAttributes={"stanfordSource":"BioNLP'13"})
            print >> sys.stderr, "Removing temporary directory", tempdir
            shutil.rmtree(tempdir)

def processParses(xml, splitTarget="McCC"):
    print >> sys.stderr, "---------------", "Protein Name Splitting", "---------------"
    #ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
    ProteinNameSplitter.mainFunc(xml, None, splitTarget, removeOld=True)
    print >> sys.stderr, "---------------", "Head Detection", "---------------"
    #xml = FindHeads.findHeads(xml, "split-"+splitTarget, tokenization=None, output=None, removeExisting=True)
    xml = FindHeads.findHeads(xml, splitTarget, tokenization=None, output=None, removeExisting=True)

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
    optparser = OptionParser(usage="%prog [options]\nBioNLP Shared Task corpus conversion")
    optparser.add_option("-c", "--corpora", default=None, dest="corpora", help="corpus names in a comma-separated list, e.g. \"GE11,EPI11,ID11\"")
    optparser.add_option("-e", "--evaluators", default=False, action="store_true", dest="evaluators", help="Install evaluators")
    optparser.add_option("-o", "--outdir", default=None, dest="outdir", help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, dest="downloaddir", help="directory to download corpus files to")
    optparser.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="save intermediate corpus files")
    optparser.add_option("--forceDownload", default=False, action="store_true", dest="forceDownload", help="re-download all source files")
    optparser.add_option("--noEquiv", default=False, action="store_true", dest="noEquiv", help="Don't interpret equiv annotation into duplicate events")
    optparser.add_option("--noAnalyses", default=False, action="store_true", dest="noAnalyses", help="Don't add parses")
    optparser.add_option("--evaluate", default=False, action="store_true", dest="evaluate", help="Convert devel sets back to ST format and evaluate")
    (options, args) = optparser.parse_args()
    
    if options.evaluators:
        installEvaluators(options.outdir, options.downloaddir, options.forceDownload)
    if options.corpora != None:
        options.corpora = options.corpora.replace("ALL11", "GE11,EPI11,ID11,BB11,BI11,CO11,REL11,REN11")
        options.corpora = options.corpora.replace("ALL13", "GE13,CG13,PC13,GRO13,GRN13,BB13T2,BB13T3")
        #Stream.openLog(os.path.join(options.outdir, "conversion-log.txt"))
        convert(options.corpora.split(","), options.outdir, options.downloaddir, options.forceDownload, options.intermediateFiles, evaluate=options.evaluate, processEquiv=not options.noEquiv, addAnalyses=not options.noAnalyses)