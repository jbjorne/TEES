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

# for entities to match, they have to have the same head offsets and same type
def compareEntitiesSimple(e1,e2,tokens=None):
    if e1.get("headOffset") == e2.get("headOffset") and e1.get("type") == e2.get("type"):
        return True
    else:
        return False

# not used
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

# Produces a mapping that connects matching entities from prediction (from)
# to gold standard (to).
def mapEntities(entitiesFrom, entitiesTo, tokens, compareFunction=compareEntitiesSimple):
    entityMap = {}
    for entityFrom in entitiesFrom:
        entityMap[entityFrom] = []
        for entityTo in entitiesTo:
            if compareFunction(entityFrom, entityTo, tokens):
                entityMap[entityFrom].append(entityTo)
    return entityMap

# Splits merged types generated from overlapping entities/edges into their components
def getElementTypes(element):
    typeName = element.get("type")
    if typeName.find("---") != -1:
        return typeName.split("---")
    else:
        return [typeName]

# Uses the mapped entities to give predictions for a single sentence
def getEntityPredictions(entityMap, targetEntities, classSet, negativeClassId):
    predictions = []
    id = "Unknown.x0"
    for entityFrom, entitiesTo in entityMap.iteritems():
        if entityFrom.get("isName") == "True":
            continue
        found = False
        for entityTo in entitiesTo:
            predictions.append( ((id, classSet.getId(entityTo.get("type"))), classSet.getId(entityFrom.get("type")), None, None) )
            found = True # entitiesTo has at least one item
        if not found: # false positive prediction
            predictions.append( ((id, negativeClassId), classSet.getId(entityFrom.get("type")), None, None) )
    # mappedTargetEntities will contain all gold entities for which is mapped at least
    # one predicted entity. Those gold entities not in mappedTargetEntities are then
    # undetected ones, i.e. false negatives.
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

# Uses mapped entities and predicted and gold interactions to provide
# predictions for the interactions
def getInteractionPredictions(interactionsFrom, interactionsTo, entityMap, classSet, negativeClassId):
    predictions = []
    id = "Unknown.x0"
    fromEntityIdToElement = {}
    for key in entityMap.keys():
        entityId = key.get("id")
        assert not fromEntityIdToElement.has_key(entityId), entityId
        fromEntityIdToElement[entityId] = key
    
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

# Compares a prediction (from) to a gold (to) sentence
def processSentence(fromSentence, toSentence, target, classSets, negativeClassId):
    splitMerged(fromSentence) # modify element tree to split merged elements into multiple elements
    entitiesFrom = fromSentence.entities
    entitiesTo = toSentence.entities
    tokens = fromSentence.tokens
    # map predicted entities to gold entities
    entityMap = mapEntities(entitiesFrom, entitiesTo, tokens, compareFunction=compareEntitiesSimple)
    
    # get predictions for predicted edges/entities vs. gold edges/entities
    entityPredictions = []
    interactionPredictions = []
    if target == "entities" or target == "both":
        entityPredictions = getEntityPredictions(entityMap, entitiesTo, classSets["entity"], negativeClassId)
    if target == "interactions" or target == "both":
        interactionPredictions = getInteractionPredictions(fromSentence.interactions + fromSentence.pairs, toSentence.interactions + toSentence.pairs, entityMap, classSets["interaction"], negativeClassId)
    
    return entityPredictions, interactionPredictions

# Compares a prediction (from) to a gold (to) corpus
def processCorpora(EvaluatorClass, fromCorpus, toCorpus, target, classSets, negativeClassId):
    entityPredictions = []
    interactionPredictions = []
    counter = ProgressCounter(len(fromCorpus.sentences), "Corpus Processing")
    # Loop through the sentences and collect all predictions
    for i in range(len(fromCorpus.sentences)):
        counter.update(1,fromCorpus.sentences[i].sentence.get("id"))
        newEntityPredictions, newInteractionPredictions = processSentence(fromCorpus.sentences[i], toCorpus.sentences[i], target, classSets, negativeClassId)
        entityPredictions.extend(newEntityPredictions)
        interactionPredictions.extend(newInteractionPredictions)
    
    # Process the predictions with an evaluator and print the results
    if len(entityPredictions) > 0:
        evaluator = EvaluatorClass(entityPredictions, classSet=classSets["entity"])
        print evaluator.toStringConcise(title="Entities")    
    if len(interactionPredictions) > 0:
        evaluator = EvaluatorClass(interactionPredictions, classSet=classSets["interaction"])
        print evaluator.toStringConcise(title="Interactions")    

# Splits entities/edges with merged types into separate elements
def splitMerged(sentence):
    for sourceList in [sentence.entities, sentence.interactions, sentence.pairs]:
        for element in sourceList[:]:
            types = getElementTypes(element)
            if len(types) > 1:
                for type in types:
                    newElement = copy.copy(element)
                    newElement.set("type", type)
                    sourceList.append(newElement)
                sourceList.remove(element)

def run(EvaluatorClass, inputCorpusFile, goldCorpusFile, parse, tokenization, target="both"):
    print >> sys.stderr, "##### EvaluateInteractionXML #####"
    # Class sets are used to convert the types to ids that the evaluator can use
    classSets = {}
    evaluator = EvaluatorClass()
    if evaluator.type == "binary":
        classSets["entity"] = IdSet(idDict={"True":1,"False":-1}, locked=True)
        classSets["interaction"] = IdSet(idDict={"True":1,"False":-1}, locked=True)
        negativeClassId = -1
    elif evaluator.type == "multiclass":
        classSets["entity"] = IdSet(idDict={"neg":1}, locked=False)
        classSets["interaction"] = IdSet(idDict={"neg":1}, locked=False)
        negativeClassId = 1
    else:
        sys.exit("Unknown evaluator type")
    
    # Load corpus and make sentence graphs
    goldCorpusElements = CorpusElements.loadCorpus(goldCorpusFile, parse, tokenization, False)
    predictedCorpusElements = CorpusElements.loadCorpus(inputCorpusFile, parse, tokenization, False)    
    
    # Compare the corpora and print results on screen
    processCorpora(EvaluatorClass, predictedCorpusElements, goldCorpusElements, target, classSets, negativeClassId)
    
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
    optparser.add_option("-i", "--input", default=None, dest="input", help="Predictions in interaction XML", metavar="FILE")
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="Gold standard in interaction XML", metavar="FILE")
    #optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the statistics")
    optparser.add_option("-r", "--target", default="both", dest="target", help="edges/entities/both (default: both)")
    optparser.add_option("-e", "--evaluator", default="AveragingMultiClassEvaluator", dest="evaluator", help="Prediction evaluator class")
    optparser.add_option("-t", "--tokenization", default="split-Charniak-Lease", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-Charniak-Lease", dest="parse", help="parse")
    (options, args) = optparser.parse_args()

    # Load the selected evaluator class
    print >> sys.stderr, "Importing modules"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as Evaluator"
    
    run(Evaluator, options.input, options.gold, options.parse, options.tokenization, options.target)
