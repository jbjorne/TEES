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
import Utils.Range as Range
from Detectors.StructureAnalyzer import StructureAnalyzer
from Detectors.Preprocessor import Preprocessor
import Core.Split

def downloadFiles(downloadPath=None, extractDir=None, clear=False):
    extracted = {}
    print >> sys.stderr, "---------------", "Downloading DDI'13 Shared Task files", "---------------"
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "corpora/download")
    for dataset in ["DDI13_TRAIN", 
                    "DDI13_TRAIN_TEES_PARSES",
                    "DDI13_TEST_TASK_9.1",
                    "DDI13_TEST_TASK_9.2",
                    "DDI13_TEST_TASK_9.1_TEES_PARSES",
                    "DDI13_TEST_TASK_9.2_TEES_PARSES"]:
        if Settings.URL[dataset] != None:
            downloaded = Utils.Download.download(Settings.URL[dataset], downloadPath, clear=clear)
            print >> sys.stderr, "Extracting package", downloaded
            extracted[dataset] = Utils.Download.extractPackage(downloaded, extractDir)
            if dataset == "DDI13_TRAIN":
                if len(extracted[dataset]) == 1:
                    extracted[dataset] = extracted[dataset][0]
                else:
                    extracted[dataset] = Utils.Download.getTopDir(extractDir, extracted[dataset])
            else:
                # take top level directories
                for i in range(len(extracted[dataset])):
                    if "/" not in extracted[dataset][i] or (extracted[dataset][i].endswith("/") and extracted[dataset][i].count("/") == 1):
                        extracted[dataset][i] = os.path.join(extractDir, extracted[dataset][i])
                    else:
                        extracted[dataset][i] = None
                extracted[dataset] = filter(lambda a: a != None, extracted[dataset])
        else:
            extracted[dataset] = None
    return extracted

def getCorpusXML():
    corpus = ET.ElementTree(ET.Element("corpus"))
    corpusRoot = corpus.getroot()
    corpusRoot.set("source", "DDI13")
    return corpus

def divideSets(xml, sourceSet, numFolds):
    docCount = 0
    for doc in xml.getiterator("document"):
        if doc.get("set") == sourceSet:
            docCount += 1
    
    division = Core.Split.getFolds(docCount, numFolds, 0)
    count = 0
    for doc in xml.getiterator("document"):
        if doc.get("set") == sourceSet:
            doc.set("set", doc.get("set") + str(division[count]))
            count += 1

def processElements(xml):
    for ddi in xml.getiterator("ddi"):
        ddi.tag = "interaction"
    for entity in xml.getiterator("entity"):
        entity.set("given", "True")
        # Reformat disjoint character offsets and update character range format for TEES 2.0+
        charOffsets = Range.charOffsetToTuples(entity.get("charOffset"), rangeSep=";")
        updatedCharOffsets = []
        for charOffset in charOffsets:
            updatedCharOffsets.append( (charOffset[0], charOffset[1]+1) )
        entity.set("charOffset", Range.tuplesToCharOffset(updatedCharOffsets))
        #entity.set("charOffset", entity.get("charOffset").replace(";", ","))

def parseXML(xml, intermediateFileDir, debug=False):
    preprocessor = Preprocessor()
    preprocessor.setArgForAllSteps("debug", debug)
    preprocessor.stepArgs("PARSE")["requireEntities"] = False
    #preprocessor.process(xml, intermediateFileDir, fromStep="SPLIT-SENTENCES", toStep="FIND-HEADS", omitSteps=["NER"])
    #preprocessor.process(xml, intermediateFileDir, fromStep="PARSE", toStep="FIND-HEADS")
    # Entity name splitting is omitted as this data may be used for predicting entities
    preprocessor.process(xml, intermediateFileDir, omitSteps=["CONVERT", "SPLIT-SENTENCES", "NER", "SPLIT-NAMES", "DIVIDE-SETS"])

def combineXML(corpusXML, setName, dataDirs, subDirs=["DrugBank", "MedLine"]):
    # Add all documents into one XML
    ids = {}
    if isinstance(dataDirs, basestring):
        dataDirs = []
    for dataDir in dataDirs:        
        if dataDir.startswith(".") or dataDir.startswith("_"):
            continue
        for subDir in [""] + subDirs:
            inDir = dataDir + "/" + subDir
            if "/." in dataDir or "/_" in dataDir: # attempt to survive the junk directories
                continue
            if os.path.exists(inDir):
                for filename in sorted(os.listdir(inDir)):
                    if filename.endswith(".xml"):
                        print >> sys.stderr, "Reading", filename
                        xml = ETUtils.ETFromObj(os.path.join(inDir, filename))
                        document = xml.getroot()
                        assert document.tag == "document"
                        assert document.get("id") not in ids, (document.get("id"), os.path.join(inDir, filename), ids[document.get("id")])
                        ids[document.get("id")] = os.path.join(inDir, filename)
                        document.set("source", os.path.join(subDir, filename))
                        if setName != None:
                            document.set("set", setName)
                        corpusXML.append(document)

def convertDDI13(outDir, downloadDir=None, datasets=["DDI13_TRAIN", "DDI13_TEST_TASK_9.1", "DDI13_TEST_TASK_9.2"], redownload=False, insertParses=True, parse=False, makeIntermediateFiles=True, debug=False):
    cwd = os.getcwd()
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    os.chdir(outDir)
    logFileName = os.path.join(outDir, "DDI13-conversion-log.txt")
    Stream.openLog(logFileName)
    print >> sys.stderr, "=======================", "Converting DDI'13 corpus", "======================="
    
    tempdir = tempfile.mkdtemp()
    downloaded = downloadFiles(downloadDir, tempdir, redownload)
    
    for dataset in datasets:       
        corpusTree = getCorpusXML()
        xml = corpusTree.getroot()
        print >> sys.stderr, "Merging input XMLs"
        assert downloaded[dataset] != None
        combineXML(xml, "train", downloaded[dataset], subDirs=["DrugBank", "MedLine", "NER"])
        print >> sys.stderr, "Processing elements"
        processElements(xml)
        
        if dataset == "DDI13_TRAIN":
            print >> sys.stderr, "Dividing training set into folds"
            divideSets(xml, "train", 10)
        else:
            for doc in xml.getiterator("document"):
                doc.set("set", "test")

        if parse:
            print >> sys.stderr, "Parsing"
            parseXML(corpusTree, os.path.join(tempdir, "parsing"), debug)
        elif insertParses:
            assert parse == False
            print >> sys.stderr, "Inserting McCC parses"
            Tools.BLLIPParser.insertParses(corpusTree, downloaded[dataset + "_TEES_PARSES"], None, extraAttributes={"source":"TEES"})
            print >> sys.stderr, "Inserting Stanford conversions"
            Tools.StanfordParser.insertParses(corpusTree, downloaded[dataset + "_TEES_PARSES"], None, extraAttributes={"stanfordSource":"TEES"})
        # Check what was produced by the conversion
        print >> sys.stderr, "---------------", "Corpus Structure Analysis", "---------------"
        analyzer = StructureAnalyzer()
        analyzer.analyze([xml])
        print >> sys.stderr, analyzer.toString()
        if "9.1" in dataset:
            outFileName = os.path.join(outDir, "DDI13-test-task9.1.xml")
        elif "9.2" in dataset:
            outFileName = os.path.join(outDir, "DDI13-test-task9.2.xml")
        else:
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
    optparser.add_option("-p", "--parse", default=False, action="store_true", dest="parse", help="Parse with preprocessor")
    optparser.add_option("-n", "--noparses", default=False, action="store_true", dest="noparses", help="Don't insert parses")
    optparser.add_option("--redownload", default=False, action="store_true", dest="redownload", help="re-download all source files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Keep temporary files")
    optparser.add_option("-s", "--datasets", default="DDI13_TRAIN,DDI13_TEST_TASK_9.1,DDI13_TEST_TASK_9.2", dest="datasets", help="Datasets to process")
    (options, args) = optparser.parse_args()
    
    options.datasets = options.datasets.split(",")
    convertDDI13(options.outdir, options.downloaddir, options.datasets, options.redownload, not options.noparses, options.parse, options.intermediateFiles, options.debug)
