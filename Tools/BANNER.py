parse__version__ = "$Revision: 1.3 $"

import sys,os
import time, datetime
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils")
import cElementTreeUtils as ETUtils
import StanfordParser

import shutil
import subprocess
import tempfile
import codecs

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Settings as Settings
import Utils.Download as Download
#bannerDir = Settings.BANNER_DIR

def install(destDir=None, downloadDir=None, redownload=False):
    url = "http://banner.svn.sourceforge.net/viewvc/banner/trunk/?view=tar"
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH, "tools/download/")
    if destDir == None:
        destDir = Settings.DATAPATH
    Download.downloadAndExtract(url, destDir + "/tools/BANNER", downloadDir + "banner.tar.gz", "trunk", False)
    
    # Compile BANNER
    subprocess.call("cd " + destDir + "/tools/BANNER; export JAVA_HOME=/usr/lib/jvm/java-6-openjdk; ant -f build_ext.xml", shell=True)
    
    #url ="http://downloads.sourceforge.net/project/biocreative/biocreative2entitytagging/1.1/bc2geneMention.tar.gz?use_mirror=auto"
    #Download.downloadAndExtract(url, destDir + "/data", downloadDir)
    
    url = "http://www.java2s.com/Code/JarDownload/trove/trove-2.1.0.jar.zip"
    Download.downloadAndExtract(url, destDir + "/tools/trove/", downloadDir)

def makeConfigXML(workdir, bannerDir, oldVersion=True):
    conf = ET.Element("banner-configuration")
    banner = ET.SubElement(conf, "banner")
    eval = ET.SubElement(banner, "eval")
    datasetName = ET.SubElement(eval, "datasetName").text = "banner.eval.dataset.BC2GMDataset"
    # Dataset
    dataset = ET.SubElement(eval, "dataset")
    ET.SubElement(dataset, "sentenceFilename").text = workdir + "/input.txt"
    ET.SubElement(dataset, "mentionTestFilename").text = workdir + "/empty.eval"
    ET.SubElement(dataset, "mentionAlternateFilename").text = workdir + "/empty.eval"
    codecs.open(os.path.join(workdir, "empty.eval"), "wt", "utf-8").close()
    # More eval level stuff
    ET.SubElement(eval, "idInputFilename").text = workdir + "/ids.txt"
    ET.SubElement(eval, "rawInputFilename").text = workdir + "/raw.txt"
    ET.SubElement(eval, "trainingInputFilename").text = workdir + "/training.txt"
    ET.SubElement(eval, "outputFilename").text = workdir + "/output.txt"
    codecs.open(os.path.join(workdir, "output.txt"), "wt", "utf-8").close()
    ET.SubElement(eval, "inContextAnalysisFilename").text = workdir + "/contextAnalysis.html"
    ET.SubElement(eval, "mentionFilename").text = workdir + "/mention.txt"
    ET.SubElement(eval, "modelFilename").text = bannerDir + "/output/model_BC2GM.bin"
    ET.SubElement(eval, "lemmatiserDataDirectory").text = bannerDir + "/nlpdata/lemmatiser"
    ET.SubElement(eval, "posTaggerDataDirectory").text = bannerDir + "/nlpdata/tagger"
    ET.SubElement(eval, "posTagger").text = "dragon.nlp.tool.HeppleTagger"
    ET.SubElement(eval, "tokenizer").text = "banner.tokenization.SimpleTokenizer"
    ET.SubElement(eval, "useParenthesisPostProcessing").text = "true"
    ET.SubElement(eval, "useLocalAbbreviationPostProcessing").text = "true"
    ET.SubElement(eval, "useNumericNormalization").text = "true"
    ET.SubElement(eval, "tagFormat").text = "IOB"
    ET.SubElement(eval, "crfOrder").text = "2"
    if not oldVersion:
        ET.SubElement(eval, "mentionTypes").text = "Required"
        ET.SubElement(eval, "sameTypeOverlapOption").text = "Exception"
        ET.SubElement(eval, "differentTypeOverlapOption").text = "Exception"
    ET.SubElement(eval, "dictionaryTagger").text = "banner.tagging.dictionary.DictionaryTagger"
    # End eval element
    tagging = ET.SubElement(banner, "tagging") 
    dictionary = ET.SubElement(tagging, "dictionary")
    dictionaryTagger = ET.SubElement(dictionary, "DictionaryTagger")
    ET.SubElement(dictionaryTagger, "filterContainedMentions").text = "true"
    ET.SubElement(dictionaryTagger, "normalizeMixedCase").text = "false"
    ET.SubElement(dictionaryTagger, "normalizeDigits").text = "false"
    ET.SubElement(dictionaryTagger, "canonize").text = "false"
    ET.SubElement(dictionaryTagger, "generate2PartVariations").text = "true"
    ET.SubElement(dictionaryTagger, "dropEndParentheticals").text = "false"
    ET.SubElement(dictionaryTagger, "dictionaryFile").text = bannerDir + "/dict/single.txt"
    ET.SubElement(dictionaryTagger, "dictionaryType").text = "GENE"
    # Write to file
    filename = workdir + "/banner_config.xml"
    ETUtils.write(conf, workdir + "/banner_config.xml")
    return workdir + "/banner_config.xml"

def makeEntityElements(beginOffset, endOffset, text, splitNewlines=False, elementName="entity"):
    # NOTE! Entity ids are not set by this function
    # beginOffset and endOffset in interaction XML format
    bannerOffset = str(beginOffset) + "-" + str(endOffset)
    currentEndOffset = beginOffset
    elements = []
    if splitNewlines:
        entityStrings = text[beginOffset:endOffset+1].split("\n") # TODO should support also other newlines
    else:
        entityStrings = [text[beginOffset:endOffset+1]]
    # Make elements
    currentBeginOffset = beginOffset
    for entityString in entityStrings:
        currentEndOffset += len(entityString)
        if entityString.strip() != "":
            ent = ET.Element(elementName)
            ent.set("id", None) # this should crash the XML writing, if id isn't later redefined
            # Modify offsets to remove leading/trailing whitespace
            entityBeginOffset = currentBeginOffset
            entityEndOffset = currentEndOffset
            if len(entityString.rstrip()) < len(entityString):
                entityEndOffset -= len(entityString) - len(entityString.rstrip())
            if len(entityString.lstrip()) < len(entityString):
                entityBeginOffset += len(entityString) - len(entityString.lstrip())
            # Make the element
            ent.set("charOffset", str(entityBeginOffset) + "-" + str(entityEndOffset-1))
            if ent.get("charOffset") != bannerOffset:
                ent.set("origBANNEROffset", bannerOffset)
            ent.set("type", "Protein")
            ent.set("isName", "True")
            ent.set("source", "BANNER")
            ent.set("text", text[entityBeginOffset:entityEndOffset])
            assert ent.get("text") in text, (ent.get("text"), text)
            elements.append(ent)
        currentBeginOffset += len(entityString) + 1 # +1 for the newline
        currentEndOffset += 1 # +1 for the newline
    return elements
    
def run(input, output=None, elementName="entity", processElement="document", splitNewlines=False, debug=False, bannerPath=None, trovePath=None):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    if debug:
        print >> sys.stderr, "BANNER work directory at", workdir
    infile = codecs.open(os.path.join(workdir, "input.txt"), "wt", "utf-8")
    idCount = 0
    for sentence in corpusRoot.getiterator(processElement):
        infile.write("U" + str(idCount) + " " + sentence.get("text").replace("\n", " ").replace("\n", " ") + "\n")
        idCount += 1
    infile.close()
    
    # Define classpath for java
    if bannerPath == None:
        bannerPath = Settings.BANNER_DIR
    if trovePath == None:
        trovePath = Settings.JAVA_TROVE_PATH
    libPath = "/lib/"
#    if not os.path.exists(bannerPath + libPath):
#        libPath = "/libs/"
#        assert os.path.exists(bannerPath + libPath)
    assert os.path.exists(bannerPath + libPath + "banner.jar"), bannerPath
    assert os.path.exists(trovePath), trovePath
    oldVersion = True
    classPath = bannerPath + "/bin"
    for filename in os.listdir(bannerPath + libPath):
        #if filename.endswith(".jar"):
        #    classPath += ":" + bannerPath + libPath + filename
        if filename == "uima":
            oldVersion = False
    classPath += ":" + bannerPath + libPath + "*"
#    classPath += ":" + bannerPath + libPath + "banner.jar"
#    classPath += ":" + bannerPath + libPath + "dragontool.jar"
#    classPath += ":" + bannerPath + libPath + "heptag.jar"
#    classPath += ":" + bannerPath + libPath + "commons-collections-3.2.1.jar"
#    classPath += ":" + bannerPath + libPath + "commons-configuration-1.6.jar"
#    classPath += ":" + bannerPath + libPath + "commons-lang-2.4.jar"
#    classPath += ":" + bannerPath + libPath + "mallet.jar"
#    classPath += ":" + bannerPath + libPath + "commons-logging-1.1.1.jar"
    if oldVersion:
        classPath += ":" + trovePath # ":/usr/share/java/trove.jar"
    
    config = makeConfigXML(workdir, bannerPath)
    
    # Run parser
    print >> sys.stderr, "Running BANNER", bannerPath
    print >> sys.stderr, "Trove library at", trovePath
    cwd = os.getcwd()
    os.chdir(bannerPath)
    if oldVersion: # old version
        args = ["java", "-cp", classPath, "banner.eval.TestModel", config]
    else:
        args = ["java", "-cp", classPath, "banner.eval.BANNER", "test", config]
    print args
    startTime = time.time()
    exitCode = subprocess.call(args)
    assert exitCode == 0, exitCode
    print >> sys.stderr, "BANNER time:", str(datetime.timedelta(seconds=time.time()-startTime))
    os.chdir(cwd)
    
    # Put sentences in dictionary
    sDict = {}
    sentenceHasEntities = {}
    sCount = 0
    for sentence in corpusRoot.getiterator(processElement):
        sDict["U" + str(sCount)] = sentence
        sentenceHasEntities["U" + str(sCount)] = False
        sCount += 1
    
    sentencesWithEntities = 0
    totalEntities = 0
    nonSplitCount = 0
    splitEventCount = 0
    
    # TODO: mention.txt appears to contain predicted entities directly
    # To be able to feed BANNER documents (or poorly chopped sentences)
    # one should probably remove newlines, as BANNER separates its input
    # on newlines. Replacing all \r and \n characters should preserve the
    # character offsets.
    
    # Read BANNER results
    outfile = codecs.open(os.path.join(workdir, "output.txt"), "rt", "utf-8")
    idfile = codecs.open(os.path.join(workdir, "ids.txt"), "rt", "utf-8")
    print >> sys.stderr, "Inserting entities"
    # Add output to sentences
    for line in outfile:
        bannerId = idfile.readline().strip()
        sentence = sDict[bannerId]
        
        # Find or create container elements
        sentenceId = sentence.get("id")
        
        sText = sentence.get("text")
        start = 0
        entityCount = 0
        beginOffset = None
        # Add tokens
        splits = line.strip().split()
        for split in splits:
            tokenText, tag = split.rsplit("|", 1)
            # Determine offsets by aligning BANNER-generated tokens to original text
            cStart = sText.find(tokenText, start)
            assert cStart != -1, (tokenText, tag, sText, line)
            cEnd = cStart + len(tokenText) - 1
            start = cStart + len(tokenText)
            
            if tag == "O":
                if beginOffset != None:
                    ## Make element
                    #ent = ET.Element(elementName)
                    #ent.set("id", sentenceId + ".e" + str(entityCount))
                    #ent.set("charOffset", str(beginOffset) + "-" + str(prevEnd))
                    #ent.set("type", "Protein")
                    #ent.set("isName", "True")
                    #ent.set("source", "BANNER")
                    #ent.set("text", sText[beginOffset:prevEnd+1])
                    entities = makeEntityElements(beginOffset, prevEnd, sText, splitNewlines, elementName)
                    assert len(entities) > 0
                    nonSplitCount += 1
                    if len(entities) > 1:
                        splitEventCount += 1
                    for ent in entities:
                        ent.set("id", sentenceId + ".e" + str(entityCount))
                        sentence.append(ent)
                        if not sentenceHasEntities[bannerId]:
                            sentencesWithEntities += 1
                            sentenceHasEntities[bannerId] = True
                        totalEntities += 1
                        entityCount += 1
                    beginOffset = None
            else:
                if beginOffset == None:
                    beginOffset = cStart
            prevEnd = cEnd
    
    print >> sys.stderr, "BANNER found", nonSplitCount, "entities in", sentencesWithEntities, processElement + "-elements"
    print >> sys.stderr, "New", elementName + "-elements:", totalEntities, "(Split", splitEventCount, "BANNER entities with newlines)"
    
    outfile.close()
    idfile.close()
    # Remove work directory
    if not debug:
        shutil.rmtree(workdir)
    else:
        print >> sys.stderr, "BANNER working directory for debugging at", workdir
        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree
    
if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in Interaction XML format", metavar="FILE")
    optparser.add_option("--inputCorpusName", default="PMC11", dest="inputCorpusName", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in Interaction XML format.")
    optparser.add_option("-e", "--elementName", default="entity", dest="elementName", help="BANNER created element tag in Interaction XML")
    optparser.add_option("-p", "--processElement", default="sentence", dest="processElement", help="input element tag (usually \"sentence\" or \"document\")")
    optparser.add_option("-s", "--split", default=False, action="store_true", dest="splitNewlines", help="Split BANNER entities at newlines")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Preserve temporary working directory")
    optparser.add_option("--pathBANNER", default=None, dest="pathBANNER", help="")
    optparser.add_option("--pathTrove", default=None, dest="pathTrove", help="")
    optparser.add_option("--install", default=None, dest="install", help="Install directory (or DEFAULT)")
    (options, args) = optparser.parse_args()
    
    if options.install == None:
        if os.path.isdir(options.input) or options.input.endswith(".tar.gz"):
            print >> sys.stderr, "Converting ST-format"
            import STFormat.ConvertXML
            import STFormat.STTools
            options.input = STFormat.ConvertXML.toInteractionXML(STFormat.STTools.loadSet(options.input), options.inputCorpusName)
        print >> sys.stderr, "Running BANNER"
        run(input=options.input, output=options.output, elementName=options.elementName, 
            processElement=options.processElement, splitNewlines=options.splitNewlines, debug=options.debug,
            bannerPath=options.pathBANNER, trovePath=options.pathTrove)
    else:
        downloadDir = None
        destDir = None
        if options.install != "DEFAULT":
            if "," in options.install:
                destDir, downloadDir = options.install.split(",")
            else:
                destDir = options.install
        install(destDir, downloadDir)
    