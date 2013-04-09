__version__ = "$Revision: 1.1 $"

import sys,os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

import shutil
import subprocess
import tempfile
import codecs
import tarfile

from GeniaSentenceSplitter import moveElements

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from Utils.ProgressCounter import ProgressCounter

def openFile(path, tarFile=None):
    if tarFile != None:
        try:
            return tarFile.extractfile(tarFile.getmember(path))
        except KeyError:
            pass
    else:
        if os.path.exists(path):
            return codecs.open(path, "rt", "utf-8") #open(path, "rt")
    return None
                
def makeSentences(input, tokenizationPath, output=None, removeText=False, escDict={}, ignoreErrors=False):
    """
    Divide text in the "text" attributes of document and section 
    elements into sentence elements. These sentence elements are
    inserted into their respective parent elements.
    """
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    print >> sys.stderr, "Inserting tokenizations from", tokenizationPath
    assert os.path.exists(tokenizationPath)
    if tokenizationPath.find(".tar.gz") != -1:
        tarFilePath, tokenizationPath = tokenizationPath.split(".tar.gz")
        tarFilePath += ".tar.gz"
        tarFile = tarfile.open(tarFilePath)
        if tokenizationPath[0] == "/":
            tokenizationPath = tokenizationPath[1:]
    else:
        tarFile = None
    
    docCount = 0
    docsWithSentences = 0
    sentencesCreated = 0
    sourceElements = [x for x in corpusRoot.getiterator("document")] + [x for x in corpusRoot.getiterator("section")]
    counter = ProgressCounter(len(sourceElements), "Sentence Splitting")
    for document in sourceElements:
        docCount += 1
        origId = document.get("pmid")
        if origId == None:
            origId = document.get("origId")
        origId = str(origId)
        counter.update(1, "Splitting Documents ("+document.get("id")+"/" + origId + "): ")
        docId = document.get("id")
        if docId == None:
            docId = "CORPUS.d" + str(docCount)
        if document.find("sentence") == None: # no existing sentence split                
            text = document.get("text")
            if text == None or text.strip() == "":
                continue
            
            newFile = os.path.join(tokenizationPath, origId + ".tok")
            f = openFile(newFile, tarFile)
            if f == None: # file with BioNLP'11 extension not found, try BioNLP'09 extension
                oldFile = os.path.join(tokenizationPath, origId + ".tokenized")
                f = openFile(oldFile, tarFile)
                if f == None: # no tokenization found
                    continue
            sentencesCreated += alignSentences(document, f.readlines(), escDict, ignoreErrors=ignoreErrors)
            f.close()
    
            # Remove original text
            if removeText:
                del document["text"]
            # Move elements from document element to sentences
            moveElements(document)
            docsWithSentences += 1
        else:
            docsWithSentences += 1
    
    if tarFile != None:
        tarFile.close()
    print >> sys.stderr, "Sentence splitting created", sentencesCreated, "sentences"
    print >> sys.stderr, docsWithSentences, "/", docCount, "documents have sentences"
        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

def alignSentences(document, sentenceTexts, escDict={}, ignoreErrors=False):
    text = document.get("text")
    start = 0 # sentences are consecutively aligned to the text for charOffsets
    cEnd = 0
    sentenceCount = 0
    head = None
    sentenceStart = None
    #text = text.replace("\n", " ") # should stop sentence splitter from crashing.
    #text = text.replace("  ", " ") # should stop sentence splitter from crashing.
    sText = None
    prevSentence = None
    for sText in sentenceTexts:
        sText = sText.strip() # The text of the sentence
        for key in sorted(escDict.keys()):
            sText = sText.replace(key, escDict[key])
        if sText == "":
            print >> sys.stderr, "Warning, empty sentence in", document.get("id"), document.get("origId")
            continue
        isFirst = True
        prevCStart = None
        for sToken in sText.split():
            # Find the starting point of the token in the text. This
            # point must be after previous sentences
            cStart = text.find(sToken, start) # find start position
            if ignoreErrors and cStart == -1:
                print >> sys.stderr, "Warning, cannot align token", sToken.encode("utf-8"), "for document", document.get("id"), document.get("origId")
                prevCStart = cStart
                continue
            else:
                assert cStart != -1, (text, sText, sToken, start, document.get("id"), document.get("origId"))
            if prevCStart != -1 and not text[cEnd:cStart].strip() == "":
                print >> sys.stderr,  "-----------------------------"
                print >> sys.stderr,  "text:", text.encode("utf-8")
                print >> sys.stderr,  "text[cEnd:cStart+1]:", text[cEnd:cStart+1].encode("utf-8")
                print >> sys.stderr,  "prevSText:", prevSText.encode("utf-8")
                print >> sys.stderr,  "sText:", sText.encode("utf-8")
                print >> sys.stderr,  "sToken:", sToken.encode("utf-8")
                print >> sys.stderr,  "start:", start
                print >> sys.stderr,  "-----------------------------"
                assert False
            #assert text[cEnd:cStart].strip() == "", (text, text[cEnd:cStart+1], sText, sToken, start) # only whitespace should separate words
            tail = None
            if isFirst:
                sentenceStart = cStart
                if cStart - start != 0 and prevSentence != None:
                    prevSentence.set("tail", text[start:cStart])
            if cEnd == 0 and cStart != 0:
                head = text[cEnd:cStart]
            cEnd = cStart + len(sToken) # end position is determined by length
            start = cStart + len(sToken) # for next token, start search from end of this one
            isFirst = False
            prevCStart = cStart
        # make sentence element
        e = ET.Element("sentence")
        if head != None:
            e.set("head", head)
        e.set("text", text[sentenceStart:cEnd])
        e.set("charOffset", str(sentenceStart) + "-" + str(cEnd)) # NOTE: check
        e.set("id", document.get("id") + ".s" + str(sentenceCount))
        document.append(e) # add sentence to parent element
        prevSentence = e
        sentenceCount += 1
        if sentenceCount == len(sentenceTexts): # set tail of last sentence in document
            if cEnd <= len(text):
                e.set("tail", text[cEnd:])
        prevSText = sText
    return sentenceCount
    
    
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

    optparser = OptionParser(description="For inserting an existing sentence splitting")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-t", "--tokenizationPath", default=None, dest="tokenizationPath", help="Tokenization path", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    makeSentences(input=options.input, tokenizationPath=options.tokenizationPath, output=options.output, removeText=False)
    