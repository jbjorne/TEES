import sys, os, time
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
#import Utils.InteractionXML.CopyParse
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict
import Utils.Range as Range
import DDITools

def getSets(popSize):
    random.seed(15)
    pop = range(popSize)
    random.shuffle(pop)
    floatPopSize = float(popSize)
    trainSet = set(pop[0:int(0.5 * floatPopSize)])
    develSet = set(pop[int(0.5 * floatPopSize):int(0.75 * floatPopSize)])
    testSet = set(pop[int(0.75 * floatPopSize):])
    assert len(trainSet) + len(develSet) + len(testSet) == popSize
    
    division = []
    for i in xrange(popSize):
        if i in trainSet:
            division.append("t")
        elif i in develSet:
            division.append("d")
        else:
            division.append("e")
    assert len(division) == popSize
    return division

def fixEntities(xml):
    counts = defaultdict(int)
    for sentence in xml.getiterator("sentence"):
        sText = sentence.get("text")
        for entity in sentence.findall("entity"):
            charOffset = entity.get("charOffset")
            if charOffset == "-":
                assert False, str(entity)
                sentence.remove(entity)
                counts["removed-invalid"] += 1
            else:
                charOffset = Range.charOffsetToSingleTuple(charOffset)
                # fix length
                realLength = len(entity.get("text"))
                lenDiff = (charOffset[1] - charOffset[0] + 1) - realLength
                if lenDiff != realLength:
                    counts["incorrect-ent-offset"] += 1
                    counts["incorrect-ent-offset-diff"+str(lenDiff)] += 1
                    if abs(lenDiff) > 2:
                        print "Warning, lenDiff:", (lenDiff, charOffset, sText, entity.get("text"), entity.get("id"))
                charOffset = (charOffset[0], charOffset[0] + realLength)
                # find starting position
                entIndex = sText.find(entity.get("text"), charOffset[0])
                if entIndex == -1:
                    for i in [-1,-2,-3]:
                        entIndex = sText.find(entity.get("text"), charOffset[0]+i)
                        if entIndex != -1:
                            break
                if entIndex != 0: # could be lowercase
                    sTextLower = sText.lower()
                    for i in [0,-1,-2,-3]:
                        lowerEntIndex = sTextLower.find(entity.get("text"), charOffset[0]+i)
                        if lowerEntIndex != -1:
                            break
                    if lowerEntIndex != -1 and abs(lowerEntIndex - charOffset[0]) < abs(entIndex - charOffset[0]):
                        entIndex = lowerEntIndex
                assert entIndex != -1, (charOffset, sText, entity.get("text"), entity.get("id"))
                indexDiff = entIndex - charOffset[0]
                if indexDiff != 0:
                    counts["incorrect-ent-index"] += 1
                    counts["incorrect-ent-index-diff"+str(indexDiff)] += 1
                    print "Warning, indexDiff:", (indexDiff, charOffset, sText, entity.get("text"), entity.get("id"))
                # move offset       
                charOffset = (charOffset[0]+indexDiff, charOffset[1]+indexDiff)
                # validate new offset
                sEntity = sText[charOffset[0]:charOffset[1]]
                assert sEntity == entity.get("text") or sEntity.lower() == entity.get("text"), (charOffset, sText, entity.get("text"), entity.get("id"))
                entity.set("charOffset", Range.tuplesToCharOffset( (charOffset[0], charOffset[1])))
                entity.set("given", "True")
        for interaction in sentence.findall("interaction"):
            interaction.set("type", "DDI")
    print "Fix counts:", counts
    
def convertToInteractions(xml):
    print "Renaming pair-elements"
    counts = defaultdict(int)
    for sentence in xml.getiterator("sentence"):
        sentence.set("charOffset", "0-" + str(len(sentence.get("text"))) )
        for pair in sentence.findall("pair"):
            if pair.get("interaction") == "true":
                pair.tag = "interaction"
                pair.set("type", "DDI")
                counts["pos"] += 1
            else:
                sentence.remove(pair)
                counts["neg"] += 1
    print "Pair counts:", counts

def loadDocs(inDir, idStart=0):       
    print "Loading documents from", inDir
    sentences = {"positive":[], "negative":[]}
    docCounts = {}
    docById = {}
    documents = []
    for filename in sorted(os.listdir(inDir)):
        if filename.endswith(".xml"):
            print "Reading", filename,
            xml = ETUtils.ETFromObj(os.path.join(inDir, filename))
            for document in xml.getiterator("document"):
                counts = [0,0]          
                for sentence in document.findall("sentence"):
                    #sentence.set("document.get("origId") + "." + sentence.get("origId"))
                    truePairs = False
                    for pair in sentence.findall("pair"):
                        if pair.get("interaction") == "true":
                            truePairs = True
                            break
                    if truePairs:
                        counts[0] += 1
                        sentences["positive"].append(sentence)
                    else:
                        counts[1] += 1
                        sentences["negative"].append(sentence)
                assert document.get("id") not in docCounts
                docCounts[document.get("id")] = counts
                docById[document.get("id")] = document
                documents.append(document)
                print counts,
                #print ETUtils.toStr(document)
            print
    print "Positive sentences:", len(sentences["positive"])
    print "Negative sentences:", len(sentences["negative"])
    return documents, docById, docCounts

def convertDDI(outDir, downloadDir=None, redownload=False, makeIntermediateFiles=True, debug=False):
    cwd = os.getcwd()
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    os.chdir(outDir)
    logFileName = os.path.join(outDir, "DDI11-conversion-log.txt")
    Stream.openLog(logFileName)
    print >> sys.stderr, "=======================", "Converting DDI'11 corpus", "======================="
    corpusDir = outDir + "/DDI11-original"
    Utils.Download.downloadAndExtract(Settings.URL["DDI11_CORPUS"], corpusDir, downloadDir)
    
    bigfileName = os.path.join(outDir, "DDI11")
    #oldXML = ETUtils.ETFromObj(bigfileName+".xml")
    trainUnified = corpusDir + "/train"
    trainMTMX = corpusDir + "/train_MTMX"
    testUnified = corpusDir + "/test"
    testMTMX = corpusDir + "/test_MTMX"
    
    # Load main documents
    tempdir = tempfile.mkdtemp()
    print >> sys.stderr, "Temporary files directory at", tempdir
    documents, docById, docCounts = loadDocs(trainUnified)
    # Divide training data into a train and devel set
    sortedDocCounts = sorted(docCounts.iteritems(), key=lambda (k,v): (v,k), reverse=True)
    datasetCounts = {"train":[0,0], "devel":[0,0], "test":[0,0]}
    for i in range(0, len(sortedDocCounts)-3, 4):
        for j in [0,1]:
            docById[sortedDocCounts[i+j][0]].set("set", "train")
            datasetCounts["train"][0] += sortedDocCounts[i+j][1][0]
            datasetCounts["train"][1] += sortedDocCounts[i+j][1][1]
        docById[sortedDocCounts[i+2][0]].set("set", "train") #docById[sortedDocCounts[i+2][0]].set("set", "devel")
        docById[sortedDocCounts[i+3][0]].set("set", "devel") #docById[sortedDocCounts[i+3][0]].set("set", "test")
        datasetCounts["train"][0] += sortedDocCounts[i+2][1][0] #datasetCounts["devel"][0] += sortedDocCounts[i+2][1][0]
        datasetCounts["train"][1] += sortedDocCounts[i+2][1][1] #datasetCounts["devel"][1] += sortedDocCounts[i+2][1][1]
        datasetCounts["devel"][0] += sortedDocCounts[i+3][1][0] #datasetCounts["test"][0] += sortedDocCounts[i+3][1][0]
        datasetCounts["devel"][1] += sortedDocCounts[i+3][1][1] #datasetCounts["test"][1] += sortedDocCounts[i+3][1][1]
    for document in documents: # epajaolliset jaa yli
        if document.get("set") == None:
            document.set("set", "train")
    # Print division results
    print >> sys.stderr, datasetCounts
    for key in datasetCounts.keys():
        if datasetCounts[key][1] != 0:
            print key, datasetCounts[key][0] / float(datasetCounts[key][1])
        else:
            print key, datasetCounts[key][0], "/", float(datasetCounts[key][1])
    # Some of the train and test ids overlap. Let's change the train set ids, because test set ones are needed
    # for the final evaluation.
    changeIdCount = 1000
    for trainId in ['DrugDDI.d312', 'DrugDDI.d316', 'DrugDDI.d332', 'DrugDDI.d334', 'DrugDDI.d337', 
                    'DrugDDI.d342', 'DrugDDI.d349', 'DrugDDI.d354', 'DrugDDI.d373', 'DrugDDI.d379', 
                    'DrugDDI.d383', 'DrugDDI.d388', 'DrugDDI.d392', 'DrugDDI.d396', 'DrugDDI.d398', 
                    'DrugDDI.d409', 'DrugDDI.d411', 'DrugDDI.d415', 'DrugDDI.d425', 'DrugDDI.d430', 
                    'DrugDDI.d433', 'DrugDDI.d448', 'DrugDDI.d450', 'DrugDDI.d452', 'DrugDDI.d462', 
                    'DrugDDI.d467', 'DrugDDI.d470', 'DrugDDI.d474', 'DrugDDI.d480', 'DrugDDI.d482', 
                    'DrugDDI.d485', 'DrugDDI.d492', 'DrugDDI.d494', 'DrugDDI.d496', 'DrugDDI.d498', 
                    'DrugDDI.d500', 'DrugDDI.d503', 'DrugDDI.d506', 'DrugDDI.d518', 'DrugDDI.d523', 
                    'DrugDDI.d528', 'DrugDDI.d535', 'DrugDDI.d539', 'DrugDDI.d552', 'DrugDDI.d554', 
                    'DrugDDI.d558', 'DrugDDI.d561', 'DrugDDI.d570', 'DrugDDI.d578']:
        newId = "DrugDDI.d" + str(changeIdCount)
        print >> sys.stderr, "Changing train/devel id", trainId, "to", newId
        for element in docById[trainId].getiterator():
            for attrName, attrValue in element.attrib.iteritems():
                if trainId in attrValue:
                    element.set(attrName, attrValue.replace(trainId, newId))
        docById[newId] = docById[trainId]
        del docById[trainId]
        changeIdCount += 1
    # If test set exists, load it, too
    if testUnified != None:
        testDocuments, testDocById, testDocCounts = loadDocs(testUnified)
        for document in testDocuments:
            document.set("set", "test")
        documents = documents + testDocuments
        overlappingIds = []
        for key in docById:
            if key in testDocById:
                overlappingIds.append(key)
        for key in docById:
            assert key not in testDocById, (key, docById[key].get("origId"), testDocById[key].get("origId"), sorted(docById.keys()), sorted(testDocById.keys()), sorted(overlappingIds))
        docById.update(testDocById)
    
    # Add all documents into one XML
    xmlTree = ET.ElementTree(ET.Element("corpus"))
    root = xmlTree.getroot()
    root.set("source", "DDI11")
    for document in documents:
        root.append(document)
    if makeIntermediateFiles:
        ETUtils.write(root, bigfileName + "-documents-notfixed.xml")
    xml = xmlTree
    print >> sys.stderr, "Fixing DDI XML"
    fixEntities(xml)
    convertToInteractions(xml)
    # Add MTMX
    if trainMTMX != None:
        inDir = Utils.Download.getTopDir(tempdir, Utils.Download.downloadAndExtract(trainMTMX, tempdir, outDir + "/DDI11-original"))
        DDITools.addMTMX(xml, inDir)
    if testMTMX != None:
        inDir = Utils.Download.getTopDir(tempdir, Utils.Download.downloadAndExtract(testMTMX, tempdir, outDir + "/DDI11-original"))
        DDITools.addMTMX(xml, inDir)
    if makeIntermediateFiles:
        ETUtils.write(root, bigfileName + "-documents.xml")



    print >> sys.stderr, "---------------", "Inserting TEES-generated analyses", "---------------"
    Utils.Download.downloadAndExtract(Settings.URL["TEES_PARSES"], os.path.join(Settings.DATAPATH, "TEES-parses"), downloadDir, redownload=redownload)
    extractedFilename = os.path.join(Settings.DATAPATH, "TEES-parses") + "/DDI11"
    print >> sys.stderr, "Making sentences"
    Tools.SentenceSplitter.makeSentences(xml, extractedFilename, None)
    print >> sys.stderr, "Inserting McCC parses"
    Tools.BLLIPParser.insertParses(xml, extractedFilename, None, extraAttributes={"source":"TEES-preparsed"})
    print >> sys.stderr, "Inserting Stanford conversions"
    Tools.StanfordParser.insertParses(xml, extractedFilename, None, extraAttributes={"stanfordSource":"TEES-preparsed"})
    print >> sys.stderr, "Protein Name Splitting"
    splitTarget = "McCC"
    #ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
    ProteinNameSplitter.mainFunc(xml, None, splitTarget, removeOld=True)
    print >> sys.stderr, "Head Detection"
    #xml = FindHeads.findHeads(xml, "split-"+splitTarget, tokenization=None, output=None, removeExisting=True)
    xml = FindHeads.findHeads(xml, splitTarget, tokenization=None, output=None, removeExisting=True)    
    
    print >> sys.stderr, "Dividing into sets"
    Utils.InteractionXML.DivideSets.processCorpus(xml, outDir, "DDI11", ".xml")
    
    Stream.closeLog(logFileName)
    if not debug:
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
    optparser = OptionParser(usage="%prog [options]\nDDI'11 Shared Task corpus conversion")
    optparser.add_option("-o", "--outdir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), dest="outdir", help="directory for output files")
    optparser.add_option("-d", "--downloaddir", default=None, dest="downloaddir", help="directory to download corpus files to")
    optparser.add_option("--intermediateFiles", default=False, action="store_true", dest="intermediateFiles", help="save intermediate corpus files")
    optparser.add_option("--redownload", default=False, action="store_true", dest="redownload", help="re-download all source files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Keep temporary files")
    (options, args) = optparser.parse_args()
    
    convertDDI(options.outdir, options.downloaddir, options.redownload, options.intermediateFiles, options.debug)