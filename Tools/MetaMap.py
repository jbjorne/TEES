import sys,os
import xml.etree.cElementTree as ET

import shutil
import subprocess
import tempfile
import codecs

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
from Utils.ProgressCounter import ProgressCounter

def convert(metamapEl, sentenceEl):
    """
    Convert MetaMap XML into phrase-elements
    """
    newMetamapEl = ET.Element("metamap") # make a new metamap element
    utteranceCount = 0
    for utterance in metamapEl.getiterator("Utterance"): # process all utterances (sentences)
        utteranceCount += 1
        #print "UT:", utterance.find("UttText").text
        uttOffsetBegin = int(utterance.find("UttStartPos").text)
        for phrase in utterance.getiterator("Phrase"): # process all phrases for each utterance
            #print "Phrase:", phrase.find("PhraseText").text
            phraseEl = ET.Element("phrase")
            phraseOffset = [int(phrase.find("PhraseStartPos").text), int(phrase.find("PhraseStartPos").text) + int(phrase.find("PhraseLength").text)]
            phraseOffset = [phraseOffset[0] - uttOffsetBegin, phraseOffset[1] - uttOffsetBegin]
            phraseEl.set("charOffset", Range.tuplesToCharOffset(phraseOffset))
            phraseEl.set("text", phrase.find("PhraseText").text)
            for candidate in phrase.getiterator("Candidate"): # process first candidate of each phrase
                phraseEl.set("score", candidate.find("CandidateScore").text)
                phraseEl.set("cui", candidate.find("CandidateCUI").text)
                phraseEl.set("matched", candidate.find("CandidateMatched").text)
                phraseEl.set("preferred", candidate.find("CandidatePreferred").text)
                semTypes = set()
                for semType in candidate.getiterator("SemType"):
                    semTypes.add(semType.text)
                phraseEl.set("semTypes", ",".join(sorted(list(semTypes))))
                sources = set()
                for source in candidate.getiterator("Source"):
                    sources.add(source.text)
                phraseEl.set("sources", ",".join(sorted(list(sources))))
                break
            if phraseEl.get("matched") != None: # include only matched phrases as new elements
                newMetamapEl.append(phraseEl)
            #print ET.tostring(phraseEl, "utf-8")
    
    if utteranceCount > 1:
        print >> sys.stderr, "Warning, sentence", sentenceEl.get("id"), "has", utteranceCount, "utterances"
    return newMetamapEl
                
def process(input, output=None, preprocess=True, debug=False):
    """
    Run MetaMap.
    """    
    counter = ProgressCounter(id="MetaMap")
    
    # Create working directory
    workdir = tempfile.mkdtemp()
    
    outWriter = None
    if output != None:
        outWriter = ETUtils.ETWriter(output)
    
    # Loop iteratively over elements
    skip = False
    for event, element in ETUtils.ETIteratorFromObj(input, ("start", "end")):
        if event == "start": # element start message, element may not be fully read yet
            if element.tag == "sentence":
                sentence = element
                counter.update(1, "Processing MetaMap ("+sentence.get("id")+"): ")
                # Run metamap for the sentence element
            elif element.tag == "metamap": # skip the metamap element to remove the original one
                skip = True
            if not skip and output != None:
                outWriter.begin(element)
        
        elif event == "end": # element is fully read in memory
            if not skip and output != None:
                outWriter.end(element)

            if element.tag == "metamap":
                skip = False # write elements again after this one
                if preprocess:
                    element = convert(element, sentence)
                outWriter.write(element) # insert the new metamap element into the output stream
        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        outWriter.close()
        ETUtils.encodeNewlines(output)

    if debug:
        print >> sys.stderr, "Work directory preserved for debugging at", workdir
    else:
        shutil.rmtree(workdir)

    return output
    
if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(description="MetaMap processing")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-n", "--no_preprocess", default=False, action="store_true", dest="no_preprocess", help="Preprocess MetaMap output")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="Debug mode")
    (options, args) = optparser.parse_args()
    
    process(input=options.input, output=options.output, preprocess=not options.no_preprocess, debug=options.debug)
    