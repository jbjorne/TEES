import sys, os
import tempfile
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
import Utils.InteractionXML.DivideSets
import Utils.InteractionXML.MakeSets as MakeSets

PPI_CORPORA = ["AIMed", "BioInfer", "HPRD50", "IEPA", "LLL"]

def downloadCorpus(corpus, destPath=None, downloadPath=None, clear=False):
    print >> sys.stderr, "---------------", "Downloading PPI corpus", corpus, "files", "---------------"
    downloaded = {}
    downloadPath = downloadPath if downloadPath else os.path.join(Settings.DATAPATH, "download")
    identifier = corpus + "_LEARNING_FORMAT"
    downloaded[identifier] = Utils.Download.download(Settings.URL[identifier], downloadPath, clear=clear)
    downloaded["PPI_EVALUATION_STANDARD"] = Utils.Download.download(Settings.URL["PPI_EVALUATION_STANDARD"], downloadPath, clear=clear)
    return downloaded

def convert(corpora, outDir=None, downloadDir=None, redownload=False, removeAnalyses=True, develFraction=0.3, logPath=None):
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
        print >> sys.stderr, "=======================", "Converting PPI", corpus, "corpus ("+str(i+1)+"/"+str(len(corpora))+")", "======================="
        xml = convertCorpus(corpus, outDir, downloadDir, redownload, removeAnalyses, develFraction, logPath)
    return xml if len(corpora) == 1 else None

def updateXML(root, removeAnalyses=True):
    counts = defaultdict(int)
    for document in root.findall("document"):
        sentencePos = 0
        counts["documents"] += 1
        for sentence in document.findall("sentence"):
            counts["sentences"] += 1
            # Remove the original parses
            analyses = sentence.find("sentenceanalyses")
            if analyses != None:
                counts["analyses"] += 1
                if removeAnalyses:
                    counts["removed-analyses"] += 1
                    sentence.remove(analyses)
            # Add an artifical sentence offset so that sentences can be exported as a single document
            sentenceText = sentence.get("text")
            sentence.set("charOffset", Range.tuplesToCharOffset((sentencePos, sentencePos + len(sentenceText))))
            # Update the character offsets of all entities from the old format (begin,end) to the new one (begin,end+1)
            for entity in sentence.findall("entity"):
                counts["entities"] += 1
                offsets = [(x[0], x[1] + 1) for x in Range.charOffsetToTuples(entity.get("charOffset"))]
                entityText = entity.get("text")
                for offset, entitySpan in zip(offsets, [sentenceText[x[0]:x[1]] for x in offsets]):
                    counts["entity-offsets"] += 1
                    lenOffset = offset[1] - offset[0]
                    offsetText, entityText = entityText[:lenOffset].strip(), entityText[lenOffset:].strip()
                    assert offsetText == entitySpan, (offsets, (entity.get("text"), entitySpan), (offsetText, entityText), sentenceText)
                entity.set("charOffset", Range.tuplesToCharOffset(offsets))
            # Convert positive pairs into interaction elements
            numInteractions = 0
            for pair in sentence.findall("pair"):
                counts["pairs"] += 1
                sentence.remove(pair)
                if pair.get("interaction") == "True":
                    del pair.attrib["interaction"]
                    pair.set("id", pair.get("id").rsplit(".", 1)[0] + ".i" + str(numInteractions))
                    pair.set("type", "PPI")
                    ET.SubElement(sentence, "interaction", pair.attrib)
                    numInteractions += 1
                    counts["interactions"] += 1
            sentencePos += len(sentenceText) + 1
    print >> sys.stderr, "Updated Interaction XML format:", dict(counts)
    return root

def addSets(corpus, xml, evalStandardDownloadPath, evalStandardPackageDir="ppi-eval-standard"):
    #evalStandardExtractPath = os.path.join(tempfile.gettempdir(), "PPIEvalStandard")
    evalStandardPath = os.path.join(tempfile.gettempdir(), evalStandardPackageDir)
    if not os.path.exists(evalStandardPath):
        print >> sys.stderr, "Extracting evaluation standard from", evalStandardDownloadPath
        Utils.Download.extractPackage(evalStandardDownloadPath, tempfile.gettempdir())
    print >> sys.stderr, "Using extracted evaluation standard at", evalStandardPath
    assert os.path.exists(evalStandardPath)
    docSets = {}
    for dataSet in "train", "test":
        dataSetXMLPath = os.path.join(evalStandardPath, dataSet, corpus + "-" + dataSet + ".xml")
        print >> sys.stderr, "Loading evaluation standard XML from", dataSetXMLPath
        dataSetXML = ETUtils.ETFromObj(dataSetXMLPath)
        for document in dataSetXML.getroot().findall("document"):
            assert document.get("id") not in docSets
            docSets[document.get("id")] = {"set":dataSet, "element":document}
    print >> sys.stderr, "Assigning sets"
    counts = defaultdict(int)
    for document in xml.findall("document"):
        counts["documents"] += 1
        docId = document.get("id")
        if docId in docSets:
            counts["documents-in-eval-standard"] += 1
            document.set("set", docSets[docId]["set"])
            if document.get("origId") != None and docSets[docId]["element"].get("origId") != None:
                assert document.get("origId") == docSets[docId]["element"].get("origId"), docId
                counts["documents-match-by-origId"] += 1
            counts["eval-standard-set:" + docSets[docId]["set"]] += 1
        else:
            print >> sys.stderr, "Warning, removing document", document.get("id"), "which is not included in the PPI evaluation standard"
            counts["missing-from-eval-standard"] += 1
            xml.remove(document)
    print >> sys.stderr, "PPI Evaluation Standard sets for corpus", corpus, "documents:", dict(counts)
    return xml

def convertCorpus(corpus, outDir=None, downloadDir=None, redownload=False, removeAnalyses=True, develFraction=0.3, logPath=None):
    assert corpus in PPI_CORPORA
    if logPath == "AUTO":
        logPath = outDir + "/conversion/" + corpus + "-conversion-log.txt" if outDir != None else None
    if logPath:
        Stream.openLog(logPath)
    print >> sys.stderr, "==========", "Converting PPI corpus", corpus, "=========="
    downloaded = downloadCorpus(corpus, outDir, downloadDir, redownload)
    print >> sys.stderr, "---------------", "Updating Interaction XML format", "---------------"
    print >> sys.stderr, "Loading", downloaded[corpus + "_LEARNING_FORMAT"]
    xml = ETUtils.ETFromObj(downloaded[corpus + "_LEARNING_FORMAT"])
    root = xml.getroot()
    updateXML(root, removeAnalyses)
    print >> sys.stderr, "---------------", "Adding sets from the PPI evaluation standard", "---------------"
    addSets(corpus, root, downloaded["PPI_EVALUATION_STANDARD"])
    if develFraction > 0.0:
        print >> sys.stderr, "---------------", "Generating devel set", "---------------"
        MakeSets.processCorpus(xml, None, "train", [("devel", develFraction), ("train", 1.0)], 1)
    if outDir != None:
        print >> sys.stderr, "---------------", "Writing corpus", "---------------"
        #if intermediateFiles:
        #print >> sys.stderr, "Writing combined corpus"
        #ETUtils.write(xml, os.path.join(outDir, corpus + ".xml"))
        print >> sys.stderr, "Dividing into sets"
        Utils.InteractionXML.DivideSets.processCorpus(xml, outDir, corpus, ".xml")
    
    if logPath != None:
        Stream.closeLog(logPath)
    return xml  

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nFive PPI corpora conversion")
    optparser.add_option("-c", "--corpora", default=None, help="corpus names in a comma-separated list")
    optparser.add_option("-o", "--outdir", default=None, help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, help="directory to download corpus files to")
    optparser.add_option("-f", "--develFraction", default=0.3, type=float, help="fraction of train set to use as devel set")
    optparser.add_option("-k", "--keepAnalyses", default=False, action="store_true", help="keep existing sentence analyses (parses)")
    optparser.add_option("--forceDownload", default=False, action="store_true", dest="forceDownload", help="re-download all source files")
    optparser.add_option("--logPath", default="AUTO", help="AUTO, None, or a path")
    optparser.add_option("--debug", default=False, action="store_true", help="")
    (options, args) = optparser.parse_args()
    
    convert(options.corpora, options.outdir, options.downloaddir, options.forceDownload, not options.keepAnalyses, options.develFraction, options.logPath)