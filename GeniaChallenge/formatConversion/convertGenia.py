"""
Convert Shared Task format to Interaction XML
"""
try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import sys, os
import subprocess

thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import readTokenization
from InteractionXML.RecalculateIds import recalculateIds
import geniaToGifxml
from Utils.FindHeads import findHeads

def convert(inputDir, outputFilename, parse, tokenization, task=1, removeDuplicates=True, extra=True):
    geniaToGifxml.process(inputDir, task, outputFilename, removeDuplicates, extra)
    # Make sure geniaToGifxml worked
    assert os.path.exists(outputFilename)
    
    # Parse insertion
    corpus= ET.parse(outputFilename).getroot()
    corpus = readTokenization.reorderCorpus(corpus,inputDir)
    # Fix ids
    corpus = recalculateIds(corpus, outputFilename)
    # Split protein names
    splitterCommand = "python ProteinNameSplitter.py -f " + outputFilename + " -o " + outputFilename + " -p " + parse + " -t " + tokenization + " -s split-" + tokenization + " -n split-" + parse
    p = subprocess.Popen(splitterCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    printLines(p.stderr.readlines())
    printLines(p.stdout.readlines())
    # Head detection
    corpus= ET.parse(outputFilename).getroot()
    findHeads(corpus, parse, tokenization, outputFilename)
    # Remove unneeded ThemeX and CauseX
    print >> sys.stderr, "Removing ThemeX and CauseX"
    perlCommand = "perl -pi -e \'s/\\\"(Theme|Cause|Site|CSite|AtLoc|ToLoc)[0-9]+\\\"/\\\"$1\\\"/g' " + outputFilename
    p = subprocess.Popen(perlCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    printLines(p.stderr.readlines())
    printLines(p.stdout.readlines())

def printLines(lines):
    for line in lines:
        print >> sys.stderr, line[:-1]

if __name__=="__main__":
    print >> sys.stderr, "##### Convert BioNLP'09 Shared Task GENIA to Interaction XML #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nConvert shared task data to interaction xml.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input directory with a1, a2, txt, dep etc. files")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output interaction xml file name")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse element name in interaction XML")
    optparser.add_option("-k", "--tokenization", default=None, dest="tokenization", help="Tokenization element name in interaction XML")
    optparser.add_option("-r", "--remove",
                  dest="remove_duplicates",
                  help="Remove duplicate nodes and edges",
                  default=True,
                  action="store_false")
    optparser.add_option("-e", "--extra",
                  dest="modify_extra",
                  help="Modify extra arguments (do not use if you do not know what it does)",
                  default=False,
                  action="store_true")
    optparser.add_option("-t", "--task",
                  dest="task",
                  help="Which tasks to process (a2.tXXX file must be present)",
                  choices=["1","12","13","123"],
                  default="1",
                  metavar="[1|12|13|123]")
    (options, args) = optparser.parse_args()
    
    convert(options.input, options.output, options.parse, options.tokenization, options.task, options.remove_duplicates, options.modify_extra)
    
    