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
from Utils.ProgressCounter import ProgressCounter
                
def process(input, output=None):
    """
    Run and preprocess MetaMap.
    """    
    counter = ProgressCounter(None, "MetaMap")
    
    counts = defaultdict(int)
    
    outWriter = None
    if output != None:
        outWriter = ETUtils.ETWriter(output)

    skip = False
    for event in ETUtils.ETIteratorFromObj(input, ("start", "end")):
        if event[0] == "start":
            if event[1].tag == "sentence":
                sentence = event[1]
                counter.update(1, "Processing MetaMap ("+sentence.get("id")+"): ")
            if not skip:
                outWriter.begin(event[1])
                counts[event[1].tag + ":kept"] += 1
            else:
                counts[event[1].tag + ":removed"] += 1
        elif event[0] == "end":
            if not skip:
                outWriter.end(event[1])
    
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
    