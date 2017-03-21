import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
from collections import defaultdict

def mergeSentences(input, output):
    print >> sys.stderr, "Merging sentences into documents"
    print >> sys.stderr, "Loading corpus file", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    counts = defaultdict(int)
    for document in corpusRoot.findall("document"):
        counts["documents"] += 1
        children = [x for x in document]
        docChildTypes = sorted(set([x.tag for x in children]))
        if len(docChildTypes) == 0:
            counts["documents-with-no-sentences"] += 1
            continue
        elif len(docChildTypes) == 1:
            assert docChildTypes[0] == "sentence"
        else:
            raise Exception("Document '" + str(document.get("id")) + "' has non-sentence children: " + str(docChildTypes))
        docId = document.get("id")
        interactions = []
        entities = []
        entityById = {}
        combinedText = ""
        for sentence in children:
            document.remove(sentence)
            combinedText += sentence.get("head", "") + sentence.get("text", "") + sentence.get("tail", "")
            sentOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            for entity in sentence.findall("entity"):
                for offsetKey in ("charOffset", "headOffset"):
                    if entity.get(offsetKey) != None:
                        offset = Range.charOffsetToTuples(entity.get(offsetKey))
                        for i in range(len(offset)):
                            offset[i][0] += sentOffset[0]
                            offset[i][1] += sentOffset[0]
                        entity.set(offsetKey, Range.tuplesToCharOffset(offset))
                assert entity.get("id") not in entityById
                entityById[entity.get("id")] = entity
                entity.set("id", docId + ".e" + str(len(entities)))
                entities.append(entity)
                counts["moved-entities"] += 1
            for interaction in sentence.findall("interaction"):
                for entKey in ("e1", "e2"):
                    interaction.set(entKey, entityById[interaction.get(entKey)].get("id"))
                interaction.set("id", docId + ".i" + str(len(interactions)))
                interactions.append(interaction)
                counts["moved-interactions"] += 1
        if document.get("text") != None and document.get("text") != combinedText:
            raise Exception("Document '" + str(document.get("id")) + "' text differs from combined sentence text: " + str([document.get("text"), combinedText]))
        document.extend(entities)
        document.extend(interactions)
    print >> sys.stderr, "Counts:", dict(counts)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

if __name__=="__main__":
    print >> sys.stderr, "##### Delete Elements #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)

    processCorpus(options.input, options.output, rules, options.reverse)
