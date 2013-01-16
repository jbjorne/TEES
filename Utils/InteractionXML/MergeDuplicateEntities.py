import CorpusElements
import SentenceElements
import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Utils.ElementTreeUtils as ETUtils
from optparse import OptionParser
import sys
from collections import defaultdict

def compareEntities(entity1, entity2):
    if entity1.get("charOffset") == entity2.get("charOffset") and entity1.get("type") == entity2.get("type"):
        #assert(entity1.get("given") == entity2.get("given"))
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

def mergeDuplicateEntities(sentences, debug=False):
    entitiesByType = {}
    duplicatesRemovedByType = {}
    globalEntityIsDuplicateOf = {}
    for sentence in sentences:
        entityIsDuplicateOf = {}
        for k in sentence.entitiesById.keys():
            assert k not in entityIsDuplicateOf
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
            assert k not in globalEntityIsDuplicateOf, k
            globalEntityIsDuplicateOf[k] = v
            if v != None:
                entityToRemove = sentence.entitiesById[k]
                if not duplicatesRemovedByType.has_key(entityToRemove.attrib["type"]):
                    duplicatesRemovedByType[entityToRemove.attrib["type"]] = 0
                duplicatesRemovedByType[entityToRemove.attrib["type"]] += 1
                sentence.sentence.remove(entityToRemove)
                if debug: print "Removing Entity", k, "duplicate of", v
    # Remap pairs and interactions that used the removed entities
    for sentence in sentences:
        for pair in sentence.pairs + sentence.interactions:
#            if pair.get("id") == "GE.d1.s13.i56":
#                print "BEFORE"
#                print pair.get("e1"), globalEntityIsDuplicateOf[pair.get("e1")]
#                print pair.get("e2"), globalEntityIsDuplicateOf[pair.get("e2")]
            if pair.get("e1") not in globalEntityIsDuplicateOf or pair.get("e2") not in globalEntityIsDuplicateOf:
                print >> sys.stderr, "Warning, interaction", pair.get("id"), [pair.get("e1"), pair.get("e2")], "links to a non-existing entity"
                continue
            if globalEntityIsDuplicateOf[pair.attrib["e1"]] != None:
                pair.attrib["e1"] = globalEntityIsDuplicateOf[pair.attrib["e1"]]
                if debug: print "Remapping", pair.get("id"), "arg e1 from", pair.get("e1"), "to", globalEntityIsDuplicateOf[pair.get("e1")]
            if globalEntityIsDuplicateOf[pair.attrib["e2"]] != None:
                pair.attrib["e2"] = globalEntityIsDuplicateOf[pair.attrib["e2"]]
                if debug: print "Remapping", pair.get("id"), "arg e2 from", pair.get("e2"), "to", globalEntityIsDuplicateOf[pair.get("e2")]
#            if pair.get("id") == "GE.d1.s13.i56":
#                print "AFTER"
#                print pair.get("e1"), globalEntityIsDuplicateOf[pair.get("e1")]
#                print pair.get("e2"), globalEntityIsDuplicateOf[pair.get("e2")]
#                pair.set("Processed", "True")
    
    return entitiesByType, duplicatesRemovedByType

def mergeDuplicateInteractions(sentences, debug=False):
    interactionsByType = {}
    duplicatesRemovedByType = {}
    for sentence in sentences:
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
                if debug: print "Removing Interaction", k, "duplicate of", v
    
    return interactionsByType, duplicatesRemovedByType

def printStats(origItemsByType, duplicatesRemovedByType):    
    print >> sys.stderr, "Removed duplicates (original count in parenthesis):"
    keys = duplicatesRemovedByType.keys()
    keys.sort()
    for key in keys:
        print >> sys.stderr, "  " + key + ": " + str(duplicatesRemovedByType[key]) + " (" + str(origItemsByType[key]) + ")"
    print >> sys.stderr, "  ---------------------------------"
    print >> sys.stderr, "  Total: " + str(sum(duplicatesRemovedByType.values())) + " (" + str(sum(origItemsByType.values())) + ")"

def mergeAll(input, output=None, debug=False, iterate=False):
    if iterate:
        origItems = defaultdict(int)
        removedItems = defaultdict(int)
        for docSentences in SentenceElements.getCorpusIterator(input, output):
            entitiesByType, duplicatesRemovedByType = mergeDuplicateEntities(docSentences, debug)
            for key in entitiesByType: origItems[key] += entitiesByType[key]
            for key in duplicatesRemovedByType: removedItems[key] += duplicatesRemovedByType[key]
            interactionsByType, duplicatesRemovedByType = mergeDuplicateInteractions(docSentences, debug)
            for key in interactionsByType: origItems[key] += interactionsByType[key]
            for key in duplicatesRemovedByType: removedItems[key] += duplicatesRemovedByType[key]
        printStats(origItems, removedItems)
        return None
    else:
        corpusElements = CorpusElements.loadCorpus(input, removeIntersentenceInteractions=False)
        print >> sys.stderr, "Merging duplicate entities"
        entitiesByType, duplicatesRemovedByType = mergeDuplicateEntities(corpusElements.sentences, debug)
        printStats(entitiesByType, duplicatesRemovedByType)
        print >> sys.stderr, "Merging duplicate interactions"
        interactionsByType, duplicatesRemovedByType = mergeDuplicateInteractions(corpusElements.sentences, debug)
        printStats(interactionsByType, duplicatesRemovedByType)
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
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="")
    optparser.add_option("-r", "--iterate", default=False, action="store_true", dest="iterate", help="")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    #assert(options.output != None)
    
    mergeAll(options.input, options.output, options.debug, options.iterate)
