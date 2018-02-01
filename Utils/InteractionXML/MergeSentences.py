import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
from collections import defaultdict

def mergeSentences(input, output, verbose=False):
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
        elif len(docChildTypes) > 1 or docChildTypes[0] != "sentence":
            raise Exception("Document '" + str(document.get("id")) + "' has non-sentence children: " + str(docChildTypes))
        # Process all the child sentence elements
        docId = document.get("id")
        interactions = []
        entities = []
        entityById = {}
        interactionById = {}
        combinedText = ""
        calculatedOffset = (0, 0)
        for sentence in children:
            document.remove(sentence)
            sentenceText = sentence.get("head", "") + sentence.get("text", "") + sentence.get("tail", "")
            sentOffset = sentence.get("charOffset")
            if sentence == children[0]:
                noDefinedOffsets = sentOffset == None
            elif (sentOffset == None) != noDefinedOffsets:
                raise Exception("Only some sentences in document '" + docId + "' have defined offsets")
            if sentOffset == None:
                if sentence != children[-1]:
                    sentenceText = sentenceText + " "
                calculatedOffset = (calculatedOffset[1], calculatedOffset[1] + len(sentenceText))
                sentOffset = calculatedOffset
            else:
                sentOffset = Range.charOffsetToSingleTuple(sentOffset)
            combinedText += sentenceText
            # Collect and update the entity elements
            for entity in sentence.findall("entity"):
                # Map sentence-level entity offsets to document level
                for offsetKey in ("charOffset", "headOffset"):
                    if entity.get(offsetKey) != None:
                        offset = Range.charOffsetToTuples(entity.get(offsetKey))
                        for i in range(len(offset)):
                            offset[i] = (offset[i][0] + sentOffset[0], offset[i][1] + sentOffset[0])
                        entity.set(offsetKey, Range.tuplesToCharOffset(offset))
                # Compare mapped offsets to origOffset, if available
                if entity.get("origOffset") != None:
                    if entity.get("charOffset") != entity.get("origOffset"):
                        raise Exception("Document '" + str(document.get("id")) + "' entity '" + str(entity.get("id")) + "' new charOffset differs from origOffset: " + str([entity.get("charOffset"), entity.get("origOffset")]))
                    counts["checked-origOffsets"] += 1
                    del entity.attrib["origOffset"]
                assert entity.get("id") not in entityById
                entityById[entity.get("id")] = entity # For re-mapping the interaction 'e1' and 'e2' attributes
                entities.append(entity)
                counts["moved-entities"] += 1
            # Collect and update the interaction elements
            for interaction in sentence.findall("interaction"):
                assert interaction.get("id") not in interactionById
                interactionById[interaction.get("id")] = interaction # For re-mapping the interaction 'siteOf' attributes
                interactions.append(interaction)
                counts["moved-interactions"] += 1
        # Check that the combined sentence text matches the document text, if available
        if document.get("text") != None and document.get("text") != combinedText:
            if combinedText == document.get("text")[0:len(combinedText)] and document.get("text")[len(combinedText):].strip() == "":
                if verbose:
                    print >> sys.stderr, "Warning, document '" + document.get("id") + "' text has trailing whitespace not included in the combined sentence text"
                combinedText = document.get("text")
                counts["missing-trailing-whitespace"] += 1 
            else:
                raise Exception("Document '" + str(document.get("id")) + "' text differs from combined sentence text: " + str([document.get("text"), combinedText]))
            counts["checked-document-texts"] += 1
        # Check that the entities' texts match the document text
        for entity in entities:
            offset = Range.charOffsetToTuples(entity.get("charOffset"))
            if len(offset) == 1: # Compare only continous entities
                if not Range.contains((0, len(combinedText)), offset[0]):
                    raise Exception("Document '" + str(document.get("id")) + "' entity '" + str(entity.get("id")) + "' offset is not contained in combined sentence text: " + str([entity.attrib, offset, [0, len(combinedText)], combinedText]))
                combTextSpan = combinedText[offset[0][0]:offset[0][1]]
                if entity.get("text") != combTextSpan:
                    raise Exception("Document '" + str(document.get("id")) + "' entity '" + str(entity.get("id")) + "' text does not match combined sentence text: " + str([entity.get("text"), combTextSpan]))
                counts["checked-charOffsets"] += 1
        # Set the combined text as the document text
        document.set("text", combinedText)
        # Update entity and interaction ids (not done earlier so that possible error messages will refer to original ids, also because of siteOf-remapping)
        for i in range(len(entities)):
            entities[i].set("id", docId + ".e" + str(i)) # Update the id for the document level
        for i in range(len(interactions)):
            interaction.set("id", docId + ".i" + str(i)) # Update the id for the document level
        # Update interaction e1 and e2 ids (cannot be done earlier because interactions may refer to entities from multiple sentences)
        for i in range(len(interactions)):
            interaction = interactions[i]
            for entKey in ("e1", "e2"):
                interaction.set(entKey, entityById[interaction.get(entKey)].get("id"))
            if interaction.get("siteOf") != None:
                interaction.set("siteOf", interactionById[interaction.get("siteOf")].get("id"))
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
