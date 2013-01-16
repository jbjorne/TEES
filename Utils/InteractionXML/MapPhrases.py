import sys, os
from collections import defaultdict
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
sys.path.append(extraPath)
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range

def fixIndices(phrases, tokens):
    fixCount = 0
    phraseCount = 0
    for phrase in phrases:
        fixed = False
        phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
        phraseBegin = int(phrase.get("begin"))
        phraseEnd = int(phrase.get("end"))
        for i in range(len(tokens)):
            token = tokens[i]
            tokOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
            if tokOffset[0] == phraseOffset[0]:
                if phraseBegin != i:
                    phrase.set("begin", str(i))
                    fixed = True
            if tokOffset[1] == phraseOffset[1]:
                if phraseEnd != i:
                    phrase.set("end", str(i))
                    fixed = True
                break
        if fixed:
            fixCount += 1
        phraseCount += 1
    #print fixCount, phraseCount

def getPhrases(parse, tokens, filter=None):
    phrases = parse.findall("phrase")
    toKeep = []
    for phrase in phrases:
        if phrase.get("charOffset") == None:
            continue
        if filter != None and phrase.get("type") not in filter:
            continue
        toKeep.append(phrase)
    fixIndices(toKeep, tokens)
    return toKeep

def removeNamedEntityPhrases(entities, phrases, phraseDict):
    neOffsets = set()
    for entity in entities:
        if entity.get("given") != "True":
            continue
        neOffsets.add(entity.get("charOffset"))
    phrasesToKeep = []
    for phrase in phrases:
        phraseOffset = phrase.get("charOffset")
        if phraseOffset in neOffsets:
            phraseOffsetTuple = Range.charOffsetToSingleTuple(phraseOffset)
            if phraseOffsetTuple in phraseDict:
                del phraseDict[phraseOffsetTuple]
        else:
            phrasesToKeep.append(phrase)
    #print >> sys.stderr, "Removed", len(phrases) - len(phrasesToKeep), "named entity phrases"
    return phrasesToKeep

def getPhraseDict(phrases):
    phraseDict = {}   
    # Define offsets
    for phrase in phrases:
        phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
        if not phraseDict.has_key(phraseOffset):
            phraseDict[phraseOffset] = []
        phraseDict[phraseOffset].append(phrase)
    return phraseDict

def getPhraseTypeCounts(phrases):
    counts = {}
    for phrase in phrases:
        pType = phrase.get("type")
        if pType not in counts:
            counts[pType] = 0
        counts[pType] += 1
    return counts

def makePhrase(type, offset, begin, end):
    e = ET.Element("phrase")
    e.set("type", type)
    e.set("begin", str(begin))
    e.set("end", str(end))
    e.set("charOffset", str(offset[0])+"-"+str(offset[1]))
    return e

def makeINSubPhrases(phrases, tokens, phraseDict, filter=None):
    newPhrases = []
    for phrase in phrases:
        if filter != None and phrase.get("type") not in filter:
            continue
        phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
        phraseBegin = int(phrase.get("begin"))
        phraseEnd = int(phrase.get("end"))
        prevToken = None
        tokCount = 0
        for token in tokens[phraseBegin:phraseEnd+1]:
            if token.get("POS") == "IN" and prevToken != None:
                newPhraseOffset = (phraseOffset[0], Range.charOffsetToSingleTuple(prevToken.get("charOffset"))[-1])
                newPhrase = makePhrase(phrase.get("type") + "-IN",
                          newPhraseOffset, 
                          phraseBegin, 
                          phraseBegin + tokCount-1)
                if not phraseDict.has_key(newPhraseOffset):
                    #print "NEW PHRASE:", ETUtils.toStr(newPhrase)
                    newPhrases.append(newPhrase)
                    phraseDict[newPhraseOffset] = [newPhrase]
            prevToken = token
            tokCount += 1
    return newPhrases

def makeDETSubPhrases(phrases, tokens, phraseDict, filter=None):
    newPhrases = []
    for phrase in phrases:
        if filter != None and phrase.get("type") not in filter:
            continue
        phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
        phraseBegin = int(phrase.get("begin"))
        phraseEnd = int(phrase.get("end"))
        if phraseBegin > 0 and tokens[phraseBegin-1].get("POS") == "DT":
            newPhraseOffset = (Range.charOffsetToSingleTuple(tokens[phraseBegin-1].get("charOffset"))[0], phraseOffset[1])
            newPhrase = makePhrase("DT-" + phrase.get("type"),
                      newPhraseOffset, 
                      phraseBegin - 1, 
                      phraseEnd)
            if not phraseDict.has_key(newPhraseOffset):
                #print "NEW PHRASE:", ETUtils.toStr(newPhrase)
                newPhrases.append(newPhrase)
                phraseDict[newPhraseOffset] = [newPhrase]
    return newPhrases

def makeTokenSubPhrases(tokens, phraseDict, includePOS=["PRP$", "IN", "WP$"]):
    newPhrases = []
    for i in range(len(tokens)):
        token = tokens[i]
        tokPOS = token.get("POS")
        if tokPOS in includePOS:
            tokOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
            if not phraseDict.has_key(tokOffset):
                newPhrase = makePhrase("TOK-t" + tokPOS, tokOffset, i, i)
                newPhrases.append(newPhrase)
                phraseDict[tokOffset] = [newPhrase]
    return newPhrases

def makePhrases(parse, tokenization, entities=None):
    tokens = tokenization.findall("token")
    phrases = getPhrases(parse, tokens)
    phraseDict = getPhraseDict(phrases)    
    
    # IN-phrases
    phrases.extend(makeINSubPhrases(phrases, tokens, phraseDict))
    # DET-phrases
    phrases.extend(makeDETSubPhrases(phrases, tokens, phraseDict))
    # Token-phrases
    phrases.extend(makeTokenSubPhrases(tokens, phraseDict))
    
    # Remove phrases matching named entity offsets
    #if entities != None:
    #    phrases = removeNamedEntityPhrases(entities, phrases, phraseDict)
    
    return phrases, phraseDict
    #phraseOffsets = phraseDict.keys()

def getMatchingPhrases(entity, phraseOffsets, phraseDict):
    matches = []
    if entity.get("isName") == "True":
        return []
    maxOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
    minOffset = entity.get("altOffset")
    if minOffset != None:
        minOffset = Range.charOffsetToSingleTuple(minOffset)
    else:
        minOffset = maxOffset
    for phraseOffset in phraseOffsets:
        if Range.contains(maxOffset, phraseOffset) and Range.contains(phraseOffset, minOffset):
            matches.extend(phraseDict[phraseOffset])
    return matches

def selectBestMatch(entity, phrases):
    entOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
    if entity.get("altOffset") != None:
        entOffset = Range.charOffsetToSingleTuple(entity.get("altOffset"))
    best = (sys.maxint, None)
    for phrase in phrases:
        matchValue = Range.mismatch(entOffset, Range.charOffsetToSingleTuple(phrase.get("charOffset")))
        if best[0] > matchValue:
            best = (matchValue, phrase)
    return best[1]

def getPhraseEntityMapping(entities, phraseDict):
    phraseOffsets = phraseDict.keys()
    phraseToEntity = {}
    for entity in entities:
        if entity.get("given") == "True":
            continue
        matches = getMatchingPhrases(entity, phraseOffsets, phraseDict)
        if len(matches) == 1:
            bestMatch = matches[0]
        elif len(matches) == 0:
            bestMatch = None
        else:
            bestMatch = selectBestMatch(entity, matches)
        if bestMatch != None:
            if not phraseToEntity.has_key(bestMatch):
                phraseToEntity[bestMatch] = []
            phraseToEntity[bestMatch].append(entity)
    return phraseToEntity

def getNECounts(phrases, entities):
    counts = {}
    for phrase in phrases:
        phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
        counts[phrase] = 0
        for entity in entities:
            if entity.get("given") != "True": # only check names
                continue
            if Range.contains(phraseOffset, Range.charOffsetToSingleTuple(entity.get("charOffset"))):
                counts[phrase] += 1
    return counts

def processCorpus(input, parserName):
    print >> sys.stderr, "Loading corpus file", input
    corpusRoot = ETUtils.ETFromObj(input).getroot()
    documents = corpusRoot.findall("document")

    counts = defaultdict(int)
    matchByType = defaultdict(lambda : [0,0])
    filteredMatchByType = defaultdict(lambda : [0,0])
    filter = set(["NP", "TOK-tIN", "WHADVP", "WHNP", "TOK-tWP$", "TOK-tPRP$", "NP-IN"])
    
#    # fix spans
#    for document in documents:
#        for sentence in document.findall("sentence"):
#            sentOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
#            for entity in sentence.findall("entity"):
#                altOffsetString = entity.get("altOffset")
#                if altOffsetString == None:
#                    continue
#                #print altOffsetString
#                altOffsets = Range.charOffsetToTuples(altOffsetString)
#                assert len(altOffsets) == 1
#                for i in range(len(altOffsets)):
#                    altOffset = altOffsets[i] 
#                    altOffsets[i] = (altOffset[0] - sentOffset[0], altOffset[1] - sentOffset[0])
#                entity.set("altOffset", Range.tuplesToCharOffset(altOffsets))
    
    #counter = ProgressCounter(len(documents), "Documents")
    for document in documents:
        for sentence in document.findall("sentence"):
            entities = sentence.findall("entity")
            parse = ETUtils.getElementByAttrib(sentence.find("sentenceanalyses"), "parse", {"parser":parserName})
            if parse == None:
                continue
            tokenization = ETUtils.getElementByAttrib(sentence.find("sentenceanalyses"), "tokenization", {"tokenizer":parse.get("tokenizer")})
            phrases, phraseDict = makePhrases(parse, tokenization, entities)
            phraseOffsets = phraseDict.keys()
            #phraseOffsets.sort()
            phraseNECounts = getNECounts(phrases, entities)
            
            for value in phraseDict.values():
                counts["phrases"] += len(value)
                for phrase in value:
                    matchByType[phrase.get("type")][0] += 1
                    if phrase.get("type") in filter:
                        filteredMatchByType[phrase.get("type")][0] += 1
                        counts["phrases-filtered"] += 1
                    if phrase.get("type").find("NP") != -1:
                        matchByType[phrase.get("type")+"_NE"+str(phraseNECounts[phrase])][0] += 1
            counts["tokens"] += len(tokenization.findall("token"))
            
            corefType = {}
            for interaction in sentence.findall("interaction"):
                if interaction.get("type") == "Coref":
                    corefType[interaction.get("e1")] = "Anaphora"
                    corefType[interaction.get("e2")] = "Antecedent"
            
            for entity in entities:
                if entity.get("given") == "True":
                    continue
                counts["entity"] += 1
                print "entity", entity.get("id")
                print ETUtils.toStr(entity)
                matches = getMatchingPhrases(entity, phraseOffsets, phraseDict)
                count = 0
                filteredCount = 0
                for phrase in matches:
                    cType = "UNKNOWN"
                    if corefType.has_key(entity.get("id")):
                        cType = corefType[entity.get("id")]
                    print "  match", count, ETUtils.toStr(phrase), "NE" + str(phraseNECounts[phrase]), "ctype:" + cType, "ent:" + ETUtils.toStr(entity)
                    count += 1
                    matchByType[phrase.get("type")][1] += 1
                    matchByType[phrase.get("type")+"_"+cType][1] += 1
                    matchByType[phrase.get("type")+"_"+cType+"_NE"+str(phraseNECounts[phrase])][1] += 1
                    if phrase.get("type") in filter:
                        filteredCount += 1
                        filteredMatchByType[phrase.get("type")][1] += 1
                # Matching
                if count == 0:
                    print "  NO MATCH", ETUtils.toStr(entity)
                    counts["no-match"] += 1
                else:
                    counts["match"] += 1
                # Multimatching
                if len(matches) > 1:
                    bestMatch = selectBestMatch(entity, matches)
                    print "  MULTIMATCH("+ entity.get("charOffset")+","+str(entity.get("altOffset")) + ")", ", ".join([x.get("type") + "_" + x.get("charOffset") for x in matches]), "SEL(" + bestMatch.get("type") + "_" + bestMatch.get("charOffset") + ")"
                # Filtered matching
                if filteredCount == 0: counts["no-match-filtered"] += 1
                else: counts["match-filtered"] += 1
    print "Match"
    for key in sorted(matchByType.keys()):
        print "  ", key, " ", matchByType[key]
    print "Filtered", filteredMatchByType
    print "Counts", counts

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Split elements with merged types #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-p", "--parser", default="split-McClosky", dest="parser", help="")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)

    processCorpus(options.input, options.parser)
