import sys, os
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
from collections import defaultdict
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Settings as Settings
import Utils.Stream as Stream
import Utils.Download
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range

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

def updateXML(root, removeParses=True):
    counts = defaultdict(int)
    for document in root.findall("document"):
        counts["documents"] += 1
        for sentence in document.findall("sentence"):
            counts["sentences"] += 1
            analyses = sentence.find("sentenceanalyses")
            if analyses != None:
                counts["analyses"] += 1
                if removeParses:
                    counts["removed-analyses"] += 1
                    sentence.remove(analyses)
            sentenceText = sentence.get("text")
            for entity in sentence.findall("entity"):
                offset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
                offset = (offset[0], offset[1] + 1)
                assert sentenceText[offset[0]:offset[1]] == entity.get("text")
                entity.set("charOffset", Range.tuplesToCharOffset(offset))
            numInteractions = 0
            for pair in sentence.findall("pair"):
                sentence.remove(pair)
                if pair.get("interaction") == "True":
                    del pair.attrib["interaction"]
                    pair.set("id", pair.get("id").replace(".p", ".i"))
                    ET.SubElement(sentence, "interaction", pair.attrib)

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
    print >> sys.stderr, "Updating Interaction XML format"
    xml = updateXML
    
    if logPath != None:
        Stream.closeLog(logPath)
    return xml  

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nFive PPI corpora conversion")
    optparser.add_option("-c", "--corpora", default=None, help="corpus names in a comma-separated list")
    optparser.add_option("-o", "--outdir", default=None, help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, help="directory to download corpus files to")
    optparser.add_option("--forceDownload", default=False, action="store_true", dest="forceDownload", help="re-download all source files")
    optparser.add_option("--logPath", default="AUTO", help="AUTO, None, or a path")
    optparser.add_option("--debug", default=False, action="store_true", help="")
    (options, args) = optparser.parse_args()
    
    convert(options.corpora, options.outdir, options.downloaddir, options.forceDownload, True, options.logPath)