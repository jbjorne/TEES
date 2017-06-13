import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Settings as Settings
import Utils.Stream as Stream

PPI_CORPORA = ["AIMed", "BioInfer", "HPRD50", "IEPA", "LLL"]

def downloadCorpus(corpus, destPath=None, downloadPath=None, clear=False):
    print >> sys.stderr, "---------------", "Downloading PPI corpus", corpus, "files", "---------------"
    downloaded = {}
    downloadPath = downloadPath if downloadPath else os.path.join(Settings.DATAPATH, "download")
    finalDestPath = destPath if destPath else os.path.join(Settings.DATAPATH, "corpora/BioNLP11-original") 
    for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
        identifier = corpus + setName
        parentIdentifier = identifier.replace("BB13T2", "BB13").replace("BB13T3", "BB13")
        if setName in ("_DEVEL", "_TRAIN") and parentIdentifier not in Settings.URL:
            raise Exception("Settings key '" + parentIdentifier + "' not found")
        if parentIdentifier in Settings.URL:
            downloaded[identifier] = Utils.Download.download(Settings.URL[parentIdentifier], downloadPath, clear=clear)
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
    elif corpus.endswith("13") or corpus.endswith("13T2") or corpus.endswith("13T3"):
        for setName in ["_DEVEL", "_TRAIN", "_TEST"]:
            cTag = corpus.replace("13T2", "13").replace("13T3","13")
            downloaded[corpus + setName + "_McCCJ"] = Utils.Download.download(Settings.URL[cTag + setName + "_McCCJ"], downloadPath + "/support/", clear=clear)
            downloaded[corpus + setName + "_TOK"] = Utils.Download.download(Settings.URL[cTag + setName + "_TOK"], downloadPath + "/support/", clear=clear)
    else:
        assert corpus.startswith("BB16") or corpus.startswith("SDB16")
    return downloaded

def convert(corpora, outDir=None, downloadDir=None, redownload=False, removeParses=True, logPath=None):
    if outDir == "AUTO":
        outDir = os.path.normpath(Settings.DATAPATH + "/corpora")
    elif outDir != None:
        if not os.path.exists(outDir):
            os.makedirs(outDir)
    assert os.path.isdir(outDir)
    
    if isinstance(corpora, basestring):
        corpora = corpora.split(",")
    else:
        corpora = PPI_CORPORA

    for i in range(len(corpora)):
        corpus = corpora[i]
        print >> sys.stderr, "=======================", "Converting PPI", corpus, "corpus ("+str(i)+"/"+str(len(corpora))+")", "======================="
        xml = convertCorpus(corpus, outDir, downloadDir, redownload, removeParses, logPath)
    return xml if len(corpora) == 1 else None

def convertCorpus(corpus, outDir=None, downloadDir=None, redownload=False, removeParses=True, logPath=None):
    assert corpus in PPI_CORPORA
    if logPath == "AUTO":
        logPath = outDir + "/conversion/" + corpus + "-conversion-log.txt" if outDir != None else None
    if logPath:
        Stream.openLog(logPath)
    print >> sys.stderr, "==========", "Converting PPI corpus", corpus, "=========="
    downloaded = downloadCorpus(corpus, outDir, downloadDir, redownload)
    
    if logPath != None:
        Stream.closeLog(logPath)
        

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nFive PPI corpora conversion")
    optparser.add_option("-c", "--corpora", default=None, dest="corpora", help="corpus names in a comma-separated list")
    optparser.add_option("-o", "--outdir", default=None, dest="outdir", help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, dest="downloaddir", help="directory to download corpus files to")
    optparser.add_option("--forceDownload", default=False, action="store_true", dest="forceDownload", help="re-download all source files")
    optparser.add_option("--logPath", default="AUTO", dest="logPath", help="AUTO, None, or a path")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
        