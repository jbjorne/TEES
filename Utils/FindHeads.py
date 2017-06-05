import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import ElementTreeUtils as ETUtils
from collections import defaultdict
import Core.SentenceGraph as SentenceGraph
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import Utils.Range as Range
import re

def getEntities(sentence):
    return sentence.findall("entity") + [x for x in sentence.iter("span")]

def getEntityTokens(entity, tokens):
    entityTokens = []
    for entityOffset in Range.charOffsetToTuples(entity.get("charOffset")):
        for token in tokens:
            if Range.overlap(entityOffset, Range.charOffsetToSingleTuple(token.get("charOffset"))):
                entityTokens.append(token)
    return entityTokens

def getSentenceTokens(sentence, parseName, counts=None):
    parse = IXMLUtils.getParseElement(sentence, parseName, False, False)
    tokens = []
    if parse:
        if counts: counts["parses"] += 1
        tokenization = IXMLUtils.getTokenizationElement(sentence, parse.get("tokenizer"), False, False)
        if tokenization != None:
            if counts: counts["tokenizations"] += 1
            tokens = tokenization.findall("token")
    return tokens

def findHeads(input, parseName, tokenizationName=None, output=None, removeExisting=True, iterate=False):   
    print >> sys.stderr, "Removing existing head offsets"
    counts = defaultdict(int)
    tokenCounts = {}
    xml = ETUtils.ETFromObj(input)
    for document in xml.getroot().findall("document"):
        counts["documents"] += 1
        for sentence in document.findall("sentence"):
            counts["sentences"] += 1
            tokens = getSentenceTokens(sentence, parseName, counts)
            for entity in getEntities(sentence):
                counts["entities"] += 1
                if entity.get("headOffset") != None:
                    counts["existing-heads"] += 1
                    if removeExisting:
                        counts["removed-heads"] += 1
                        del entity.attrib["headOffset"]
                candidates = getEntityTokens(entity, tokens)
                if entity.get("headOffset") == None:
                    if len(candidates) == 0:
                        entity.set("headOffset", entity.get("charOffset"))
                        counts["head-defined"] += 1
                        counts["head-notokens"] += 1
                    elif len(candidates) == 1:
                        entity.set("headOffset", candidates[0].get("charOffset"))
                        counts["head-defined"] += 1
                        counts["head-unique"] += 1
                entityType = entity.get("type")
                for candidate in candidates:
                    tokenText = candidate.get("text")
                    if tokenText not in tokenCounts:
                        tokenCounts[tokenText] = {}
                    if entityType not in tokenCounts[tokenText]:
                        tokenCounts[tokenText][entityType] = 0
                    tokenCounts[tokenText][entityType] += 1
    if removeExisting:
        print >> sys.stderr, "Removed head offsets from", counts["removed-heads"], "out of", counts["existing-heads"], "entities with existing head offset"
    
    if counts["head-defined"] != counts["entities"]:
        print >> sys.stderr, "Determining head offsets by token ranking"
        for document in xml.getroot().findall("document"):
            for sentence in document.findall("sentence"):
                tokens = getSentenceTokens(sentence, parseName)
                for entity in getEntities(sentence):
                    if entity.get("headOffset") != None: # head offset is already defined
                        continue
                    candidates = getEntityTokens(entity, tokens)
                    candidates = [{"token":x, "text":x.get("text"), "scores":[], "offset":Range.charOffsetToSingleTuple(x.get("charOffset"))} for x in candidates]
                    candidates.sort(key=lambda k: k['offset']) # sort by token linear order
                    entityType = entity.get("type")
                    for c in candidates:
                        c["scores"].append(tokenCounts[c["token"]["text"]][entityType])
                    for candidate in candidates:
                        hasLetters = re.search('[a-zA-Z]', c["token"]["text"]) != None
                        hasDigits = re.search('[0-9]', c["token"]["text"]) != None
                        if hasLetters:
                            c["scores"].append(2) # prefer tokens with letters
                        elif hasDigits:
                            c["scores"].append(1) # prefer digits over special characters
                        else:
                            c["scores"].append(0)
                    for i in range(len(candidates)):
                        c = candidates[i]
                        c["scores"].append(i) # prefer the rightmost token in the linear order
                    candidates.sort(reverse=True, key=lambda k: k['scores']) # sort by hierarchical scores
                    entity.set("headOffset", candidates[0]["token"].get("charOffset"))
                    for index, comparison in ((0, "frequency"), (1, "alpha"), (2, "linear")): 
                        if candidates[0]["scores"][index] > candidates[1]["scores"][index]:
                            break
                    counts["head-" + comparison] += 1
                    counts["head-defined"] += 1
                    entity.set("headScores", ";".join([x["text"] + ":" + ",".join(x["scores"]) for x in candidates]))
    
    # SentenceGraph automatically calculates head offsets and adds them to entities if they are missing
    if counts["head-defined"] != counts["entities"]:
        print >> sys.stderr, "Determining head offsets using parse", parseName, "and tokenization", tokenizationName
        corpusElements = SentenceGraph.loadCorpus(xml, parseName, tokenizationName) 
        # Make sure every parse gets head scores
        for sentence in corpusElements.sentences:
            if sentence.sentenceGraph == None:
                continue
            if sentence.sentenceGraph.tokenHeadScores == None:
                sentence.sentenceGraph.getTokenHeadScores()
    
    print >> sys.stderr, "Counts", dict(counts)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusElements.rootElement, output)
    return xml

# def findHeads(input, parse, tokenization=None, output=None, removeExisting=True, iterate=False):
#     if iterate:
#         from Utils.ProgressCounter import ProgressCounter
#         import InteractionXML.SentenceElements as SentenceElements
#         print >> sys.stderr, "Determining head offsets using parse", parse, "and tokenization", tokenization
#         print >> sys.stderr, "Removing existing head offsets"
#         removeCount = 0
#         counter = ProgressCounter(None, "Find heads")
#         counter.showMilliseconds = True
#         for sentences in SentenceElements.getCorpusIterator(input, output, parse, tokenization):
#             for sentence in sentences:
#                 if removeExisting:
#                     for e in getEntities(sentence.sentence):
#                         if e.get("headOffset") != None:
#                             removeCount += 1
#                             del e.attrib["headOffset"]
#                 graph = SentenceGraph.SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
#                 graph.mapInteractions(sentence.entities, sentence.interactions)
#                 # Make sure every parse gets head scores
#                 #if graph.tokenHeadScores == None:
#                 #    graph.getTokenHeadScores()
#             counter.update(len(sentences), "Finding heads ("+sentences[-1].sentence.get("id")+"): ")                
#         print >> sys.stderr, "Removed head offsets from", removeCount, "entities"    
#     else:
#         xml = ETUtils.ETFromObj(input)
#         if removeExisting:
#             print >> sys.stderr, "Removing existing head offsets"
#             removeCount = 0
#             xml = ETUtils.ETFromObj(input)
#             for d in xml.getroot().findall("document"):
#                 for s in d.findall("sentence"):
#                     for e in getEntities(s):
#                         if e.get("headOffset") != None:
#                             removeCount += 1
#                             del e.attrib["headOffset"]
#             print >> sys.stderr, "Removed head offsets from", removeCount, "entities"
#         
#         # SentenceGraph automatically calculates head offsets and adds them to entities if they are missing
#         print >> sys.stderr, "Determining head offsets using parse", parse, "and tokenization", tokenization
#         corpusElements = SentenceGraph.loadCorpus(xml, parse, tokenization)
#         
#         # Make sure every parse gets head scores
#         for sentence in corpusElements.sentences:
#             if sentence.sentenceGraph == None:
#                 continue
#             if sentence.sentenceGraph.tokenHeadScores == None:
#                 sentence.sentenceGraph.getTokenHeadScores()
#         
#         if output != None:
#             print >> sys.stderr, "Writing output to", output
#             ETUtils.write(corpusElements.rootElement, output)
#         return xml
    
if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Calculating entity head token offsets #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nRecalculate head token offsets.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse element name for calculating head offsets")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization element name for calculating head offsets")
    optparser.add_option("-r", "--iterate", default=False, action="store_true", dest="iterate", help="")
    (options, args) = optparser.parse_args()
    
    findHeads(input=options.input, output=options.output, parse=options.parse, tokenization=options.tokenization, iterate=options.iterate)
    
