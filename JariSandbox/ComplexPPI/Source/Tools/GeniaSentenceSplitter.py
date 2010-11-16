__version__ = "$Revision: 1.5 $"

import sys,os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import Range

import shutil
import subprocess
import tempfile
import codecs

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter
"""
A wrapper for the Joachims SVM Multiclass classifier.
"""

sentenceSplitterDir = "/home/jari/biotext/tools/geniass"

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
            entityOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
            if Range.overlap(sentenceOffset, entityOffset):
                document.remove(entity)
                sentence.append(entity)
                prevId = entity.get("id")
                entity.set("id", sentence.get("id") + ".e" + str(entCount))
                entMap[prevId] = sentence.get("id") + ".e" + str(entCount)
                entSentence[prevId] = sentence
                entSentenceIndex[prevId] = sentenceCount
                newEntityOffset = (entityOffset[0] - sentenceOffset[0], entityOffset[1] - sentenceOffset[0])
                entity.set("origOffset", entity.get("charOffset"))
                entity.set("charOffset", str(newEntityOffset[0]) + "-" + str(newEntityOffset[1])) 
                entCount += 1
        sentenceCount += 1
    # Move interactions
    intCount = 0
    for interaction in document.findall("interaction"):
        if entSentenceIndex[interaction.get("e1")] < entSentenceIndex[interaction.get("e1")]:
            targetSentence = entSentence[interaction.get("e1")]
        else:
            targetSentence = entSentence[interaction.get("e2")]
        document.remove(interaction)
        targetSentence.append(interaction)
        interaction.set("id", targetSentence.get("id") + ".i" + str(intCount))
        interaction.set("e1", entMap[interaction.get("e1")])
        interaction.set("e2", entMap[interaction.get("e2")])
        intCount += 1
                
def makeSentences(input, output=None, removeText=False, postProcess=True):
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
    
    docCount = 0
    sentencesCreated = 0
    sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
    counter = ProgressCounter(len(sourceElements), "GeniaSentenceSplitter")
    for document in sourceElements:
        counter.update(1, "Splitting Documents ("+document.get("id")+"): ")
        docId = document.get("id")
        if docId == None:
            docId = "CORPUS.d" + str(docCount)
        assert document.find("sentence") == None
        text = document.get("text")
        if text == None or text.strip() == "":
            continue
        # Write text to workfile
        workdir = tempfile.mkdtemp()
        workfile = codecs.open(os.path.join(workdir, "sentence-splitter-input.txt"), "wt", "utf-8")
        workfile.write(text)
        workfile.close()
        # Run sentence splitter
        args = [sentenceSplitterDir + "/run_geniass.sh", os.path.join(workdir, "sentence-splitter-input.txt"), os.path.join(workdir, "sentence-splitter-output.txt")]
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
            ppIn = codecs.open(os.path.join(workdir, "sentence-splitter-output.txt"), "rt", "utf-8")
            ppOut = codecs.open(os.path.join(workdir, "sentence-splitter-output-postprocessed.txt"), "wt", "utf-8")
            subprocess.call(os.path.join(sentenceSplitterDir, "geniass-postproc.pl"), stdin=ppIn, stdout=ppOut)
            ppIn.close()
            ppOut.close()
            # Read split sentences
            workfile = codecs.open(os.path.join(workdir, "sentence-splitter-output-postprocessed.txt"), "rt", "utf-8")
        else:
            workfile = codecs.open(os.path.join(workdir, "sentence-splitter-output.txt"), "rt", "utf-8")
        start = 0 # sentences are consecutively aligned to the text for charOffsets
        sentenceCount = 0
        for sText in workfile.readlines():
            sText = sText.strip() # The text of the sentence
            # Find the starting point of the sentence in the text. This
            # point must be after previous sentences
            cStart = text.find(sText, start) # find start position
            tail = None
            if cStart - start != 0:
                prevSentence.set("tail", text[start:cStart])
            cEnd = cStart + len(sText) # end position is determined by length
            start = cStart + len(sText) # for next sentence, start search from end of this one
            # make sentence element
            e = ET.Element("sentence")
            e.set("text", sText)
            e.set("charOffset", str(cStart) + "-" + str(cEnd - 1)) # NOTE: check
            e.set("id", docId + ".s" + str(sentenceCount))
            document.append(e) # add sentence to parent element
            prevSentence = e
            sentencesCreated += 1
            sentenceCount += 1
        # Remove original text
        if removeText:
            del document["text"]
        # Remove work directory
        shutil.rmtree(workdir)
        # Move elements from document element to sentences
        moveElements(document)
        docCount += 1
    
    print >> sys.stderr, "Sentence splitting created", sentencesCreated, "sentences"
        
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
    optparser.add_option("-p", "--postprocess", default=False, action="store_true", dest="postprocess", help="Run postprocessor")
    (options, args) = optparser.parse_args()
    
    makeSentences(input=options.input, output=options.output, removeText=False, postProcess=options.postprocess)
    