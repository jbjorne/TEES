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

if __name__=="__main__":
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.output != None)
    
    corpusElements = CorpusElements.loadCorpus(options.input)
    
    print >> sys.stderr, "Merging duplicates"
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
    
    print >> sys.stderr, "Removed duplicates (original count in parenthesis):"
    keys = duplicatesRemovedByType.keys()
    keys.sort()
    for key in keys:
        print >> sys.stderr, "  " + key + ": " + str(duplicatesRemovedByType[key]) + " (" + str(entitiesByType[key]) + ")"
    print >> sys.stderr, "  ---------------------------------"
    print >> sys.stderr, "  Total: " + str(sum(duplicatesRemovedByType.values())) + " (" + str(sum(entitiesByType.values())) + ")"
    
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(corpusElements.rootElement, options.output)
