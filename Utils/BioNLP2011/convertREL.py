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

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def convert(datasets, outdir, corpusName):
    # Depends on CO-conversion
    
    bigfileName = corpusName + "-" + "-and-".join([x[0] for x in datasets])
    documents = []
    for pair in datasets:
        print >> sys.stderr, "Reading", pair[0], "set,",
        docs = ST.loadSet(pair[1], pair[0])
        print >> sys.stderr, len(docs), "documents"
        documents.extend(docs)

    print >> sys.stderr, "Converting to", bigfileName+"-documents.xml"
    xml = STConvert.toInteractionXML(documents, corpusName, bigfileName+"-documents.xml")
    print >> sys.stderr, "Making sentences"
    xml = Tools.GeniaSentenceSplitter.makeSentences(xml, bigfileName+"-sentences.xml")
    #print >> sys.stderr, "Copying parses"
    #parsePath = "/home/jari/biotext/BioNLP2011/data/CO/co-devel-and-train-and-test.xml"
    #InteractionXML.CopyParse.copyParse(bigfileName+"-sentences.xml", parsePath, bigfileName+"-copied-parses.xml", "split-McClosky", "split-McClosky")
    print >> sys.stderr, "Parsing"
    Tools.CharniakJohnsonParser.parse(bigfileName+"-sentences.xml", bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False)
    print >> sys.stderr, "Stanford Conversion"
    Tools.StanfordParser.convertXML("McClosky", bigfileName+"-parsed.xml", bigfileName+"-stanford.xml")
    print >> sys.stderr, "Protein Name Splitting"
    splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + bigfileName+"-stanford.xml" + " -o " + bigfileName+"-split.xml" + " -p " + "McClosky" + " -t " + "McClosky" + " -s split-McClosky" + " -n split-McClosky"
    subprocess.call(splitterCommand, shell=True)
    print >> sys.stderr, "Head Detection"
    xml = FindHeads.findHeads(bigfileName+"-split.xml", "split-McClosky", tokenization=None, output=bigfileName+".xml", removeExisting=True)
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(bigfileName+".xml", outDir, corpusName + "-", ".xml", [("devel", "train")])
    if "devel" in [x[0] for x in datasets]:
        print >> sys.stderr, "Creating empty devel set"
        deletionRules = {"interaction":{},"entity":{"isName":"False"}}
        InteractionXML.DeleteElements.processCorpus(corpusName + "-devel.xml", corpusName + "-devel-empty.xml", deletionRules)
    return xml

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    outDir = "/usr/share/biotext/BioNLP2011/data/REL/"
    #everythingXML = outDir + "rel-everything-with-unconnected.xml"
    #everythingXMLNoUnconnected = outDir + "rel-everything.xml"
    
    trainSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_training_data"
    develSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_development_data"
    testSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_test_data"
    datasets = [("devel", develSet), ("train", trainSet), ("test", testSet)]
    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "rel-conversion-log.txt")
    convert(datasets, outDir, "rel")
    os.chdir(cwd)
    
#    print >> sys.stderr, "Reading Train Set,",
#    trainDoc = ST.loadSet(trainSet, "train")
#    print >> sys.stderr, len(trainDoc), "documents"
#    print >> sys.stderr, "Reading Devel Set,",
#    devDoc = ST.loadSet(develSet, "devel")
#    print >> sys.stderr, len(devDoc), "documents"
#    documents = trainDoc + devDoc
#    
#    print >> sys.stderr, "Converting to", everythingXML
#    xml = STConvert.toInteractionXML(documents, "REL", None)
#    print >> sys.stderr, "Making sentences"
#    xml = Tools.GeniaSentenceSplitter.makeSentences(xml, everythingXML+"-sentences")
#    #print >> sys.stderr, "Tokenizing"
#    #xml = Tools.GeniaTagger.tokenize(xml, everythingXML+"-tokenized.xml", extraFields=[])
#    print >> sys.stderr, "Parsing"
#    skipIds = ["REL.d469.s2"] # skip sentences that crash the parser
#    #Tools.CharniakJohnsonParser.parse(xml, everythingXML+"-parsed.xml", tokenizationName="GeniaTagger-3.0.1", parseName="McClosky", requireEntities=False, skipIds=skipIds)
#    Tools.CharniakJohnsonParser.parse(xml, everythingXML+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False, skipIds=skipIds)
#    print >> sys.stderr, "Stanford Conversion"
#    Tools.StanfordParser.convertXML("McClosky", xml, everythingXML+"-stanford.xml")
#    print >> sys.stderr, "Protein Name Splitting"
#    #splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + everythingXML+"-stanford.xml" + " -o " + everythingXML+"-split.xml" + " -p " + "McClosky" + " -t " + "GeniaTagger-3.0.1" + " -s split-GeniaTagger-3.0.1" + " -n split-McClosky"
#    splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + everythingXML+"-stanford.xml" + " -o " + everythingXML+"-split.xml" + " -p " + "McClosky" + " -t " + "McClosky" + " -s split-McClosky" + " -n split-McClosky"
#    subprocess.call(splitterCommand, shell=True)
#    print >> sys.stderr, "Head Detection"
#    xml = FindHeads.findHeads(everythingXML+"-split.xml", "split-McClosky", tokenization=None, output=everythingXML, removeExisting=True)
#    print >> sys.stderr, "Dividing into sets"
#    InteractionXML.DivideSets.processCorpus(everythingXML, outDir, "rel-", "-with-unconnected.xml")
#    # Make alternative with no unconnected entities
#    print >> sys.stderr, "Removing unconnected entities"
#    xml = InteractionXML.RemoveUnconnectedEntities.removeUnconnectedEntities(everythingXML, everythingXMLNoUnconnected)
#    print >> sys.stderr, "Dividing into sets"
#    InteractionXML.DivideSets.processCorpus(xml, outDir, "rel-", ".xml")
