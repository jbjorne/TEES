parse__version__ = "$Revision: 1.2 $"

import sys,os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import StanfordParser

import shutil
import subprocess
import tempfile
import codecs

bannerDir = "/home/jari/biotext/tools/BANNER-trunk-SMP-300910"

def makeConfigXML(workdir, bannerDir):
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
    ETUtils.writeUTF8(conf, workdir + "/banner_config.xml")
    return workdir + "/banner_config.xml"
    
def run(input, output=None):
    global bannerDir
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    # Write text to input file
    workdir = tempfile.mkdtemp()
    infile = codecs.open(os.path.join(workdir, "input.txt"), "wt", "utf-8")
    idCount = 0
    for sentence in corpusRoot.getiterator("sentence"):
        infile.write("U" + str(idCount) + " " + sentence.get("text") + "\n")
        idCount += 1
    infile.close()
    
    # Define classpath for java
    classPath = bannerDir + "/bin"
    classPath += ":" + bannerDir + "/lib/banner.jar"
    classPath += ":" + bannerDir + "/lib/dragontool.jar"
    classPath += ":" + bannerDir + "/lib/heptag.jar"
    classPath += ":" + bannerDir + "/lib/commons-collections-3.2.1.jar"
    classPath += ":" + bannerDir + "/lib/commons-configuration-1.6.jar"
    classPath += ":" + bannerDir + "/lib/commons-lang-2.4.jar"
    classPath += ":" + bannerDir + "/lib/mallet.jar"
    classPath += ":" + bannerDir + "/lib/commons-logging-1.1.1.jar"
    classPath += ":/usr/share/java/trove.jar"
    
    config = makeConfigXML(workdir, bannerDir)
    
    # Run parser
    print >> sys.stderr, "Running BANNER", bannerDir
    cwd = os.getcwd()
    os.chdir(bannerDir)
    args = ["java", "-cp", classPath, "banner.eval.TestModel", config]
    #print args
    subprocess.call(args)
    os.chdir(cwd)
    
    # Put sentences in dictionary
    sDict = {}
    sentenceHasEntities = {}
    sCount = 0
    for sentence in corpusRoot.getiterator("sentence"):
        sDict["U" + str(sCount)] = sentence
        sentenceHasEntities["U" + str(sCount)] = False
        sCount += 1
    
    sentencesWithEntities = 0
    totalEntities = 0
    
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
            # Determine offsets
            cStart = sText.find(tokenText, start)
            assert cStart != -1, (tokenText, tag, sText, line)
            cEnd = cStart + len(tokenText) - 1
            start = cStart + len(tokenText)
            
            if tag == "O":
                if beginOffset != None:
                    # Make element
                    ent = ET.Element("entity")
                    ent.set("id", sentenceId + ".e" + str(entityCount))
                    ent.set("charOffset", str(beginOffset) + "-" + str(prevEnd))
                    ent.set("type", "Protein")
                    ent.set("isName", "True")
                    ent.set("text", sText[beginOffset:prevEnd+1])
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
    
    print >> sys.stderr, "Found", totalEntities, "entities in", sentencesWithEntities, "sentences"
    
    outfile.close()
    idfile.close()
    # Remove work directory
    shutil.rmtree(workdir)
        
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
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    run(input=options.input, output=options.output)
    