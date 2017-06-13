import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Settings as Settings
import Utils.Stream as Stream
import Utils.Download
import Utils.ElementTreeUtils as ETUtils

PPI_CORPORA = ["AIMed", "BioInfer", "HPRD50", "IEPA", "LLL"]

def downloadCorpus(corpus, destPath=None, downloadPath=None, clear=False):
    print >> sys.stderr, "---------------", "Downloading PPI corpus", corpus, "files", "---------------"
    downloaded = {}
    downloadPath = downloadPath if downloadPath else os.path.join(Settings.DATAPATH, "download")
    identifier = corpus + "_LEARNING_FORMAT"
    downloaded[identifier] = Utils.Download.download(Settings.URL[identifier], downloadPath, clear=clear)
    downloaded["PPI_EVALUATION_STANDARD"] = Utils.Download.download(Settings.URL["PPI_EVALUATION_STANDARD"], downloadPath, clear=clear)
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
    print >> sys.stderr, "Loading", downloaded[corpus + "_LEARNING_FORMAT"]
    xml = ETUtils.ETFromObj(downloaded[corpus + "_LEARNING_FORMAT"])
    
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
    
        