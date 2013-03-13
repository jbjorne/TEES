import sys,os
import sys
import xml.etree.cElementTree as ET

import shutil
import subprocess
import tempfile
import codecs
import tarfile

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from Utils.ProgressCounter import ProgressCounter
                
def process(input, output=None):
    """
    Run and preprocess MetaMap.
    """
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    docCount = 0
    counter = ProgressCounter(len(sourceElements), "Sentence Splitting")
    for document in corpusRoot.findall("document"):
        docCount += 1
        origId = document.get("pmid")
        if origId == None:
            origId = document.get("origId")
        origId = str(origId)
        counter.update(1, "Splitting Documents ("+document.get("id")+"/" + origId + "): ")
        for sentence in document.findall("sentence"):
            pass
            
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

    optparser = OptionParser(description="MetaMap processing")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    makeSentences(input=options.input, tokenizationPath=options.tokenizationPath, output=options.output, removeText=False)
    