import sys, os, time
import subprocess
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.Stream as Stream
import Utils.FindHeads as FindHeads
import Tools.GeniaSentenceSplitter
import Tools.GeniaTagger
import Tools.CharniakJohnsonParser
import Tools.StanfordParser
import InteractionXML.CopyParse
import InteractionXML.DeleteElements
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
import cElementTreeUtils as ETUtils
from collections import defaultdict
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../../../../GeniaChallenge/formatConversion")))
import ProteinNameSplitter
import Range

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

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
        for entity in sentence.findall("entity"):
            charOffset = entity.get("charOffset")
            if charOffset == "-":
                sentence.remove(entity)
                counts["removed-invalid"] += 1
            else:
                charOffset = Range.charOffsetToSingleTuple(charOffset)
                entity.set("charOffset", Range.tuplesToCharOffset( (charOffset[0], charOffset[1]+1)))
                entity.set("isName", "True")
        for interaction in sentence.findall("interaction"):
            interaction.set("type", "DDI")
    print "Fix counts:", counts
    
def convertToInteractions(xml):
    print "Renaming pair-elements"
    counts = defaultdict(int)
    for sentence in xml.getiterator("sentence"):
        sentence.set("charOffset", "0-" + str(len(sentence.get("text"))-1) )
        for pair in sentence.findall("pair"):
            if pair.get("interaction") == "true":
                pair.tag = "interaction"
                pair.set("type", "DDI")
                counts["pos"] += 1
            else:
                sentence.remove(pair)
                counts["neg"] += 1
    print "Pair counts:", counts

def convertDDI(inDir, outDir):
    bigfileName = os.path.join(outDir, "DrugDDI")
    #oldXML = ETUtils.ETFromObj(bigfileName+".xml")
    if False:
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
        
        #for doc in oldXML.getiterator("document"):
        #    docById[doc.get("id")] = doc
        
        sortedDocCounts = sorted(docCounts.iteritems(), key=lambda (k,v): (v,k), reverse=True)
        datasetCounts = {"train":[0,0], "devel":[0,0], "test":[0,0]}
        for i in range(0, len(sortedDocCounts)-3, 4):
            for j in [0,1]:
                docById[sortedDocCounts[i+j][0]].set("set", "train")
                datasetCounts["train"][0] += sortedDocCounts[i+j][1][0]
                datasetCounts["train"][1] += sortedDocCounts[i+j][1][1]
            docById[sortedDocCounts[i+2][0]].set("set", "devel")
            docById[sortedDocCounts[i+3][0]].set("set", "test")
            datasetCounts["devel"][0] += sortedDocCounts[i+2][1][0]
            datasetCounts["devel"][1] += sortedDocCounts[i+2][1][1]
            datasetCounts["test"][0] += sortedDocCounts[i+3][1][0]
            datasetCounts["test"][1] += sortedDocCounts[i+3][1][1]
        
        print datasetCounts
        for key in datasetCounts.keys():
            print key, datasetCounts[key][0] / float(datasetCounts[key][1]) 
        
    if False:
        xmlTree = ET.ElementTree(ET.Element("corpus"))
        root = xmlTree.getroot()
        root.set("source", "DrugDDI")
        for document in documents:
            root.append(document)
        #root.append(ET.Element("dummy"))
        #print type(documents[-1]), documents[-1].get("id"), documents[-1].get("origId") 
        #print type(documents[-2])
        #print ETUtils.toStr(documents[-2])
        #print ETUtils.toStr(documents[-1])
        #sys.exit()
        ETUtils.write(root, bigfileName + "-documents.xml")
        xml = xmlTree
        
        print >> sys.stderr, "Parsing"
        Tools.CharniakJohnsonParser.parse(xml, bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=True, timeout=10)
        print >> sys.stderr, "Stanford Conversion"
        Tools.StanfordParser.convertXML("McClosky", xml, bigfileName+"-stanford.xml")
    
        print >> sys.stderr, "Fixing DDI XML"
        fixEntities(xml)
    if True:
        xml = bigfileName + "-stanford.xml"        
        print >> sys.stderr, "Protein Name Splitting"
        splitTarget = "McClosky"
        xml = ProteinNameSplitter.mainFunc(xml, None, splitTarget, splitTarget, "split-"+splitTarget, "split-"+splitTarget)
        print >> sys.stderr, "Head Detection"
        xml = FindHeads.findHeads(xml, "split-McClosky", tokenization=None, output=bigfileName+".xml", removeExisting=True)
        convertToInteractions(xml)
        print >> sys.stderr, "Dividing into sets"
        InteractionXML.DivideSets.processCorpus(xml, outDir, "DrugDDI-", ".xml", [("devel", "train", "test"), ("devel", "train")])
        #InteractionXML.DivideSets.processCorpus(oldXML, outDir, "DrugDDI-", ".xml", [("devel", "train", "test"), ("devel", "train")])
    #InteractionXML.DivideSets.processCorpus(bigfileName+".xml", outDir, "DrugDDI-", ".xml", [("devel", "train", "test"), ("devel", "train")])
    #if "devel" in [x[0] for x in datasets]:
    #    print >> sys.stderr, "Creating empty devel set"
    #    deletionRules = {"interaction":{},"entity":{"isName":"False"}}
    #    InteractionXML.DeleteElements.processCorpus(corpusName + "-devel.xml", corpusName + "-devel-empty.xml", deletionRules)
    #return xml

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    inDir = "/home/jari/data/DDIExtraction2011/DrugDDI_Unified"
    outDir = "/usr/share/biotext/DDIExtraction2011/data/"
    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "DDI-conversion-log.txt")
    print >> sys.stderr, "Converting DDI"
    convertDDI(inDir, outDir)
    os.chdir(cwd)