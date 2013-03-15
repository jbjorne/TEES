import sys,os
import sys
import xml.etree.cElementTree as ET

import shutil
import subprocess
import tempfile
import codecs
import tarfile
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
from Utils.ProgressCounter import ProgressCounter
                
def process(input, output=None):
    """
    Preprocess MetaMap output.
    """    
    counter = ProgressCounter(id="MetaMap")
    
    counts = defaultdict(int)
    
    outWriter = None
    if output != None:
        outWriter = ETUtils.ETWriter(output)
    
    # Loop iteratively over elements
    skip = False
    for event in ETUtils.ETIteratorFromObj(input, ("start", "end")):
        if event[0] == "start": # element start message, element may not be fully read yet
            if event[1].tag == "sentence":
                sentence = event[1]
                counter.update(1, "Processing MetaMap ("+sentence.get("id")+"): ")
            elif event[1].tag == "metamap": # skip the metamap element to remove the original one
                skip = True
            if not skip and output != None:
                outWriter.begin(event[1])
                counts[event[1].tag + ":kept"] += 1
            else:
                counts[event[1].tag + ":removed"] += 1
        elif event[0] == "end": # element is fully read in memory
            if not skip and output != None:
                outWriter.end(event[1])
            if event[1].tag == "metamap":
                skip = False # write elements again after this one
                for utterance in event[1].getiterator("Utterance"): # process all utterances (sentences)
                    #print "UT:", utterance.find("UttText").text
                    uttOffsetBegin = int(utterance.find("UttStartPos").text)
                    metamapEl = ET.Element("metamap") # make a new metamap element
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
                            metamapEl.append(phraseEl)
                        #print ET.tostring(phraseEl, "utf-8")
                    outWriter.write(metamapEl) # insert the new metamap element into the output stream
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        outWriter.close()
        ETUtils.encodeNewlines(output)

    return output
    
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

    optparser = OptionParser(description="MetaMap processing")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    process(input=options.input, output=options.output)
    