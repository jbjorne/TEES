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

def log(clear=False, logCmd=True, logFile="log.txt"):
    Stream.setLog(logFile, clear)
    Stream.setTimeStamp("[%H:%M:%S]", True)
    print >> sys.stderr, "####### Log opened at ", time.ctime(time.time()), "#######"
    if logCmd:
        sys.stdout.writeToLog("Command line: " + " ".join(sys.argv) + "\n")

def convert(datasets, outdir, corpusName):
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
    print >> sys.stderr, "Parsing"
    Tools.CharniakJohnsonParser.parse(xml, bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False)
    print >> sys.stderr, "Stanford Conversion"
    Tools.StanfordParser.convertXML("McClosky", bigfileName+"-parsed.xml", bigfileName+"-stanford.xml")
    print >> sys.stderr, "Protein Name Splitting"
    splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + bigfileName+"-stanford.xml" + " -o " + bigfileName+"-split.xml" + " -p " + "McClosky" + " -t " + "McClosky" + " -s split-McClosky" + " -n split-McClosky"
    subprocess.call(splitterCommand, shell=True)
    print >> sys.stderr, "Fix AltOffsets"
    import InteractionXML.FixAltOffsets
    xml = InteractionXML.FixAltOffsets.fixAltOffsets(bigfileName+"-split.xml")
    print >> sys.stderr, "Head Detection"
    xml = FindHeads.findHeads(xml, "split-McClosky", tokenization=None, output=bigfileName+".xml", removeExisting=True)
    print >> sys.stderr, "Dividing into sets"
    InteractionXML.DivideSets.processCorpus(xml, outDir, corpusName + "-", ".xml")
    return xml

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    outDir = "/usr/share/biotext/BioNLP2011/data/CO/"    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "co-conversion-log.txt")
    
    trainSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_coreference_training_data"
    develSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_coreference_development_data"
    testSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_coreference_test_data"
    datasets = [("devel", develSet), ("train", trainSet), ("test", testSet)]
    convert(datasets, outDir, "co")
    os.chdir(cwd)
    