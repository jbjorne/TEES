import sys, os
from collections import defaultdict
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
#IF LOCAL
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source"
#ENDIF
sys.path.append(extraPath)
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import Range

def getPhrases(parse):
    phrases = parse.findall("phrase")
    toKeep = []
    for phrase in phrases:
        if phrase.get("charOffset") == None:
            continue
        toKeep.append(phrase)
    return toKeep

def makePhrase(type, offset, begin, end):
    e = ET.Element("phrase")
    e.set("type", type)
    e.set("begin", str(begin))
    e.set("end", str(end))
    e.set("charOffset", str(offset[0])+"-"+str(offset[1]))
    return e

def makePhrases(parse, tokenization):
    phrases = getPhrases(parse)
    phraseDict = {}
    
    # Define offsets
    for phrase in phrases:
        phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
        if not phraseDict.has_key(phraseOffset):
            phraseDict[phraseOffset] = []
        phraseDict[phraseOffset].append(phrase)
    
    tokens = tokenization.findall("token")
    for phrase in phrases[:]:
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
                    phrases.append(newPhrase)
                    phraseDict[newPhraseOffset] = [newPhrase]
            prevToken = token
            tokCount += 1
    # DET-phrases
    for phrase in phrases[:]:
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
                phrases.append(newPhrase)
                phraseDict[newPhraseOffset] = [newPhrase]
    # Token-phrases
    for i in range(len(tokens)):
        token = tokens[i]
        tokPOS = token.get("POS")
        if tokPOS in ["PRP$", "IN", "WP$"]:
            tokOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
            if not phraseDict.has_key(tokOffset):
                newPhrase = makePhrase("TOK-" + tokPOS, tokOffset, i, i)
                phraseDict[tokOffset] = [newPhrase]

    return phraseDict
    #phraseOffsets = phraseDict.keys()

def processCorpus(input, parserName):
    print >> sys.stderr, "Loading corpus file", input
    corpusRoot = ETUtils.ETFromObj(input).getroot()
    documents = corpusRoot.findall("document")

    counts = defaultdict(int)
    matchByType = defaultdict(lambda : [0,0])
    filteredMatchByType = defaultdict(lambda : [0,0])
    filter = set(["NP", "TOK-IN", "WHADVP", "WHNP", "TOK-WP$", "TOK-PRP$", "NP-IN"])
    
    # fix spans
    for document in documents:
        for sentence in document.findall("sentence"):
            sentOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            for entity in sentence.findall("entity"):
                altOffsetString = entity.get("altOffset")
                if altOffsetString == None:
                    continue
                #print altOffsetString
                altOffsets = Range.charOffsetToTuples(altOffsetString)
                assert len(altOffsets) == 1
                for i in range(len(altOffsets)):
                    altOffset = altOffsets[i] 
                    altOffsets[i] = (altOffset[0] - sentOffset[0], altOffset[1] - sentOffset[0])
                entity.set("altOffset", Range.tuplesToCharOffset(altOffsets))
    
    #counter = ProgressCounter(len(documents), "Documents")
    for document in documents:
        for sentence in document.findall("sentence"):
            parse = ETUtils.getElementByAttrib(sentence.find("sentenceanalyses"), "parse", {"parser":parserName})
            if parse == None:
                continue
            tokenization = ETUtils.getElementByAttrib(sentence.find("sentenceanalyses"), "tokenization", {"tokenizer":parse.get("tokenizer")})
            phraseDict = makePhrases(parse, tokenization)
            phraseOffsets = phraseDict.keys()
            #phraseOffsets.sort()
            
            for value in phraseDict.values():
                counts["phrases"] += len(value)
                for phrase in value:
                    matchByType[phrase.get("type")][0] += 1
                    if phrase.get("type") in filter:
                        filteredMatchByType[phrase.get("type")][0] += 1
                        counts["phrases-filtered"] += 1
            counts["tokens"] += len(tokenization.findall("token"))
            
            for entity in sentence.findall("entity"):
                if entity.get("isName") == "True":
                    continue
                counts["entity"] += 1
                print "entity", entity.get("id")
                print ETUtils.toStr(entity)
                maxOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
                minOffset = entity.get("altOffset")
                if minOffset != None:
                    minOffset = Range.charOffsetToSingleTuple(minOffset)
                else:
                    minOffset = maxOffset
                count = 0
                filteredCount = 0
                for phraseOffset in phraseOffsets:
                    if Range.contains(maxOffset, phraseOffset) and Range.contains(phraseOffset, minOffset):
                        for phrase in phraseDict[phraseOffset]:
                            print "  match", count, ETUtils.toStr(phrase)
                            count += 1
                            matchByType[phrase.get("type")][1] += 1
                            if phrase.get("type") in filter:
                                filteredCount += 1
                                filteredMatchByType[phrase.get("type")][1] += 1
                if count == 0:
                    print "  NO MATCH", ETUtils.toStr(entity)
                    counts["no-match"] += 1
                else:
                    counts["match"] += 1
                
                if filteredCount == 0: counts["no-match-filtered"] += 1
                else: counts["match-filtered"] += 1
    print "Match", matchByType
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
