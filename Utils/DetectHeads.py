import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Core.SentenceGraph as SentenceGraph
from Utils.ProgressCounter import ProgressCounter
from FindHeads import findHeads
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.CorpusElements
import Utils.Range as Range
import Utils.Libraries.PorterStemmer as PorterStemmer

def getTriggers(corpus):
    """
    Returns a dictionary of "entity type"->"entity text"->"count"
    """
    corpus = ETUtils.ETFromObj(corpus)
    trigDict = {}
    for entity in corpus.getroot().getiterator("entity"):
        if entity.get("given") == "True":
            continue
        eType = entity.get("type")
        if not trigDict.has_key(eType):
            trigDict[eType] = {}
        eText = entity.get("text")
        eText = PorterStemmer.stem(eText)
        if not trigDict[eType].has_key(eText):
            trigDict[eType][eText] = 0
        trigDict[eType][eText] += 1
    return trigDict

def getDistribution(trigDict):
    """
    Converts a dictionary of "entity type"->"entity text"->"count"
    to "entity text"->"entity type"->"(count, fraction)"
    """
    distDict = {}
    eTypes = trigDict.keys()
    for eType in trigDict.keys():
        for string in trigDict[eType].keys():
            if not distDict.has_key(string):
                distDict[string] = {}
                for e in eTypes:
                    distDict[string][e] = [0, None]
            distDict[string][eType] = [trigDict[eType][string], None]
    # define ratios
    for string in distDict.keys():
        count = 0.0
        for eType in distDict[string].keys():
            count += distDict[string][eType][0]
        for eType in distDict[string].keys():
            distDict[string][eType][1] = distDict[string][eType][0] / count
    return distDict

def getHeads(corpus):
    corpus = ETUtils.ETFromObj(corpus)
    headDict = {}
    headDict["None"] = {}
    for sentence in corpus.getiterator("sentence"):
        headOffsetStrings = set()
        for entity in sentence.findall("entity"):
            eType = entity.get("type")
            if not headDict.has_key(eType):
                headDict[eType] = {}
            eText = entity.get("text")
            headOffset = entity.get("headOffset")
            headOffsetStrings.add(headOffset)
            headOffset = Range.charOffsetToSingleTuple(headOffset)
            charOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
            if headOffset == charOffset:
                if not headDict[eType].has_key(eText): headDict[eType][eText] = 0
                headDict[eType][eText] += 1
            else:
                headText = sentenceText[headOffset[0]-charOffset[0]:headOffset[1]-charOffset[0]+1]
                if not headDict[eType].has_key(headText): headDict[eType][headText] = 0
                headDict[eType][headText] += 1
        for token in tokens:
            if not token.get("charOffset") in headOffsetStrings: # token is not the head of any entity
                headText = token.get("text")
                if not headDict["None"].has_key(headText): headDict["None"][headText] = 0
                headDict["None"][headText] += 1
                
    return headDict

def getOverlap():
    pass

def removeHeads(corpus):
    print >> sys.stderr, "Removing existing head offsets"
    removeCount = 0
    xml = ETUtils.ETFromObj(corpus)
    for d in xml.getroot().findall("document"):
        for s in d.findall("sentence"):
            for e in s.findall("entity"):
                if e.get("headOffset") != None:
                    removeCount += 1
                    del e.attrib["headOffset"]
    print >> sys.stderr, "Removed head offsets from", removeCount, "entities"
    return [0, removeCount]

def findHeads(corpus, stringsFrom, methods, parse, tokenization):
    for m in methods:
        assert m in ["REMOVE", "SYNTAX", "DICT"]
    corpus = ETUtils.ETFromObj(corpus)
    counts = {}
    for method in methods:
        print >> sys.stderr, method, "pass"
        if method == "REMOVE":
            counts[method] = removeHeads(corpus)
        elif method == "DICT":
            counts[method] = findHeadsDictionary(corpus, stringsFrom, parse, tokenization)
        elif method == "SYNTAX":
            counts[method] = findHeadsSyntactic(corpus, parse, tokenization)
        print >> sys.stderr, method, "pass added", counts[method][0], "and removed", counts[method][1], "heads"
        
    print >> sys.stderr, "Summary (pass/added/removed):"
    for method in methods:
        print >> sys.stderr, " ", method, "/", counts[method][0], "/", counts[method][1]
    
def mapSplits(splits, string, stringOffset):
    """
    Maps substrings to a string, and stems them
    """
    begin = 0
    tuples = []
    for split in splits:
        offset = string.find(split, begin)
        assert offset != -1
        tuples.append( (split, PorterStemmer.stem(split), (offset,len(split))) )
        begin = offset + len(split)
    return tuples

def findHeadsDictionary(corpus, stringsFrom, parse, tokenization):
    print "Extracting triggers from", stringsFrom
    trigDict = getTriggers(stringsFrom)
    print "Determining trigger distribution"
    distDict = getDistribution(trigDict)
    allStrings = sorted(distDict.keys())
    print "Determining heads for", corpus
    corpusElements = Utils.InteractionXML.CorpusElements.loadCorpus(corpus, parse, tokenization, removeIntersentenceInteractions=False, removeNameInfo=False)
    cases = {}
    counts = [0,0]
    for sentence in corpusElements.sentences:
        #print sentence.sentence.get("id")
        sText = sentence.sentence.get("text")
        #tokenHeadScores = None
        for entity in sentence.entities:
            if entity.get("headOffset") != None:
                continue
            if entity.get("given") == "True": # Only for triggers
                continue
            #if tokenHeadScores == None:
            #    tokenHeadScores = getTokenHeadScores(sentence.tokens, sentence.dependencies, sentenceId=sentence.sentence.get("id"))
            eText = entity.get("text")
            eType = entity.get("type")
            eOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
            wsSplits = eText.split() # Split by whitespace
            if len(wsSplits) == 1 and eText.find("-") == -1: # unambiguous head will be assigned by SYNTAX pass
                continue
            else: # Entity text has multiple (whitespace or hyphen separated) parts
                candidates = []
                # Try to find entity substring in individual entity strings
                for wsTuple in mapSplits(wsSplits, eText, eOffset):
                    if not distDict.has_key(wsTuple[1]): # string not found, low score
                        candidates.append( ((-1, -1), wsTuple[2], wsTuple[0], wsTuple[1]) )
                    else: # String found, more common ones get higher score
                        assert distDict[wsTuple[1]].has_key(eType), (distDict[wsTuple[0]], wsTuple[0], eText)
                        candidates.append( (tuple(distDict[wsTuple[1]][eType]), wsTuple[2], wsTuple[0], wsTuple[1]) )
                # Split each whitespace-separated string further into hyphen-separated substrings
                for candidate in candidates[:]:
                    hyphenSplits = candidate[2].split("-")
                    if len(hyphenSplits) > 1: # Substring has a hyphen
                        # Try to find entity substring in individual entity strings
                        for hyphenTuple in mapSplits(hyphenSplits, eText, candidate[1]):
                            if not distDict.has_key(hyphenTuple[1]):
                                candidates.append( ((-1, -1), hyphenTuple[2], hyphenTuple[0], hyphenTuple[1]) )
                            else:
                                candidates.append( (tuple(distDict[hyphenTuple[1]][eType]), hyphenTuple[2], hyphenTuple[0], hyphenTuple[1]) )
            # Sort candidates, highes scores come first
            candidates.sort(reverse=True)
            # If not matches, look for substrings inside words
            if candidates[0][0][0] in [-1, 0]: # no matches, look for substrings
                print "Substring matching", candidates, "for entity", entity.get("id")
                for i in range(len(candidates)):
                    candidate = candidates[i]
                    cText = candidate[2]
                    for string in allStrings:
                        subStringPos = cText.find(string)
                        if subStringPos != -1:
                            print "  Substring match", string, cText,
                            score = tuple(distDict[string][eType])
                            if score > candidate[0]:
                                print score, candidate[0], "Substring selected" #, score > candidate[0], score < candidate[0]
                                subStringCoords = [candidate[1][0] + subStringPos, len(string)]
                                candidate = (score, subStringCoords, candidate[2], ">"+string+"<")
                            else:
                                print score, candidate[0]
                    candidates[i] = candidate
                # Resort after possibly replacing some candidates
                candidates.sort(reverse=True)
            if candidates[0][0][0] not in [-1, 0]: # if it is in [-1, 0], let SYNTAX pass take care of it
                candidateOffset = (candidates[0][1][0] + eOffset[0], candidates[0][1][0] + candidates[0][1][1] + eOffset[0]) 
                entity.set("headOffset", str(candidateOffset[0]) + "-" + str(candidateOffset[1]-1))
                entity.set("headMethod", "Dict")
                entity.set("headString", sText[candidateOffset[0]:candidateOffset[1]])
                counts[0] += 1
            # Prepare results for printing
            for i in range(len(candidates)):
                c = candidates[i]
                candidates[i] = (tuple(c[0]), c[2], c[3])
            case = (eType, eText, tuple(candidates))
            if not cases.has_key(case):
                cases[case] = 0
            cases[case] += 1
            print entity.get("id"), eType + ": '" + eText + "'", candidates    
            #headToken = getEntityHeadToken(entity, sentence.tokens, tokenHeadScores)
            # The ElementTree entity-element is modified by setting the headOffset attribute
            #entity.set("headOffset", headToken.get("charOffset"))
            #entity.set("headMethod", "Syntax")
    print "Cases"
    for case in sorted(cases.keys()):
        print case, cases[case]
    #return corpus
    return counts

def findHeadsSyntactic(corpus, parse, tokenization):
    """
    Determine the head token for a named entity or trigger. The head token is the token closest
    to the root for the subtree of the dependency parse spanned by the text of the element.
    
    @param entityElement: a semantic node (trigger or named entity)
    @type entityElement: cElementTree.Element
    @param verbose: Print selected head tokens on screen
    @param verbose: boolean
    """
    counts = [0,0]
    sentences = [x for x in corpus.getiterator("sentence")]
    counter = ProgressCounter(len(sentences), "SYNTAX")
    for sentence in sentences:
        counter.update()
        tokElement = ETUtils.getElementByAttrib(sentence, "sentenceanalyses/tokenizations/tokenization", {"tokenizer":tokenization})
        parseElement = ETUtils.getElementByAttrib(sentence, "sentenceanalyses/parses/parse", {"parser":parse})
        if tokElement == None or parseElement == None:
            print >> sys.stderr, "Warning, sentence", sentence.get("id"), "missing parse or tokenization" 
        tokens = tokElement.findall("token")
        tokenHeadScores = getTokenHeadScores(tokens, parseElement.findall("dependency"), sentenceId=sentence.get("id"))
        for entity in sentence.findall("entity"):
            if entity.get("headOffset") == None:
                headToken = getEntityHeadToken(entity, tokens, tokenHeadScores)
                # The ElementTree entity-element is modified by setting the headOffset attribute
                entity.set("headOffset", headToken.get("charOffset"))
                entity.set("headMethod", "Syntax")
                entity.set("headString", headToken.get("text"))
                counts[0] += 1
    return counts
        
def getEntityHeadToken(entity, tokens, tokenHeadScores):
    if entity.get("headOffset") != None:
        charOffsets = Range.charOffsetToTuples(entity.get("headOffset"))
    elif entity.get("charOffset") != "":
        charOffsets = Range.charOffsetToTuples(entity.get("charOffset"))
    else:
        charOffsets = []
    # Each entity can consist of multiple syntactic tokens, covered by its
    # charOffset-range. One of these must be chosen as the head token.
    headTokens = [] # potential head tokens
    for token in tokens:
        tokenOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
        for offset in charOffsets:
            if Range.overlap(offset, tokenOffset):
                headTokens.append(token)
    if len(headTokens)==1: # An unambiguous head token was found
        selectedHeadToken = headTokens[0]
    else: # One head token must be chosen from the candidates
        selectedHeadToken = findHeadToken(headTokens, tokenHeadScores)
        #if verbose:
        #    print >> sys.stderr, "Selected head:", token.attrib["id"], token.attrib["text"]
    assert selectedHeadToken != None, entityElement.get("id")
    return selectedHeadToken

def findHeadToken(candidateTokens, tokenHeadScores):
    """
    Select the candidate token that is closest to the root of the subtree of the depencdeny parse
    to which the candidate tokens belong to. See getTokenHeadScores method for the algorithm.
    
    @param candidateTokens: the list of syntactic tokens from which the head token is selected
    @type candidateTokens: list of cElementTree.Element objects
    """
    if len(candidateTokens) == 0:
        return None
    
    highestScore = -9999999
    bestTokens = []
    for token in candidateTokens:
        if tokenHeadScores[token] > highestScore:
            highestScore = tokenHeadScores[token]
    for token in candidateTokens:
        if tokenHeadScores[token] == highestScore:
            bestTokens.append(token)
    return bestTokens[-1]

def getTokenHeadScores(tokens, dependencies, sentenceId=None):
    """
    A head token is chosen using a heuristic that prefers tokens closer to the
    root of the dependency parse. In a list of candidate tokens, the one with
    the highest score is the head token. The return value of this method
    is a dictionary that maps token elements to their scores.
    """
    tokenHeadScores = {}
    
    # Give all tokens initial scores
    for token in tokens:
        tokenHeadScores[token] = 0 # initialize score as zero (unconnected token)
        for dependency in dependencies:
            if dependency.get("t1") == token.get("id") or dependency.get("t2") == token.get("id"):
                tokenHeadScores[token] = 1 # token is connected by a dependency
                break               
    
    # Give a low score for tokens that clearly can't be head and are probably produced by hyphen-splitter
    for token in tokens:
        tokenText = token.get("text")
        if tokenText == "\\" or tokenText == "/" or tokenText == "-":
            tokenHeadScores[token] = -1
    
    # Loop over all dependencies and increase the scores of all governor tokens
    # until each governor token has a higher score than its dependent token.
    # Some dependencies might form a loop so a list is used to define those
    # dependency types used in determining head scores.
    depTypesToInclude = ["prep", "nn", "det", "hyphen", "num", "amod", "nmod", "appos", "measure", "dep", "partmod"]
    #depTypesToRemoveReverse = ["A/AN"]
    modifiedScores = True
    loopCount = 0 # loopcount for devel set approx. 2-4
    while modifiedScores == True: # loop until the scores no longer change
        if loopCount > 20: # survive loops
            print >> sys.stderr, "Warning, possible loop in parse for sentence", sentenceId
            break
        modifiedScores = False
        for token1 in tokens:
            for token2 in tokens: # for each combination of tokens...
                for dep in dependencies: # ... check each dependency
                    if dep.get("t1") == token1.get("id") and dep.get("t2") == token2.get("id") and (dep.get("type") in depTypesToInclude):
                        # The governor token of the dependency must have a higher score
                        # than the dependent token.
                        if tokenHeadScores[token1] <= tokenHeadScores[token2]:
                            tokenHeadScores[token1] = tokenHeadScores[token2] + 1
                            modifiedScores = True
        loopCount += 1
    return tokenHeadScores

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
    optparser.add_option("-d", "--dictionary", default=None, dest="dictionary", help="Corpus file to use as dictionary of entity strings.")
    optparser.add_option("-m", "--methods", default=None, dest="methods", help="")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse element name for calculating head offsets")
    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization element name for calculating head offsets")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Loading corpus"
    corpus = ETUtils.ETFromObj(options.input)
    print >> sys.stderr, "Finding heads"
    findHeads(corpus, options.dictionary, ["REMOVE", "DICT", "SYNTAX"], options.parse, options.tokenization)
    #findHeadsDictionary(corpus, options.parse, options.tokenization)
    if options.output != None:
        print >> sys.stderr, "Writing corpus"
        ETUtils.write(corpus, options.output)