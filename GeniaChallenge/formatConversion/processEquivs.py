import cElementTreeUtils as ETUtils

def insertInteraction(sentence, interaction):
    interactions = sentence.findall("interaction")
    newIdNumber = getNextFreeId(interactions)
    interaction.set("id", sentence.get("id") + "." + str(newIdNumber))
    sentence.insertElement(interaction, interactions[-1])

def duplicateFlat(sourceEnt, targetEnt):
    sourceEntId = sourceEnt.get("id")
    targetEntId = targetEnt.get("id")
    for interaction in interactionsByEntity[sourceEnt]:
        e1 = interaction.get("e1")
        e2 = interaction.get("e2")
        assert e2 == sourceEntId
        sentenceId = interaction.get("id").rsplit(".", 1)
        sentence = sentencesById[sentenceId]
        
        # Create new interaction (or pair) element
        newInteraction = ET.Element(interaction.tag)
        newInteraction.set("e2", targetEntId)
        newInteraction.set("e1", sourceEntId)
        insertInteraction(sentence, newInteraction)

def getElementsById(tag, root):
    elementById = {}
    for e in root.getiterator("tag"):
        id = e.get("id")
        assert id != None
        assert not elementsById.has_key(id)
        elementById[id] = e
    return elementById

def processEquivs(tree):
    ETUtils.ETFromObje(input)
    root = tree.getroot()
    interactions = root.findall("interaction") + root.findall("pair")
    for interaction in interactions:
        if interaction.get("type") == "Equiv":
            duplicate(entitiesById[interaction.get("e1")], entitiesById[interaction.get("e2")])
    ETUtils.write(tree, output)

if __name__=="__main__":
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output-folder")
    (options, args) = optparser.parse_args()
    
    