__version__ = "$Revision: 1.7 $"

import sys,os
import shutil
import subprocess
import tempfile
import codecs
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
import Tool
import Utils.Settings as Settings
from Utils.ProgressCounter import ProgressCounter
import Utils.Download as Download

def install(destDir=None, downloadDir=None, redownload=False, updateLocalSettings=False):
    print >> sys.stderr, "Installing GENIA Sentence Splitter"
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH, "tools/download/")
    if destDir == None:
        destDir = os.path.join(Settings.DATAPATH, "tools/geniass")
    Download.downloadAndExtract(Settings.URL["GENIA_SENTENCE_SPLITTER"], destDir, downloadDir, "geniass")
    print >> sys.stderr, "Compiling GENIA Sentence Splitter"
    Tool.testPrograms("Genia Sentence Splitter", ["make", "ruby"])
    cwd = os.getcwd()
    os.chdir(destDir)
    print >> sys.stderr, "Compiling Genia Sentence Splitter"
    subprocess.call("make", shell=True)
    os.chdir(cwd)
    Tool.finalizeInstall(["./run_geniass.sh"], 
                         {"./run_geniass.sh":"./run_geniass.sh README /dev/null " + Settings.RUBY_PATH},
                         destDir, {"GENIA_SENTENCE_SPLITTER_DIR":destDir}, updateLocalSettings)

def moveElements(document):
    entMap = {}
    entSentence = {}
    entSentenceIndex = {}
    sentences = document.findall("sentence")
    sentenceCount = 0
    for sentence in sentences:
        sentenceOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
        # Move entities
        entCount = 0
        for entity in document.findall("entity"):
            entityOffsets = Range.charOffsetToTuples(entity.get("charOffset"))
            overlaps = False
            for entityOffset in entityOffsets:
                if Range.overlap(sentenceOffset, entityOffset):
                    overlaps = True
                    break
            if overlaps:
                document.remove(entity)
                sentence.append(entity)
                entityId = entity.get("id")
                entityIdLastPart = entityId.rsplit(".", 1)[-1]
                if entityIdLastPart.startswith("e"):
                    entity.set("id", sentence.get("id") + "." + entityIdLastPart)
                    entMap[entityId] = sentence.get("id") + "." + entityIdLastPart
                else:
                    entity.set("docId", entityId)
                    entity.set("id", sentence.get("id") + ".e" + str(entCount))
                    entMap[entityId] = sentence.get("id") + ".e" + str(entCount)
                entSentence[entityId] = sentence
                entSentenceIndex[entityId] = sentenceCount
                #newEntityOffset = (entityOffset[0] - sentenceOffset[0], entityOffset[1] - sentenceOffset[0])
                newEntityOffsets = []
                for entityOffset in entityOffsets:
                    newEntityOffsets.append( (entityOffset[0] - sentenceOffset[0], entityOffset[1] - sentenceOffset[0]) )
                entity.set("origOffset", entity.get("charOffset"))
                #entity.set("charOffset", str(newEntityOffset[0]) + "-" + str(newEntityOffset[1]))
                entity.set("charOffset", Range.tuplesToCharOffset(newEntityOffsets)) 
                entCount += 1
        sentenceCount += 1
    # Move interactions
    intCount = 0
    interactions = []
    interactionOldToNewId = {}
    for interaction in document.findall("interaction"):
        interactions.append(interaction)
        #if entSentenceIndex[interaction.get("e1")] < entSentenceIndex[interaction.get("e2")]:
        #    targetSentence = entSentence[interaction.get("e1")]
        #else:
        #    targetSentence = entSentence[interaction.get("e2")]
        
        # Interactions go to a sentence always by e1, as this is the event they are an argument of.
        # If an intersentence interaction is a relation, this shouldn't matter.
        targetSentence = entSentence[interaction.get("e1")]  
        document.remove(interaction)
        targetSentence.append(interaction)
        newId = targetSentence.get("id") + ".i" + str(intCount)
        interactionOldToNewId[interaction.get("id")] = newId
        interaction.set("id", newId)
        interaction.set("e1", entMap[interaction.get("e1")])
        interaction.set("e2", entMap[interaction.get("e2")])
        intCount += 1
    for interaction in interactions:
        if interaction.get("siteOf") != None:
            interaction.set("siteOf", interactionOldToNewId[interaction.get("siteOf")])
        
def makeSentence(text, begin, end, prevSentence=None, prevEnd=None):
    # Make sentence element
    e = ET.Element("sentence")
    e.set("text", text[begin:end])
    e.set("charOffset", str(begin) + "-" + str(end)) # NOTE: check
    # Set tail string for previous sentence
    if prevSentence != None and begin - prevEnd > 1:
        prevSentence.set("tail", text[prevEnd+1:begin])
    # Set head string for first sentence in document
    if begin > 0 and prevSentence == None:
        e.set("head", text[0:begin])
    assert "\n" not in e.get("text"), e.get("text")
    assert "\r" not in e.get("text"), e.get("text")
    return e
                            
def makeSentences(input, output=None, removeText=False, postProcess=True, debug=False):
    """
    Run GENIA Sentence Splitter
    
    Divide text in the "text" attributes of document and section 
    elements into sentence elements. These sentence elements are
    inserted into their respective parent elements.
    """
    global sentenceSplitterDir
    
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    print >> sys.stderr, "Running GENIA Sentence Splitter", Settings.GENIA_SENTENCE_SPLITTER_DIR,
    if postProcess:
        print >> sys.stderr, "(Using post-processing)"
    else:
        print >> sys.stderr, "(No post-processing)"
    docCount = 0
    sentencesCreated = 0
    redivideCount = 0
    emptySentenceCount = 0
    sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
    counter = ProgressCounter(len(sourceElements), "GeniaSentenceSplitter")
    counter.showMilliseconds = True
    # Create working directory
    workdir = tempfile.mkdtemp()
    for document in sourceElements:
        counter.update(1, "Splitting Documents ("+document.get("id")+"): ")
        docId = document.get("id")
        if docId == None:
            docId = "CORPUS.d" + str(docCount)
        docTag = "-" + str(docCount)
        assert document.find("sentence") == None
        text = document.get("text")
        if text == None or text.strip() == "":
            continue
        #print type(text)
        # Write text to workfile
        #workdir = tempfile.mkdtemp()
        workfile = codecs.open(os.path.join(workdir, "sentence-splitter-input.txt"+docTag), "wt", "utf-8")
        # From http://themoritzfamily.com/python-encodings-and-unicode.html
        # "You have to be careful with the codecs module. Whatever you pass to it must be a Unicode 
        # object otherwise it will try to automatically decode the byte stream as ASCII"
        # However, the unicode errors here were simply due to STTools reading unicode ST-format as ASCII,
        # thus creating an ASCII interaction XML, which then triggered here the unicode error. So, at this
        # point we should be able to safely write(text), as the output file is unicode, and reading with
        # the correct coded is taken care of earlier in the pipeline.
        workfile.write(text) #.encode("utf-8"))
        workfile.close()
        # Run sentence splitter
        assert os.path.exists(Settings.GENIA_SENTENCE_SPLITTER_DIR + "/run_geniass.sh"), Settings.GENIA_SENTENCE_SPLITTER_DIR
        args = [Settings.GENIA_SENTENCE_SPLITTER_DIR + "/run_geniass.sh", os.path.join(workdir, "sentence-splitter-input.txt"+docTag), os.path.join(workdir, "sentence-splitter-output.txt"+docTag), Settings.RUBY_PATH]
        #p = subprocess.call(args)
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if stdout != "":
            print >> sys.stderr, stdout
        if stderr != 'Extracting events.roading model file.\nstart classification.\n':
            print >> sys.stderr, stderr
        #print "stdout<", p.stdout.readlines(), ">"
        #print "stderr<", p.stderr.readlines(), ">"
        if postProcess:
            postProcessorPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geniass-postproc.pl")
            assert os.path.exists(postProcessorPath), postProcessorPath
            ppIn = codecs.open(os.path.join(workdir, "sentence-splitter-output.txt"+docTag), "rt", "utf-8")
            ppOut = codecs.open(os.path.join(workdir, "sentence-splitter-output-postprocessed.txt"+docTag), "wt", "utf-8")
            perlReturnValue = subprocess.call(["perl", postProcessorPath], stdin=ppIn, stdout=ppOut)
            assert perlReturnValue == 0, perlReturnValue
            ppIn.close()
            ppOut.close()
            # Read split sentences
            workfile = codecs.open(os.path.join(workdir, "sentence-splitter-output-postprocessed.txt"+docTag), "rt", "utf-8")
        else:
            workfile = codecs.open(os.path.join(workdir, "sentence-splitter-output.txt"+docTag), "rt", "utf-8")
        start = 0 # sentences are consecutively aligned to the text for charOffsets
        sentenceCount = 0
        #text = text.replace("\n", " ") # should stop sentence splitter from crashing.
        #text = text.replace("  ", " ") # should stop sentence splitter from crashing.
        #alignmentText = text.replace("\n", " ").replace("\r", " ")
        #docTokens = reWhiteSpace.split(text)
        docIndex = 0
        sentenceBeginIndex = -1
        prevSentence = None
        prevEndIndex = None
        #emptySentenceCount = 0
        prevText = None
        for sText in workfile.readlines():
            sText = sText.strip() # The text of the sentence
            if sText == "":
                emptySentenceCount += 1
                continue

            for i in range(len(sText)):
                if sText[i].isspace():
                    assert sText[i] not in ["\n", "\r"]
                    continue
                while text[docIndex].isspace():
                    if text[docIndex] in ["\n", "\r"] and sentenceBeginIndex != -1:
                        redivideCount += 1
                        prevSentence = makeSentence(text, sentenceBeginIndex, docIndex, prevSentence, prevEndIndex)
                        prevSentence.set("id", docId + ".s" + str(sentenceCount))
                        prevSentence.set("redevided", "True")
                        sentencesCreated += 1
                        sentenceCount += 1
                        prevEndIndex = docIndex-1
                        sentenceBeginIndex = -1
                        document.append(prevSentence)
                    docIndex += 1
                assert sText[i] == text[docIndex], (text, sText, prevText, sText[i:i+10], text[docIndex:docIndex+10], (i, docIndex), sentenceBeginIndex) # tokens[i].isspace() == False
                if sentenceBeginIndex == -1:
                    sentenceBeginIndex = docIndex
                docIndex += 1
                prevText = sText
            if sentenceBeginIndex != -1:
                prevSentence = makeSentence(text, sentenceBeginIndex, docIndex, prevSentence, prevEndIndex)
                prevSentence.set("id", docId + ".s" + str(sentenceCount))
                prevEndIndex = docIndex-1
                sentenceBeginIndex = -1
                sentencesCreated += 1
                sentenceCount += 1
                document.append(prevSentence)
        # Add possible tail for last sentence
        if prevEndIndex < len(text) - 1 and prevSentence != None:
            assert prevSentence.get("tail") == None, prevSentence.get("tail")
            prevSentence.set("tail", text[prevEndIndex+1:])
            
        #if emptySentenceCount > 0:
        #    print >> sys.stderr, "Warning,", emptySentenceCount, "empty sentences in", document.get("id") 
        # Remove original text
        if removeText:
            del document["text"]
        # Move elements from document element to sentences
        moveElements(document)
        docCount += 1
    
    print >> sys.stderr, "Sentence splitting created", sentencesCreated, "sentences"
    print >> sys.stderr, "Redivided", redivideCount, "sentences"
    if emptySentenceCount > 0:
        print >> sys.stderr, "Warning,", emptySentenceCount, "empty sentences"
    
    if debug:
        print >> sys.stderr, "Work directory preserved for debugging at", workdir
    else:
        # Remove work directory
        shutil.rmtree(workdir)
        
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

    optparser = OptionParser(description="GENIA Sentence Splitter wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-p", "--postprocess", default=False, action="store_true", dest="postprocess", help="Run postprocessor")
    group = OptionGroup(optparser, "Install Options", "")
    group.add_option("--install", default=None, action="store_true", dest="install", help="Install BANNER")
    group.add_option("--installDir", default=None, dest="installDir", help="Install directory")
    group.add_option("--downloadDir", default=None, dest="downloadDir", help="Install files download directory")
    group.add_option("--redownload", default=False, action="store_true", dest="redownload", help="Redownload install files")
    optparser.add_option_group(group)
    (options, args) = optparser.parse_args()
    
    if not options.install:
        makeSentences(input=options.input, output=options.output, removeText=False, postProcess=options.postprocess)
    else:
        install(options.installDir, options.downloadDir, redownload=options.redownload)
    