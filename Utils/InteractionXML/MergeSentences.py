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
        # Check that the entity has only sentence elements as children
        children = [x for x in document]
        docChildTypes = sorted(set([x.tag for x in children]))
        if len(docChildTypes) == 0:
            counts["documents-with-no-sentences"] += 1
            continue
        elif len(docChildTypes) == 1:
            assert docChildTypes[0] == "sentence"
        else:
            raise Exception("Document '" + str(document.get("id")) + "' has non-sentence children: " + str(docChildTypes))
        # Process all the child sentence elements
        docId = document.get("id")
        interactions = []
        entities = []
        entityById = {}
        combinedText = ""
        for sentence in children:
            document.remove(sentence)
            combinedText += sentence.get("head", "") + sentence.get("text", "") + sentence.get("tail", "")
            sentOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            # Collect and update the entity elements
            for entity in sentence.findall("entity"):
                # Map sentence-level entity offsets to document level
                for offsetKey in ("charOffset", "headOffset"):
                    if entity.get(offsetKey) != None:
                        offset = Range.charOffsetToTuples(entity.get(offsetKey))
                        for i in range(len(offset)):
                            offset[i] = (offset[i][0] + sentOffset[0], offset[i][1] + sentOffset[0])
                        # Compare a continous entity's text with the combined sentence text
                        if offsetKey == "charOffset" and len(offset) == 1:
                            if not Range.contains((0, len(combinedText)), offset[0]):
                                raise Exception("Document '" + str(document.get("id")) + "' entity '" + str(entity.get("id")) + "' offset is not contained in combined sentence text: " + str([entity.attrib, offset, [0, len(combinedText)], combinedText]))
                            combTextSpan = combinedText[offset[0][0]:offset[0][1]]
                            if entity.get("text") != combTextSpan:
                                raise Exception("Document '" + str(document.get("id")) + "' entity '" + str(entity.get("id")) + "' text does not match combined sentence text: " + str([entity.get("text"), combTextSpan]))
                            counts["checked-charOffsets"] += 1
                        entity.set(offsetKey, Range.tuplesToCharOffset(offset))
                # Compare mapped offsets to origOffset, if available
                if entity.get("origOffset") != None:
                    if entity.get("charOffset") != entity.get("origOffset"):
                        raise Exception("Document '" + str(document.get("id")) + "' entity '" + str(entity.get("id")) + "' new charOffset differs from origOffset: " + str([entity.get("charOffset"), entity.get("origOffset")]))
                    counts["checked-origOffsets"] += 1
                    del entity.attrib["origOffset"]
                assert entity.get("id") not in entityById
                entityById[entity.get("id")] = entity # For re-mapping the interaction e1 and e2 attributes
                entity.set("id", docId + ".e" + str(len(entities))) # Update the id for the document level
                entities.append(entity)
                counts["moved-entities"] += 1
            # Collect and update the interaction elements
            for interaction in sentence.findall("interaction"):
                interaction.set("id", docId + ".i" + str(len(interactions))) # Update the id for the document level
                interactions.append(interaction)
                counts["moved-interactions"] += 1
        # Check that the combined sentence text matches the document text, if available
        if document.get("text") != None and document.get("text") != combinedText:
            if combinedText == document.get("text")[0:len(combinedText)] and document.get("text")[len(combinedText):].strip() == "":
                print >> sys.stderr, "Warning, document '" + document.get("id") + "' text has trailing whitespace not included in the combined sentence text"
                combinedText = document.get("text") 
            else:
                raise Exception("Document '" + str(document.get("id")) + "' text differs from combined sentence text: " + str([document.get("text"), combinedText]))
            counts["checked-document-texts"] += 1
        # Set the combined text as the document text
        document.set("text", combinedText)
        # Update interaction e1 and e2 ids (cannot be done earlier because interactions may refer to entities in multiple sentences)
        for interaction in sentence.findall("interaction"):
            for entKey in ("e1", "e2"):
                interaction.set(entKey, entityById[interaction.get(entKey)].get("id"))
        # Add the entity and interaction elements to the document
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
