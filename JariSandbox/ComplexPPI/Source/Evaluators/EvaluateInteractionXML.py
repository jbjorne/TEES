import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
#print os.path.dirname(os.path.abspath(__file__))+"/.."
from Utils.ProgressCounter import ProgressCounter
from Utils.Parameters import splitParameters
from optparse import OptionParser
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
import Utils.TableUtils as TableUtils
import InteractionXML.CorpusElements as CorpusElements
import copy

def compareEntitiesSimple(e1,e2,tokens=None):
    if e1.get("headOffset") == e2.get("headOffset") and e1.get("type") == e2.get("type"):
        return True
    else:
        return False

def compareEntitiesByGENIARelaxedOffsetMethod(e1, e2, tokens):
    e1Offset = Range.charOffsetToSingleTuple(e1.get("charOffset"))
    e2Offset = Range.charOffsetToSingleTuple(e2.get("charOffset"))
    goldOffset = [99999999999,-999999999999999]
    for i in range(len(tokens)):
        token = tokens[i]
        tokenOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
        if Range.overlap(tokenOffset,e2Offset):
            if i > 0:
                prevOffset = Range.charOffsetToSingleTuple(tokens[i-1].get("charOffset"))
            else:
                prevOffset = tokenOffset
            if goldOffset[0] > prevOffset[0]:
                goldOffset[0] = prevOffset[0]
            
            if i < len(tokens)-1:
                nextOffset = Range.charOffsetToSingleTuple(tokens[i+1].get("charOffset"))
            else:
                nextOffset = tokenOffset
            if goldOffset[1] < nextOffset[1]:
                goldOffset[1] = nextOffset[1]
        
    if e1Offset[0] >= goldOffset[1] and e1Offset[1] <= goldOffset[1]:
        return True
    else:
        return False        

def mapEntities(entitiesFrom, entitiesTo, tokens, compareFunction=compareEntitiesSimple):
    entityMap = {}
    for entityFrom in entitiesFrom:
        entityMap[entityFrom] = []
        for entityTo in entitiesTo:
            if compareFunction(entityFrom, entityTo, tokens):
                entityMap[entityFrom].append(entityTo)
    return entityMap

def getElementTypes(element):
    typeName = element.get("type")
    if typeName.find("---") != -1:
        return typeName.split("---")
    else:
        return [typeName]

def getEntityPredictions(entityMap, targetEntities, classSet, negativeClassId):
    predictions = []
    id = "Unknown.x0"
    for entityFrom, entitiesTo in entityMap.iteritems():
        if entityFrom.get("isName") == "True":
            continue
        found = False
        for entityTo in entitiesTo:
            predictions.append( ((id, classSet.getId(entityTo.get("type"))), classSet.getId(entityFrom.get("type")), None, None) )
            found = True
        if not found: # false positive prediction
            predictions.append( ((id, negativeClassId), classSet.getId(entityFrom.get("type")), None, None) )
    mappedTargetEntities = set()
    for eList in entityMap.values():
        for e in eList:
            mappedTargetEntities.add(e)
    for e in targetEntities:
        if e.get("isName") == "True":
            continue
        if not e in mappedTargetEntities: # false negative gold
            predictions.append( ((id, classSet.getId(e.get("type"))), negativeClassId, None, None) )
    return predictions

def getInteractionPredictions(interactionsFrom, interactionsTo, entityMap, classSet, negativeClassId):
    predictions = []
    id = "Unknown.x0"
    fromEntityIdToElement = {}
    for key in entityMap.keys():
        fromEntityIdToElement[key.get("id")] = key
    
    toInteractionsWithPredictions = set()
    for interactionFrom in interactionsFrom:
        e1s = entityMap[fromEntityIdToElement[interactionFrom.get("e1")]]
        e1Ids = []
        for e1 in e1s:
            e1Ids.append(e1.get("id"))
        e2s = entityMap[fromEntityIdToElement[interactionFrom.get("e2")]]
        e2Ids = []
        for e2 in e2s:
            e2Ids.append(e2.get("id"))
        
        found = False
        for interactionTo in interactionsTo:
            if interactionTo.get("e1") in e1Ids and interactionTo.get("e2") in e2Ids:
                toInteractionsWithPredictions.add(interactionTo)
                predictions.append( ((id, classSet.getId(interactionTo.get("type"))), classSet.getId(interactionFrom.get("type")), None, None) )
                found = True
        if not found: # false positive prediction
            predictions.append( ((id, negativeClassId), classSet.getId(interactionFrom.get("type")), None, None) )
    for interactionTo in interactionsTo:
        if interactionTo not in toInteractionsWithPredictions: # false negative gold
            predictions.append( ((id, classSet.getId(interactionTo.get("type"))), negativeClassId, None, None) )
    return predictions
    
def processSentence(fromSentence, toSentence, options, classSets, negativeClassId):
    splitMerged(fromSentence)
    entitiesFrom = fromSentence.entities
    entitiesTo = toSentence.entities
    tokens = fromSentence.tokens
    entityMap = mapEntities(entitiesFrom, entitiesTo, tokens, compareFunction=compareEntitiesSimple)
    
    entityPredictions = []
    interactionPredictions = []
    if options.target == "entities" or options.target == "both":
        entityPredictions = getEntityPredictions(entityMap, entitiesTo, classSets["entity"], negativeClassId)
    if options.target == "interactions" or options.target == "both":
        interactionPredictions = getInteractionPredictions(fromSentence.interactions + fromSentence.pairs, toSentence.interactions + toSentence.pairs, entityMap, classSets["interaction"], negativeClassId)
    
    return entityPredictions, interactionPredictions

def processCorpora(fromCorpus, toCorpus, options, classSets, negativeClassId):
    entityPredictions = []
    interactionPredictions = []
    counter = ProgressCounter(len(fromCorpus.sentences), "Corpus Processing")
    for i in range(len(fromCorpus.sentences)):
        counter.update(1)
        newEntityPredictions, newInteractionPredictions = processSentence(fromCorpus.sentences[i], toCorpus.sentences[i], options, classSets, negativeClassId)
        entityPredictions.extend(newEntityPredictions)
        interactionPredictions.extend(newInteractionPredictions)
    
    if len(entityPredictions) > 0:
        evaluator = Evaluator(entityPredictions, classSet=classSets["entity"])
        print evaluator.toStringConcise(title="Entities")    
    if len(interactionPredictions) > 0:
        evaluator = Evaluator(interactionPredictions, classSet=classSets["interaction"])
        print evaluator.toStringConcise(title="Interactions")    

def splitMerged(sentence):
    for sourceList in [sentence.entities, sentence.interactions, sentence.pairs]:
        for element in sourceList[:]:
            types = getElementTypes(element)
            if len(types) > 0:
                for type in types:
                    newElement = copy.copy(element)
                    sourceList.append(newElement)
                sourceList.remove(element)
    
if __name__=="__main__":
    import sys, os
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the statistics")
    optparser.add_option("-r", "--target", default="edges", dest="target", help="edges/entities/both")
    optparser.add_option("-e", "--evaluator", default="AveragingMultiClassEvaluator", dest="evaluator", help="Prediction evaluator class")
    optparser.add_option("-t", "--tokenization", default="split-Charniak-Lease", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-Charniak-Lease", dest="parse", help="parse")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Importing modules"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as Evaluator"
    
    classSets = {}
    evaluator = Evaluator()
    if evaluator.type == "binary":
        classSets["entity"] = IdSet(idDict={"True":1,"False":-1}, locked=True)
        classSets["interaction"] = IdSet(idDict={"True":1,"False":-1}, locked=True)
        negativeClassId = -1
    elif evaluator.type == "multiclass":
        classSets["entity"] = IdSet(idDict={"neg":1}, locked=False)
        classSets["interaction"] = IdSet(idDict={"neg":1}, locked=False)
        negativeClassId = 1
    
    # Load corpus and make sentence graphs
    goldCorpusElements = CorpusElements.loadCorpus(options.gold, options.parse, options.tokenization)
    predictedCorpusElements = CorpusElements.loadCorpus(options.input, options.parse, options.tokenization)    
    
    processCorpora(predictedCorpusElements, goldCorpusElements, options, classSets, negativeClassId)