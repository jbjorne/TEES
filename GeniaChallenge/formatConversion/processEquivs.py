import sys
import InteractionXML.IDUtils as IDUtils

try:
    import cElementTree as ElementTree
except ImportError:
    import xml.etree.cElementTree as ElementTree
import cElementTreeUtils as ETUtils

def insertInteraction(sentence, interaction):
    interactions = sentence.findall("interaction")
    newIdNumber = IDUtils.getNextFreeId(interactions)
    interaction.set("id", sentence.get("id") + ".i" + str(newIdNumber))
    
    # insert into sentence
    inserted = False
    for i in range(len(sentence)):
        if sentence[i].tag == "sentenceanalyses":
            sentence.insert(i, interaction)
            inserted = True
    assert inserted

def duplicateFlat(sourceEnt, targetEnt, entitiesById, sentencesById, interactionsByEntity):
    sourceEntId = sourceEnt.get("id")
    targetEntId = targetEnt.get("id")
    if interactionsByEntity.has_key(sourceEntId):
        for interaction in interactionsByEntity[sourceEntId]:
            e1 = interaction.get("e1")
            e2 = interaction.get("e2")
            assert e2 == sourceEntId, (sourceEntId, targetEntId) # only named entities are duplicated
            sentenceId = interaction.get("id").rsplit(".", 1)[0]
            sentence = sentencesById[sentenceId]
            
            # Create new interaction (or pair) element
            newInteraction = ElementTree.Element(interaction.tag)
            newInteraction.set("e2", targetEntId)
            newInteraction.set("e1", e1)
            newInteraction.set("directed", "True")
            newInteraction.set("notes", "Equiv")
            newInteraction.set("type", interaction.get("type"))
            newInteraction.set("origId", interaction.get("origId"))
            insertInteraction(sentence, newInteraction)

def getElementsById(tag, root):
    elementsById = {}
    for e in root.getiterator(tag):
        id = e.get("id")
        assert id != None
        assert not elementsById.has_key(id)
        elementsById[id] = e
    return elementsById

def processEquivs(input, output):
    tree = ETUtils.ETFromObj(input)
    root = tree.getroot()
    entitiesById = getElementsById("entity", root)
    sentencesById = getElementsById("sentence", root)
    interactions = list(root.getiterator("interaction")) + list(root.getiterator("pair"))
    
    # map entities to their incoming interactions
    interactionsByEntity = {}
    for interaction in interactions:
        # Equivs are not interactions that we want to duplicate
        if interaction.get("type") == "Equiv":
            continue
        # outgoing
        e1 = interaction.get("e1")
        if not interactionsByEntity.has_key(e1):
            interactionsByEntity[e1] = []
        interactionsByEntity[e1].append(interaction)
        # incoming
        e2 = interaction.get("e2")
        if not interactionsByEntity.has_key(e2):
            interactionsByEntity[e2] = []
        interactionsByEntity[e2].append(interaction)
     
    count = 0 
    for interaction in interactions:
        print >> sys.stderr, "Processing interaction", count, "out of", len(interactions) 
        if interaction.get("type") == "Equiv":
            e1 = entitiesById[interaction.get("e1")]
            e2 = entitiesById[interaction.get("e2")]
            duplicateFlat(e2, e1, entitiesById, sentencesById, interactionsByEntity)
            # remove equiv
            sentenceId = interaction.get("id").rsplit(".", 1)[0]
            sentencesById[sentenceId].remove(interaction)
        count += 1
    ETUtils.writeUTF8(root, output)

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output-folder")
    (options, args) = optparser.parse_args()
    
    processEquivs(options.input, options.output)
    
    