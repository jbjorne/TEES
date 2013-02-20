import sys, os
import shutil
import tempfile
import subprocess
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.STFormat.STTools as ST
import Utils.STFormat.ConvertXML as STConvert
import Utils.InteractionXML.RemoveUnconnectedEntities
import Utils.InteractionXML.DivideSets
import Utils.Download
import Utils.ProteinNameSplitter as ProteinNameSplitter
import Utils.Settings as Settings
import Utils.Stream as Stream
import Utils.FindHeads as FindHeads
import Tools.SentenceSplitter
import Tools.BLLIPParser
import Tools.StanfordParser
import xml.etree.cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
from Detectors.StructureAnalyzer import StructureAnalyzer
from Detectors.Preprocessor import Preprocessor

def downloadCorpus(downloadPath=None, clear=False):
    print >> sys.stderr, "---------------", "Downloading DDI'13 Shared Task files", "---------------"
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "corpora/download")
    downloaded = Utils.Download.download(Settings.URL["DDI13_TRAIN"], downloadPath, clear=clear)
    return downloaded

def getCorpusXML():
    corpus = ET.ElementTree(ET.Element("corpus"))
    corpusRoot = corpus.getroot()
    corpusRoot.set("source", "DDI13")
    return corpusRoot

def processElements(xml):
    for ddi in xml.getiterator("ddi"):
        ddi.tag = "interaction"
    for entity in xml.getiterator("entity"):
        entity.set("given", "True")

def parse(xml, intermediateFileDir, debug=False):
    preprocessor = Preprocessor()
    preprocessor.setArgForAllSteps("debug", debug)
    preprocessor.stepArgs("PARSE")["requireEntities"] = False
    #preprocessor.process(xml, intermediateFileDir, fromStep="SPLIT-SENTENCES", toStep="FIND-HEADS", omitSteps=["NER"])
    preprocessor.process(xml, intermediateFileDir, fromStep="PARSE", toStep="FIND-HEADS")

def combineXML(corpusXML, setName, dataDir, subDirs=["DrugBank", "MedLine"]):
    # Add all documents into one XML
    ids = set()
    for subDir in subDirs:
        inDir = os.path.join(dataDir, subDir)
        for filename in sorted(os.listdir(inDir)):
            if filename.endswith(".xml"):
                print >> sys.stderr, "Reading", filename
                xml = ETUtils.ETFromObj(os.path.join(inDir, filename))
                document = xml.getroot()
                assert document.tag == "document"
                assert document.get("id") not in ids
                ids.add(document.get("id"))
                document.set("source", os.path.join(subDir, filename))
                if setName != None:
                    document.set("set", setName)
                corpusXML.append(document)

def convertDDI13(outDir, downloadDir=None, redownload=False, parse=False, makeIntermediateFiles=True, debug=False):
    cwd = os.getcwd()
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    os.chdir(outDir)
    logFileName = os.path.join(outDir, "DDI13-conversion-log.txt")
    Stream.openLog(logFileName)
    print >> sys.stderr, "=======================", "Converting DDI'13 corpus", "======================="
    
    downloaded = downloadCorpus(downloadDir, redownload)
    tempdir = tempfile.mkdtemp()
    print >> sys.stderr, "Extracting package", downloaded
    Utils.Download.extractPackage(downloaded, tempdir)
        
    xml = getCorpusXML()
    print >> sys.stderr, "Merging input XMLs"
    combineXML(xml, "train", os.path.join(tempdir, "Train"), subDirs=["DrugBank", "MedLine"])
    print >> sys.stderr, "Processing elements"
    processElements(xml)
    if parse:
        print >> sys.stderr, "Parsing"
        parse(xml, os.path.join(tempdir, "parsing"), debug)
    # Check what was produced by the conversion
    print >> sys.stderr, "---------------", "Corpus Structure Analysis", "---------------"
    analyzer = StructureAnalyzer()
    analyzer.analyze([xml])
    print >> sys.stderr, analyzer.toString()
    outFileName = os.path.join(outDir, "DDI13-train.xml")
    print >> sys.stderr, "Writing output to", outFileName
    ETUtils.write(xml, outFileName)
    
    Stream.closeLog(logFileName)
    if not debug and tempdir != None:
        print >> sys.stderr, "Removing temporary directory", tempdir
        shutil.rmtree(tempdir)
    os.chdir(cwd)

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
    optparser = OptionParser(usage="%prog [options]\nDDI'13 Shared Task corpus conversion")
    optparser.add_option("-o", "--outdir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), dest="outdir", help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, dest="downloaddir", help="directory to download corpus files to")
    optparser.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="save intermediate corpus files")
    optparser.add_option("-p", "--parse", default=False, action="store_true", dest="parse", help="Keep temporary files")
    optparser.add_option("--redownload", default=False, action="store_true", dest="redownload", help="re-download all source files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Keep temporary files")
    (options, args) = optparser.parse_args()
    
    convertDDI13(options.outdir, options.downloaddir, options.redownload, options.parse, options.intermediateFiles, options.debug)
