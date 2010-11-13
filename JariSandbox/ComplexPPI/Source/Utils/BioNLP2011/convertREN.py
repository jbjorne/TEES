import sys, os, time
import subprocess
import STFormat.STTools as ST
import STFormat.ConvertXML as STConvert
import InteractionXML.RemoveUnconnectedEntities
import InteractionXML.DivideSets
import InteractionXML.DeleteElements
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
    bigfileName = corpusName + "-" + "-and-".join(sorted(datasets.keys()))
#    documents = []
#    for key in sorted(datasets.keys()):
#        print >> sys.stderr, "Reading", key, "set,",
#        docs = ST.loadSet(datasets[key], key)
#        print >> sys.stderr, len(docs), "documents"
#        documents.extend(docs)
#
#    print >> sys.stderr, "Converting to", bigfileName+"-documents.xml"
#    xml = STConvert.toInteractionXML(documents, corpusName, bigfileName+"-documents.xml")
#    print >> sys.stderr, "Making sentences"
#    xml = Tools.GeniaSentenceSplitter.makeSentences(xml, bigfileName+"-sentences.xml")
#    print >> sys.stderr, "Parsing"
#    Tools.CharniakJohnsonParser.parse(xml, bigfileName+"-parsed.xml", tokenizationName=None, parseName="McClosky", requireEntities=False)
#    print >> sys.stderr, "Stanford Conversion"
#    Tools.StanfordParser.convertXML("McClosky", bigfileName+"-parsed.xml", bigfileName+"-stanford.xml")
#    print >> sys.stderr, "Protein Name Splitting"
#    splitterCommand = "python /home/jari/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f " + bigfileName+"-stanford.xml" + " -o " + bigfileName+"-split.xml" + " -p " + "McClosky" + " -t " + "McClosky" + " -s split-McClosky" + " -n split-McClosky"
#    subprocess.call(splitterCommand, shell=True)
#    print >> sys.stderr, "Head Detection"
#    xml = FindHeads.findHeads(bigfileName+"-split.xml", "split-McClosky", tokenization=None, output=bigfileName+".xml", removeExisting=True)
#    print >> sys.stderr, "Dividing into sets"
#    InteractionXML.DivideSets.processCorpus(bigfileName + ".xml", outDir, corpusName + "-", ".xml")
    if "devel" in datasets.keys():
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
    
    outDir = "/usr/share/biotext/BioNLP2011/data/REN/"    
    log(False, False, "ren-conversion-log.txt")
    
    trainSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_bacteria_rename_train_data"
    develSet = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_bacteria_rename_dev_data"
    datasets = {"train":trainSet, "devel":develSet}
    cwd = os.getcwd()
    os.chdir(outDir)
    convert(datasets, outDir, "ren")
    os.chdir(cwd)
    