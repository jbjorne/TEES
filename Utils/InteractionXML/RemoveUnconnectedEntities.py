import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils

def removeUnconnectedEntities(input, output=None):
    input = ETUtils.ETFromObj(input)
    root = input.getroot()
    removed = 0
    preserved = 0
    for document in root.findall("document"):
        sentMap = {} # allow for intersentence interactions
        for sentence in document.findall("sentence"):
            sentMap[sentence.get("id")] = sentence
        connected = set()
        for interaction in document.getiterator("interaction"):
            connected.add(interaction.get("e1"))
            connected.add(interaction.get("e2"))
        entities = []
        for entity in document.getiterator("entity"):
            entities.append(entity)
        for entity in entities:
            if entity.get("given") == "True": # never remove named entities
                continue
            eId = entity.get("id")
            if eId not in connected:
                if eId.find(".s") != -1: # sentence level entity
                    sentMap[eId.rsplit(".", 1)[0]].remove(entity)
                else: # document level entity
                    document.remove(entity)
                removed += 1
            else:
                preserved += 1
    
    print >> sys.stderr, "Removed", removed, "entities, preserved", preserved, "entities"
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(root, output)
    return input

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
    
    if options.input == None:
        print >> sys.stderr, "Error, first input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)
    
    removeUnconnectedEntities(options.input, options.output)
