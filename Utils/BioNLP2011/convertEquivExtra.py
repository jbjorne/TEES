import sys, os, time
import subprocess
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import STFormat.Equiv
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../../../../GeniaChallenge/formatConversion")))
import ProteinNameSplitter
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

    print >> sys.stderr, "Resolving equivalences"
    STFormat.Equiv.process(documents)

    print >> sys.stderr, "Converting to", bigfileName+"-documents.xml"
    xml = STConvert.toInteractionXML(documents, corpusName, bigfileName+"-documents.xml")
    print >> sys.stderr, "Making sentences"
    #xml = Tools.GeniaSentenceSplitter.makeSentences(xml, bigfileName+"-sentences.xml")
    xml = Tools.GeniaSentenceSplitter.makeSentences(xml, bigfileName+".xml")
    
    #print >> sys.stderr, "Copying parses"
    #parsePath = "/home/jari/biotext/BioNLP2011/data/CO/co-devel-and-train-and-test.xml"
    #InteractionXML.CopyParse.copyParse(bigfileName+"-sentences.xml", parsePath, bigfileName+"-copied-parses.xml", "split-McClosky", "split-McClosky")
    if False:
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

    # REL    
    outDir = "/usr/share/biotext/BioNLP2011/data/equiv-recalc/REL/"
    trainSet = "/home/jari/data/BioNLP11SharedTask/supporting-tasks/BioNLP-ST_2011_Entity_Relations_training_data"
    develSet = "/home/jari/data/BioNLP11SharedTask/supporting-tasks/BioNLP-ST_2011_Entity_Relations_development_data"
    #testSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_test_data"
    datasets = [("devel", develSet), ("train", trainSet)] #, ("test", testSet)]
    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "REL-conversion-log.txt")
    convert(datasets, outDir, "REL")
    os.chdir(cwd)
    
    # OLD
    outDir = "/usr/share/biotext/BioNLP2011/data/equiv-recalc/OLD/"
    trainSet = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_training_data_rev2"
    develSet = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
    #testSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_test_data"
    datasets = [("devel", develSet), ("train", trainSet)] #, ("test", testSet)]
    
    cwd = os.getcwd()
    os.chdir(outDir)
    log(False, False, "OLD-conversion-log.txt")
    convert(datasets, outDir, "OLD")
    os.chdir(cwd)
