"""
For comparing a predicted interaction XML against a gold standard
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
#print os.path.dirname(os.path.abspath(__file__))+"/.."
from Utils.ProgressCounter import ProgressCounter
from optparse import OptionParser
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
import Utils.TableUtils as TableUtils
import Core.SentenceGraph as SentenceGraph
import copy
from collections import defaultdict

# for entities to match, they have to have the same head offsets and same type
def compareEntitiesSimple(e1,e2,tokens=None):
    #if not "headOffset" in e1:
    #    raise Exception("Entity " + str(e1.get("id")) + " has no 'headOffset' attribute")
    #if not "headOffset" in e2:
    #    raise Exception("Entity " + str(e2.get("id")) + " has no 'headOffset' attribute")
    if e1.get("headOffset") == e2.get("headOffset") and e1.get("type") == e2.get("type"):
        return True
    else:
        return False
    
def compareEntitiesStrict(e1,e2,tokens=None):
    # HORRIBLE HACK
    if e1.get("charOffset")[:-1] == e1.get("headOffset")[:-1]:
        e1.set("charOffset", e1.get("headOffset"))
    if e2.get("charOffset")[:-1] == e2.get("headOffset")[:-1]:
        e2.set("charOffset", e2.get("headOffset"))
        
        
        
    if e1.get("charOffset") == e2.get("charOffset") and e1.get("type") == e2.get("type"):
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
def mapEntities(entitiesFrom, entitiesTo, tokens=None, compareFunction=compareEntitiesSimple):
    entityMap = {}
    for entityFrom in entitiesFrom:
        entityMap[entityFrom] = []
        for entityTo in entitiesTo:
            if compareFunction(entityFrom, entityTo, tokens):
                entityMap[entityFrom].append(entityTo)
    return entityMap

## Splits merged types generated from overlapping entities/edges into their components
#def getElementTypes(element):
#    typeName = element.get("type")
#    if typeName.find("---") != -1:
#        return typeName.split("---")
#    else:
#        return [typeName]

def getEventPredictions(entityMap, allGoldEntities, interactionMap, classSet, negativeClassId):
    examples = []
    predictions = []
    id = "Unknown.x0"
    # analyze events
    for predictedEntity, goldEntities in entityMap.iteritems():
        if predictedEntity.get("given") == "True":
            continue
        found = False
        predictedEntityType = predictedEntity.get("type")
        for goldEntity in goldEntities:
            goldEntityType = goldEntity.get("type")
            if predictedEntityType != goldEntityType: # whatever the arguments, this is a false positive
                examples.append( [id, classSet.getId(goldEntity.get("type")), None, None] )
                predictions.append( [classSet.getId(predictedEntity.get("type"))] )
            else: # mapped entity types match, check the arguments
                if interactionMap[predictedEntity.get("id")]: # arguments are correct, this is a true positive
                    examples.append( [id, classSet.getId(goldEntity.get("type")), None, None] )
                    predictions.append( [classSet.getId(predictedEntity.get("type"))] )
                else: # an error in arguments, this is a false positive for the type of the entity
                    examples.append( [id, negativeClassId, None, None] )
                    predictions.append( [classSet.getId(predictedEntity.get("type"))] )
            found = True # entitiesTo has at least one item
        if not found: # false positive prediction due to entity span not being in gold
            examples.append( [id, negativeClassId, None, None] )
            predictions.append( [classSet.getId(predictedEntity.get("type"))] )
    # mappedTargetEntities will contain all gold entities for which is mapped at least
    # one predicted entity. Those gold entities not in mappedTargetEntities are then
    # undetected ones, i.e. false negatives.
    mappedTargetEntities = set()
    for eList in entityMap.values():
        for e in eList:
            mappedTargetEntities.add(e)
    for e in allGoldEntities:
        if e.get("given") == "True":
            continue
        if not e in mappedTargetEntities: # false negative gold
            examples.append( [id, classSet.getId(e.get("type")), None, None] )
            predictions.append( [negativeClassId] )
            #predictions.append( ((id, classSet.getId(e.get("type"))), negativeClassId, None, None) )
    assert len(examples) == len(predictions)
    return examples, predictions

# Uses the mapped entities to give predictions for a single sentence
def getEntityPredictions(entityMap, targetEntities, classSet, negativeClassId):
    examples = []
    predictions = []
    id = "Unknown.x0"
    for entityFrom, entitiesTo in entityMap.iteritems():
        if entityFrom.get("given") == "True":
            continue
        found = False
        for entityTo in entitiesTo:
            examples.append( [id, classSet.getId(entityTo.get("type")), None, None] )
            predictions.append( [classSet.getId(entityFrom.get("type"))] )
            #predictions.append( ((id, classSet.getId(entityTo.get("type"))), classSet.getId(entityFrom.get("type")), None, None) )
            found = True # entitiesTo has at least one item
        if not found: # false positive prediction
            examples.append( [id, negativeClassId, None, None] )
            predictions.append( [classSet.getId(entityFrom.get("type"))] )
            #predictions.append( ((id, negativeClassId), classSet.getId(entityFrom.get("type")), None, None) )
    # mappedTargetEntities will contain all gold entities for which is mapped at least
    # one predicted entity. Those gold entities not in mappedTargetEntities are then
    # undetected ones, i.e. false negatives.
    mappedTargetEntities = set()
    for eList in entityMap.values():
        for e in eList:
            mappedTargetEntities.add(e)
    for e in targetEntities:
        if e.get("given") == "True":
            continue
        if not e in mappedTargetEntities: # false negative gold
            examples.append( [id, classSet.getId(e.get("type")), None, None] )
            predictions.append( [negativeClassId] )
            #predictions.append( ((id, classSet.getId(e.get("type"))), negativeClassId, None, None) )
    assert len(examples) == len(predictions)
    return examples, predictions

# Uses mapped entities and predicted and gold interactions to provide
# predictions for the interactions
def getInteractionPredictions(interactionsFrom, interactionsTo, entityMap, classSet, negativeClassId):
    examples = []
    predictions = []
    id = "Unknown.x0"
    fromEntityIdToElement = {}
    for key in entityMap.keys():
        entityId = key.get("id")
        assert not fromEntityIdToElement.has_key(entityId), entityId
        fromEntityIdToElement[entityId] = key
    
    # Keep track of false positives caused by false positive entities
    falseEntity = defaultdict(lambda: defaultdict(int))
    
    toInteractionsWithPredictions = set()
    events = {}
    for predictedEntity in entityMap.keys():
        events[predictedEntity.get("id")] = True # mark all events as positive (if no arguments, gold or predicted, remains positive)
    for interactionFrom in interactionsFrom:
        goldE1Ids = []
        goldE2Ids = []
        if interactionFrom.get("e1") not in fromEntityIdToElement or interactionFrom.get("e2") not in fromEntityIdToElement:
            print >> sys.stderr, "Warning, interaction", interactionFrom.get("id"), [interactionFrom.get("e1"), interactionFrom.get("e2")], "links to a non-existing entity"
        else:
            # Select gold entities for entity-ids referred to in the predicted interaction
            for goldEntity in entityMap[fromEntityIdToElement[interactionFrom.get("e1")]]:
                goldE1Ids.append(goldEntity.get("id"))
            for goldEntity in entityMap[fromEntityIdToElement[interactionFrom.get("e2")]]:
                goldE2Ids.append(goldEntity.get("id"))
        
        if len(goldE1Ids) == 0 or len(goldE2Ids) == 0:
            falseEntity[interactionFrom.get("type")][0] += 1
        
        found = False
        # Go through all gold interactions
        for interactionTo in interactionsTo:
            if interactionTo.get("e1") in goldE1Ids and interactionTo.get("e2") in goldE2Ids: # this gold interaction matches the predicted one
                toInteractionsWithPredictions.add(interactionTo)
                examples.append( [id, classSet.getId(interactionTo.get("type")),None,None] )
                predictions.append( [classSet.getId(interactionFrom.get("type"))] )
                found = True
        if not found: # false positive prediction
            examples.append( [id,negativeClassId,None,None] )
            predictions.append( [classSet.getId(interactionFrom.get("type"))] )
            events[interactionFrom.get("e1")] = False # false positive argument -> incorrect event
    # Get ids of gold entities that had a correct prediction
    reverseEntityMap = {}
    for predictedEntity, goldEntities in entityMap.iteritems():
        for goldEntity in goldEntities:
            #assert goldEntity.get("id") not in reverseEntityMap, (predictedEntity.get("id"), [x.get("id") for x in goldEntities])
            # One gold entity can map to more than one predicted entities,
            # due to predicted entities created by splitting a prediction
            if goldEntity.get("id") not in reverseEntityMap:
                reverseEntityMap[goldEntity.get("id")] = []
            reverseEntityMap[goldEntity.get("id")].append(predictedEntity.get("id"))
    mappedGoldEntities = reverseEntityMap.keys()
    # Process gold interactions that did not have a prediction
    for interactionTo in interactionsTo:
        if interactionTo not in toInteractionsWithPredictions: # false negative gold
            examples.append( [id, classSet.getId(interactionTo.get("type")), None, None] )
            predictions.append( [negativeClassId] )
            #predictions.append( ((id, classSet.getId(interactionTo.get("type"))), negativeClassId, None, None) )
            if interactionTo.get("e1") not in mappedGoldEntities or interactionTo.get("e2") not in mappedGoldEntities:
                falseEntity[interactionTo.get("type")][1] += 1
            if interactionTo.get("e1") in reverseEntityMap: # mark an event false due to a missing gold interaction
                for predictedEntityId in reverseEntityMap[interactionTo.get("e1")]:
                    events[predictedEntityId] = False # missing argument -> incorrect event
    assert len(examples) == len(predictions)
    return examples, predictions, falseEntity, events

# Compares a prediction (from) to a gold (to) sentence
def processDocument(fromDocumentSentences, toDocumentSentences, target, classSets, negativeClassId, entityMatchFunction):
    #splitMerged(fromSentence) # modify element tree to split merged elements into multiple elements
    if toDocumentSentences != None:
        assert len(fromDocumentSentences) == len(toDocumentSentences)
    else:
        toDocumentSentences = [None] * len(fromDocumentSentences)
    entityMap = {}
    allToEntities = []
    for fromSentence, toSentence in zip(fromDocumentSentences, toDocumentSentences):
        if toSentence != None:
            assert fromSentence.sentence.get("id") == toSentence.sentence.get("id")
        entitiesFrom = []
        for e in fromSentence.entities:
            if e.get("type") != "neg":
                entitiesFrom.append(e)
        entitiesTo = []
        if toSentence != None:
            entitiesTo = toSentence.entities
            allToEntities.extend(entitiesTo)
        tokens = fromSentence.tokens
        # map predicted entities to gold entities
        sentenceEntityMap = mapEntities(entitiesFrom, entitiesTo, tokens, compareFunction=entityMatchFunction)
        for entity in sentenceEntityMap.keys():
            assert entity not in entityMap
            entityMap[entity] = sentenceEntityMap[entity]
    
    # select interactions
    fromInteractions = []
    for fromSentence in fromDocumentSentences:
        for interaction in fromSentence.interactions + fromSentence.pairs:
            if interaction.get("type") != "neg":
                fromInteractions.append(interaction)
    toInteractions = []
    for toSentence in toDocumentSentences:
        if toSentence != None:
            toInteractions.extend(toSentence.interactions)
            toInteractions.extend(toSentence.pairs)

    # get predictions for predicted edges/entities vs. gold edges/entities
    entityPredictions = []
    interactionPredictions = []
    falseEntity = defaultdict(lambda: defaultdict(int))
    if target == "entities" or target == "both":
        entityExamples, entityPredictions = getEntityPredictions(entityMap, allToEntities, classSets["entity"], negativeClassId)
    if target == "interactions" or target == "both":
        interactionExamples, interactionPredictions, sentFalseEntity, interactionMap = getInteractionPredictions(fromInteractions, toInteractions, entityMap, classSets["interaction"], negativeClassId)
        for k,v in sentFalseEntity.iteritems():
            falseEntity[k][0] += v[0]
            falseEntity[k][1] += v[1]
    if target == "events" or target == "both":
        eventExamples, eventPredictions = getEventPredictions(entityMap, allToEntities, interactionMap, classSets["entity"], negativeClassId)
        
    return (entityExamples, entityPredictions), (interactionExamples, interactionPredictions), (eventExamples, eventPredictions), falseEntity

# Compares a prediction (from) to a gold (to) corpus
def processCorpora(EvaluatorClass, fromCorpus, toCorpus, target, classSets, negativeClassId, entityMatchFunction, errorMatrix=False):
    entityExamples = []
    entityPredictions = []
    interactionExamples = []
    interactionPredictions = []
    eventExamples = []
    eventPredictions = []
    falseEntity = defaultdict(lambda: defaultdict(int))
    counter = ProgressCounter(len(fromCorpus.sentences), "Corpus Processing")
    # Loop through the sentences and collect all predictions
    toCorpusSentences = None
    if toCorpus != None:
        toCorpusSentences = toCorpus.documentSentences
    for i in range(len(fromCorpus.documentSentences)):
        if len(fromCorpus.documentSentences[i]) > 0:
            counter.update(len(fromCorpus.documentSentences[i]), fromCorpus.documentSentences[i][0].sentence.get("id").rsplit(".", 1)[0])
        if toCorpusSentences != None:
            newEntityExPred, newInteractionExPred, newEventExPred, sentFalseEntity = processDocument(fromCorpus.documentSentences[i], toCorpusSentences[i], target, classSets, negativeClassId, entityMatchFunction)
        else:
            newEntityExPred, newInteractionExPred, newEventExPred, sentFalseEntity = processDocument(fromCorpus.documentSentences[i], None, target, classSets, negativeClassId, entityMatchFunction)
        entityExamples.extend(newEntityExPred[0])
        entityPredictions.extend(newEntityExPred[1])
        interactionExamples.extend(newInteractionExPred[0])
        interactionPredictions.extend(newInteractionExPred[1])
        eventExamples.extend(newEventExPred[0])
        eventPredictions.extend(newEventExPred[1])
        for k,v in sentFalseEntity.iteritems():
            falseEntity[k][0] += v[0]
            falseEntity[k][1] += v[1]
    
    # Process the predictions with an evaluator and print the results
    evaluator = None
    if len(entityPredictions) > 0:
        evaluator = EvaluatorClass(entityExamples, entityPredictions, classSet=classSets["entity"])
        print evaluator.toStringConcise(title="Entities")
        if errorMatrix:
            print evaluator.matrixToString()
            print evaluator.matrixToString(True)
    if len(interactionPredictions) > 0:
        evaluator = EvaluatorClass(interactionExamples, interactionPredictions, classSet=classSets["interaction"])
        print evaluator.toStringConcise(title="Interactions")
        if errorMatrix:
            print evaluator.matrixToString()
            print evaluator.matrixToString(True)
        #print "Interactions (fp ent->fp int, fn-ent->fn-int )"
        #for key in sorted(falseEntity.keys()):
        #    print "", key, falseEntity[key][0], "/", falseEntity[key][1]
    if len(eventPredictions) > 0:
        evaluator = EvaluatorClass(eventExamples, eventPredictions, classSet=classSets["entity"])
        print evaluator.toStringConcise(title="Events")
        if errorMatrix:
            print evaluator.matrixToString()
            print evaluator.matrixToString(True)
    return evaluator

## Splits entities/edges with merged types into separate elements
#def splitMerged(sentence):
#    for sourceList in [sentence.entities, sentence.interactions, sentence.pairs]:
#        for element in sourceList[:]:
#            types = getElementTypes(element)
#            if len(types) > 1:
#                for type in types:
#                    newElement = copy.copy(element)
#                    newElement.set("type", type)
#                    sourceList.append(newElement)
#                sourceList.remove(element)

def run(EvaluatorClass, inputCorpusFile, goldCorpusFile, parse, tokenization=None, target="both", entityMatchFunction=compareEntitiesSimple, removeIntersentenceInteractions=False, errorMatrix=False):
    print >> sys.stderr, "##### EvaluateInteractionXML #####"
    print >> sys.stderr, "Comparing input", inputCorpusFile, "to gold", goldCorpusFile
    # Class sets are used to convert the types to ids that the evaluator can use
    classSets = {}
    if EvaluatorClass.type == "binary":
        classSets["entity"] = IdSet(idDict={"True":1,"False":-1}, locked=True)
        classSets["interaction"] = IdSet(idDict={"True":1,"False":-1}, locked=True)
        negativeClassId = -1
    elif EvaluatorClass.type == "multiclass":
        classSets["entity"] = IdSet(idDict={"neg":1}, locked=False)
        classSets["interaction"] = IdSet(idDict={"neg":1}, locked=False)
        negativeClassId = 1
    else:
        sys.exit("Unknown evaluator type")
    
    # Load corpus and make sentence graphs
    goldCorpusElements = None
    if goldCorpusFile != None:
        goldCorpusElements = SentenceGraph.loadCorpus(goldCorpusFile, parse, tokenization, False, removeIntersentenceInteractions)
    predictedCorpusElements = SentenceGraph.loadCorpus(inputCorpusFile, parse, tokenization, False, removeIntersentenceInteractions)    
    
    # Compare the corpora and print results on screen
    return processCorpora(EvaluatorClass, predictedCorpusElements, goldCorpusElements, target, classSets, negativeClassId, entityMatchFunction, errorMatrix=errorMatrix)
    
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
#    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="parse")
    optparser.add_option("-m", "--matching", default="SIMPLE", dest="matching", help="matching function")
    optparser.add_option("--no_intersentence", default=False, action="store_true", dest="no_intersentence", help="Exclude intersentence interactions from evaluation")
    optparser.add_option("--error_matrix", default=False, action="store_true", dest="error_matrix", help="Show error matrix")
    (options, args) = optparser.parse_args()
    
    assert options.matching in ["SIMPLE", "STRICT"]
    if options.matching == "SIMPLE":
        entityMatchFunction = compareEntitiesSimple
    elif options.matching == "STRICT":
        entityMatchFunction = compareEntitiesStrict
    
    # Load the selected evaluator class
    print >> sys.stderr, "Importing modules"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as Evaluator"
    
    run(Evaluator, options.input, options.gold, options.parse, None, options.target, entityMatchFunction=entityMatchFunction, removeIntersentenceInteractions=options.no_intersentence, errorMatrix=options.error_matrix)
