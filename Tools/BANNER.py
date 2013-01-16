parse__version__ = "$Revision: 1.3 $"

import sys,os
import time, datetime
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils

import shutil
import subprocess
import tempfile
import codecs

import Utils.Settings as Settings
import Utils.Download as Download
import Tool
#bannerDir = Settings.BANNER_DIR

def test(progDir):
    return True

def install(destDir=None, downloadDir=None, redownload=False, compile=False, javaHome=None, updateLocalSettings=False):
    print >> sys.stderr, "Installing BANNER"
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH, "tools/download")
    if destDir == None:
        destDir = Settings.DATAPATH
    if compile:
        Download.downloadAndExtract(Settings.URL["BANNER_SOURCE"], destDir + "/tools/BANNER", downloadDir + "/banner.tar.gz", "trunk", False, redownload=redownload)
        print >> sys.stderr, "Compiling BANNER with ANT"
        Tool.testPrograms("BANNER", ["ant"], {"ant":"ant -version"})
        #/usr/lib/jvm/java-6-openjdk
        if javaHome == None or javaHome.strip() == "":
            subprocess.call("cd " + destDir + "/tools/BANNER; ant -f build_ext.xml", shell=True)
        else:
            subprocess.call("cd " + destDir + "/tools/BANNER; export JAVA_HOME=" + javaHome + "; ant -f build_ext.xml", shell=True)
    else:
        print >> sys.stderr, "Downloading precompiled BANNER"
        Download.downloadAndExtract(Settings.URL["BANNER_COMPILED"], destDir + "/tools", downloadDir, redownload=redownload)
    Tool.finalizeInstall([], None, destDir + "/tools/BANNER", {"BANNER_DIR":destDir + "/tools/BANNER"}, updateLocalSettings)
    
    # Newer versions of BANNER don't need trove
    #print >> sys.stderr, "Downloading Java trove library"
    #url = Settings.URL["BANNER_SOURCE"]
    #Download.downloadAndExtract(url, destDir + "/tools/trove/", downloadDir)

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
            ent.set("charOffset", str(entityBeginOffset) + "-" + str(entityEndOffset))
            if ent.get("charOffset") != bannerOffset:
                ent.set("origBANNEROffset", bannerOffset)
            ent.set("type", "Protein")
            ent.set("given", "True")
            ent.set("source", "BANNER")
            ent.set("text", text[entityBeginOffset:entityEndOffset])
            assert ent.get("text") in text, (ent.get("text"), text)
            elements.append(ent)
        currentBeginOffset += len(entityString) + 1 # +1 for the newline
        currentEndOffset += 1 # +1 for the newline
    return elements

def getWhiteSpaceLessStringMap(string):
    """
    Map the characters in a string from which whitespace has been removed
    to their indices in the original string.
    """
    map = {}
    whiteSpaceLessPos = 0
    for originalPos in range(len(string)):
        if not string[originalPos].isspace():
            map[whiteSpaceLessPos] = originalPos
            whiteSpaceLessPos += 1
    return map

def fixWhiteSpaceLessOffset(entityText, sentenceText, begin, end, map):
    # Here we assume the BANNER offsets refer to text, from which all whitespace has been removed
    assert begin in map, (entityText, sentenceText, begin, end, map)
    # The BANNER offset end character appears to be off by one, e.g. "JAK1" at the beginning of 
    # a sentence would be 0:5, which would be off by one if using the python/java scheme of the
    # end character being the last index plus one. However, since these indices refer to a string
    # from which whitespace has been removed, the remapping could further move the end index. For
    # the remapping, the end index must refer to the actual character, so it is reduced first by one to
    # remove the original extra, then again by one to hit the actual end character's index, then
    # remapped to the actual end character index in the whitespace-including sentence, and then
    # finally, in later code, used with a +1 when getting the entity from the sentence.
    end -= 2 # hope they are consistently off by one
    assert end in map, (entityText, sentenceText, begin, end, map)
    newBegin = map[begin]
    newEnd = map[end]
    #newEnd += 1 # hope they are consistently off by one
    assert entityText == sentenceText[newBegin:newEnd+1], (entityText, sentenceText, (begin, end), (newBegin, newEnd), map)
    return newBegin, newEnd

def fixOffsetOld(origBannerEntity, bannerEntityText, begin, end, sentenceText, verbose=False):
    # The BANNER offsets appear to refer to text, from which all whitespace has been removed.
    # This function could map the offset to an incorrect position when the string of an entity
    # appeared more than once in the same sentence, and has thus been replaced with "fixWhiteSpaceLessOffset"
    origEnd = end
    end = begin + len(bannerEntityText) # the end offset seems random, let's take the length from the begin-one
    assert len(sentenceText[begin:end]) == len(bannerEntityText), (bannerEntity, sentenceText[begin:end], begin, end, sentenceText)
    slippage = 0
    found = True
    while bannerEntityText != sentenceText[begin:end]:
        found = False
        slippage += 1
        if sentenceText[begin+slippage:end+slippage] == bannerEntityText:
            found = True
            break
        if sentenceText[begin-slippage:end-slippage] == bannerEntityText:
            found = True
            slippage = -slippage
            break
    assert found, (origBannerEntity, bannerEntityText, sentenceText[begin:end], begin, end, sentenceText)
    if verbose:
        print >> sys.stderr, "Fixed BANNER entity,", str(origBannerEntity) + ", slippage", slippage, "end diff", origEnd - end
    return begin + slippage, end + slippage - 1

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
    libPath = "/lib/"
#    if not os.path.exists(bannerPath + libPath):
#        libPath = "/libs/"
#        assert os.path.exists(bannerPath + libPath)
    assert os.path.exists(bannerPath + libPath + "banner.jar"), bannerPath
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
        if trovePath == None:
            trovePath = Settings.JAVA_TROVE_PATH
        assert os.path.exists(trovePath), trovePath
        classPath += ":" + trovePath # ":/usr/share/java/trove.jar"
        print >> sys.stderr, "Trove library at", trovePath
    
    config = makeConfigXML(workdir, bannerPath, oldVersion)
    
    # Run parser
    print >> sys.stderr, "Running BANNER", bannerPath
    cwd = os.getcwd()
    os.chdir(bannerPath)
    if oldVersion: # old version
        args = Settings.JAVA.split() + ["-cp", classPath, "banner.eval.TestModel", config]
    else:
        args = Settings.JAVA.split() + ["-cp", classPath, "banner.eval.BANNER", "test", config]
    print >> sys.stderr, "BANNER command:", " ".join(args)
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
    print >> sys.stderr, "Inserting entities"
    if oldVersion:
        outfile = codecs.open(os.path.join(workdir, "output.txt"), "rt", "utf-8")
        idfile = codecs.open(os.path.join(workdir, "ids.txt"), "rt", "utf-8")
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
                        #ent.set("given", "True")
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
        outfile.close()
        idfile.close()
    else:
        sentenceEntityCount = {}
        mentionfile = codecs.open(os.path.join(workdir, "mention.txt"), "rt", "utf-8")
        for line in mentionfile:
            bannerId, offsets, word = line.strip().split("|", 2)
            offsets = offsets.split()
            sentence = sDict[bannerId]
            map = getWhiteSpaceLessStringMap(sentence.get("text"))
            offsets[0], offsets[1] = fixWhiteSpaceLessOffset(word, sentence.get("text"), int(offsets[0]), int(offsets[1]), map)
            #offsets[0], offsets[1] = fixStrangeOffset(line.strip(), word, int(offsets[0]), int(offsets[1]), sentence.get("text"))
            entities = makeEntityElements(int(offsets[0]), int(offsets[1]), sentence.get("text"), splitNewlines, elementName)
            entityText = "\n".join([x.get("text") for x in entities])
            assert entityText == word, (entityText, word, bannerId, offsets, sentence.get("id"), sentence.get("text"))
            assert len(entities) > 0, (line.strip(), sentence.get("text"))
            nonSplitCount += 1
            if len(entities) > 1:
                splitEventCount += 1
            if bannerId not in sentenceEntityCount:
                sentenceEntityCount[bannerId] = 0
            for ent in entities:
                ent.set("id", sentence.get("id") + ".e" + str(sentenceEntityCount[bannerId]))
                sentence.append(ent)
                if not sentenceHasEntities[bannerId]:
                    sentencesWithEntities += 1
                    sentenceHasEntities[bannerId] = True
                totalEntities += 1
                sentenceEntityCount[bannerId] += 1
        mentionfile.close()
    
    print >> sys.stderr, "BANNER found", nonSplitCount, "entities in", sentencesWithEntities, processElement + "-elements",
    print >> sys.stderr, "(" + str(sCount) + " sentences processed)"
    print >> sys.stderr, "New", elementName + "-elements:", totalEntities, "(Split", splitEventCount, "BANNER entities with newlines)"
    
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
    
    from optparse import OptionParser, OptionGroup
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(description="BANNER named entity recognizer wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in Interaction XML format", metavar="FILE")
    optparser.add_option("--inputCorpusName", default="PMC11", dest="inputCorpusName", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in Interaction XML format.")
    optparser.add_option("-e", "--elementName", default="entity", dest="elementName", help="BANNER created element tag in Interaction XML")
    optparser.add_option("-p", "--processElement", default="sentence", dest="processElement", help="input element tag (usually \"sentence\" or \"document\")")
    optparser.add_option("-s", "--split", default=False, action="store_true", dest="splitNewlines", help="Split BANNER entities at newlines")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="Preserve temporary working directory")
    optparser.add_option("--pathBANNER", default=None, dest="pathBANNER", help="")
    optparser.add_option("--pathTrove", default=None, dest="pathTrove", help="")
    group = OptionGroup(optparser, "Install", "")
    group.add_option("--install", default=None, action="store_true", dest="install", help="Install BANNER")
    group.add_option("--installDir", default=None, dest="installDir", help="Install directory")
    group.add_option("--downloadDir", default=None, dest="downloadDir", help="Install files download directory")
    group.add_option("--javaHome", default=None, dest="javaHome", help="JAVA_HOME setting for ANT, used when compiling BANNER")
    group.add_option("--redownload", default=False, action="store_true", dest="redownload", help="Redownload install files")
    optparser.add_option_group(group)
    (options, args) = optparser.parse_args()
    
    if not options.install:
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
        install(options.installDir, options.downloadDir, javaHome=options.javaHome, redownload=options.redownload)
    