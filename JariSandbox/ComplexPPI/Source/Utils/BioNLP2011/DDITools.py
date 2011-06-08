import sys
import cElementTreeUtils as ETUtils
from collections import defaultdict

def makeDDISubmissionFile(input, output):
    xml = ETUtils.ETFromObj(input)
    outFile = open(output, "wt")
    for sentence in xml.getiterator("sentence"):
        # First determine which pairs interact
        intMap = defaultdict(lambda:defaultdict(lambda:None))
        for interaction in sentence.findall("interaction"):
            # Make mapping both ways to discard edge directionality. This isn't actually needed,
            # since MultiEdgeExampleBuilder builds entity pairs in the same order as this function,
            # but shouldn't harm to include it and now it works regardless of pair direction.
            if interaction.get("type") != "neg":
                intMap[interaction.get("e1")][interaction.get("e2")] = interaction
                intMap[interaction.get("e2")][interaction.get("e1")] = interaction
        # Then write all pairs to the output file
        entities = sentence.findall("entity")
        for i in range(0, len(entities)-1):
            for j in range(i+1, len(entities)):
                eIId = entities[i].get("id")
                eJId = entities[j].get("id")
                outFile.write(eIId + "\t" + eJId + "\t")
                if intMap[eIId][eJId] != None:
                    outFile.write("1\n")
                else:
                    outFile.write("0\n")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input file (interaction XML)")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file (txt file)")
    (options, args) = optparser.parse_args()
    
    makeDDISubmissionFile(options.input, options.output)
