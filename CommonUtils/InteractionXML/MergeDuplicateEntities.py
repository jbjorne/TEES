import CorpusElements
import cElementTreeUtils as ETUtils
from optparse import OptionParser
import sys

def compareEntities(entity1, entity2):
    if entity1.get("charOffset") == entity2.get("charOffset") and entity1.get("type") == entity2.get("type"):
        #assert(entity1.get("isName") == entity2.get("isName"))
        assert(entity1.get("headOffset") == entity2.get("headOffset"))
        assert(entity1.get("text") == entity2.get("text"))
        return True
    else:
        return False

def compareInteractions(interaction1, interaction2):
    if interaction1.get("e1") == interaction2.get("e1") and interaction1.get("e2") == interaction2.get("e2") and interaction1.get("type") == interaction2.get("type"):
        assert(interaction1.get("interaction") == interaction2.get("interaction"))
        return True
    else:
        return False

def mergeDuplicateEntities(corpusElements):
    print >> sys.stderr, "Merging duplicate entities"
    entitiesByType = {}
    duplicatesRemovedByType = {}
    for sentence in corpusElements.sentences:
        entityIsDuplicateOf = {}
        for k in sentence.entitiesById.keys():
            entityIsDuplicateOf[k] = None
            if not entitiesByType.has_key(sentence.entitiesById[k].attrib["type"]):
                entitiesByType[sentence.entitiesById[k].attrib["type"]] = 0
            entitiesByType[sentence.entitiesById[k].attrib["type"]] += 1
        # Mark entities for removal
        for i in range(len(sentence.entities)-1):
            if entityIsDuplicateOf[sentence.entities[i].attrib["id"]] == None:
                for j in range(i+1,len(sentence.entities)):
                    if compareEntities(sentence.entities[i], sentence.entities[j]):
                        entityIsDuplicateOf[sentence.entities[j].attrib["id"]] = sentence.entities[i].attrib["id"]                    
        # Remove entities from sentence element
        for k,v in entityIsDuplicateOf.iteritems():
            if v != None:
                entityToRemove = sentence.entitiesById[k]
                if not duplicatesRemovedByType.has_key(entityToRemove.attrib["type"]):
                    duplicatesRemovedByType[entityToRemove.attrib["type"]] = 0
                duplicatesRemovedByType[entityToRemove.attrib["type"]] += 1
                sentence.sentence.remove(entityToRemove)
        # Remap pairs and interactions that used the removed entities
        for pair in sentence.pairs + sentence.interactions:
            if entityIsDuplicateOf[pair.attrib["e1"]] != None:
                pair.attrib["e1"] = entityIsDuplicateOf[pair.attrib["e1"]]
            if entityIsDuplicateOf[pair.attrib["e2"]] != None:
                pair.attrib["e2"] = entityIsDuplicateOf[pair.attrib["e2"]]
    
    printStats(entitiesByType, duplicatesRemovedByType)

def mergeDuplicateInteractions(corpusElements):
    print >> sys.stderr, "Merging duplicate interactions"
    interactionsByType = {}
    duplicatesRemovedByType = {}
    for sentence in corpusElements.sentences:
        interactions = sentence.pairs + sentence.interactions
        interactionIsDuplicateOf = {}
        for interaction in interactions:
            interactionIsDuplicateOf[interaction.attrib["id"]] = None
            if not interactionsByType.has_key(interaction.attrib["type"]):
                interactionsByType[interaction.attrib["type"]] = 0
            interactionsByType[interaction.attrib["type"]] += 1
        # Mark entities for removal
        for i in range(len(interactions)-1):
            if interactionIsDuplicateOf[interactions[i].attrib["id"]] == None:
                for j in range(i+1,len(interactions)):
                    if compareInteractions(interactions[i], interactions[j]):
                        interactionIsDuplicateOf[interactions[j].attrib["id"]] = interactions[i].attrib["id"]                    
        # Remove entities from sentence element
        for k,v in interactionIsDuplicateOf.iteritems():
            if v != None:
                elementToRemove = None
                if k.rsplit(".",1)[-1][0] == "p":
                    for pair in sentence.pairs:
                        if pair.attrib["id"] == k:
                            elementToRemove = pair
                            break
                elif k.rsplit(".",1)[-1][0] == "i":
                    for interaction in sentence.interactions:
                        if interaction.attrib["id"] == k:
                            elementToRemove = interaction
                            break

                if not duplicatesRemovedByType.has_key(elementToRemove.attrib["type"]):
                    duplicatesRemovedByType[elementToRemove.attrib["type"]] = 0
                duplicatesRemovedByType[elementToRemove.attrib["type"]] += 1
                sentence.sentence.remove(elementToRemove)
    
    printStats(interactionsByType, duplicatesRemovedByType)

def printStats(origItemsByType, duplicatesRemovedByType):    
    print >> sys.stderr, "Removed duplicates (original count in parenthesis):"
    keys = duplicatesRemovedByType.keys()
    keys.sort()
    for key in keys:
        print >> sys.stderr, "  " + key + ": " + str(duplicatesRemovedByType[key]) + " (" + str(origItemsByType[key]) + ")"
    print >> sys.stderr, "  ---------------------------------"
    print >> sys.stderr, "  Total: " + str(sum(duplicatesRemovedByType.values())) + " (" + str(sum(origItemsByType.values())) + ")"

def mergeAll(input, output=None):
    corpusElements = CorpusElements.loadCorpus(input)
    mergeDuplicateEntities(corpusElements)
    mergeDuplicateInteractions(corpusElements)
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusElements.rootElement, output)
    return corpusElements

if __name__=="__main__":
    print >> sys.stderr, "##### Merge duplicate entities and interactions #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.output != None)
    
    mergeAll(options.input, options.output)
