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

def getCorpusXML():
    corpus = ET.ElementTree(ET.Element("corpus"))
    corpusRoot = xmlTree.getroot()
    corpusRoot.set("source", "DDI13")
    return corpusRoot

def combineXML(corpusXML, setName, dataDir, subDirs=["DrugBank", "Medline"]):
    # Add all documents into one XML
    for subDir in subDirs:
        inDir = os.path.join(dataDir, subDir)
        for filename in sorted(os.listdir(inDir)):
            if filename.endswith(".xml"):
                print >> sys.stderr, "Reading", filename
                xml = ETUtils.ETFromObj(os.path.join(inDir, filename))
                document = xml.getroot()
                assert document.tag == "document"
                document.set("source", os.path.join(subDir, filename))
                if setName != None:
                    document.set("set", setName)
                corpusXML.append(document)

def convertDDI13(outDir, trainUnified=None, testUnified=None, downloadDir=None, redownload=False, makeIntermediateFiles=True, debug=False):
    cwd = os.getcwd()
    os.chdir(outDir)
    logFileName = os.path.join(outDir, "DDI13-conversion-log.txt")
    Stream.openLog(logFileName)
    print >> sys.stderr, "=======================", "Converting DDI'13 corpus", "======================="
    
    bigfileName = os.path.join(outDir, "DDI13")
    tempdir = None
    if trainUnified == None and "DDI3_TRAIN" in Settings.URL:
        trainUnified = Settings.URL["DDI3_TRAIN"]
    if testUnified == None and "DDI3_TEST" in Settings.URL:
        testUnified = Settings.URL["DDI13_TEST"]
    
    
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
    optparser.add_option("--redownload", default=False, action="store_true", dest="redownload", help="re-download all source files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Keep temporary files")
    (options, args) = optparser.parse_args()
    
    convertDDI13(options.outdir, None, None, options.downloaddir, options.redownload, options.intermediateFiles, options.debug)
