from optparse import OptionParser
try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import cElementTree as ElementTree
import gzip
import sys
import os
import re
import string
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.ElementTreeUtils as ETUtils
from Utils.ProgressCounter import ProgressCounter

# the prefix to use for split token ids
tokenIdPrefix = "bt_"

# the default name of the new tokenization
splitTokenizationName = "split"

# the default name of the new parse
newParseName = "split_parse"

# the special dependency types to connect split tokens with
splitHyphenDepName  = "hyphen"
splitSlashDepName   = "slash"
splitParensDepName  = "appos"
splitDefaultDepName = "dep"

# returns a cElementTree element corresponding to a new tokenization
# in the given sentence element.
def addTokenization(tokenization, sentence, sentenceId):
    toks = sentence.find("sentenceanalyses/tokenizations")
    if toks == None:
        toks = sentence.find("analyses")
    assert toks != None, "Missing <tokenizations> in sentence %s" % sentenceId

#    # assume new-style if there's at least one <tokenization> with
#    # a "tokenizer" attribute. Also check duplicates.
#    isNew = False
    for t in toks.getiterator("tokenization"):
        if t.get("tokenizer") is not None:
            assert t.get("tokenizer") is not None, "Split tokenization '%s' already exists in sentence %s!" % (tokenization, sentenceId)
#            isNew = True

    # add the tokenization.
#    if isNew:
    newTok = ElementTree.SubElement(toks, "tokenization")
    newTok.attrib["tokenizer"] = tokenization
#    else:
#        assert toks.find(tokenization) is None, "Split tokenization '%s' already exists in sentence %s!" % (tokenization, sentenceId)
#        newTok = ElementTree.SubElement(toks, tokenization)

    return newTok

# returns a cElementTree element corresponding to the given tokenization
# in the given sentence element.
def getTokenization(tokenization, sentence, sentenceId, remove=False):
    analyses = sentence.find("analyses")
    if analyses == None:
        return None
    for t in analyses.findall("tokenization"):
        if t.get("tokenizer") == tokenization:
            if remove:
                analyses.remove(t)
            return t
    return None

# returns a cElementTree element corresponding to a new parse in the
# given sentence element.
def addParse(parse, tokenization, sentence, sentenceId):
    for p in sentence.getiterator("parse"):
        if p.get("parser") is not None:
            assert p.get("parser") != parse, "New parse '%s' already exists in sentence %s!" % (parse, sentenceId)

    newParse = ElementTree.SubElement(sentence.find("analyses"), "parse")
    newParse.attrib["parser"] = parse
    newParse.attrib["tokenizer"] = tokenization
    return newParse
        
# returns a cElementTree element correspoding to the given parse
# in the given sentence element. Also checks that the parse is created
# for the given tokenization.
def getParse(parse, tokenization, sentence, sentenceId, remove=False):
    # first try old-style format, then new.
    parsePath = "sentenceanalyses/parses/"+parse
    found = sentence.find(parsePath)

    if found is not None:
        return found

    # then try new-style
    parses = sentence.find("sentenceanalyses/parses")
    if parses == None:
        parses = sentence.find("analyses")
    assert parses is not None, "ERROR: missing parses for sentence %s" % sentenceId

    for p in parses.getiterator("parse"):
        if p.get("parser") == parse:
            assert p.get("tokenizer") == tokenization, "ERROR: tokenization/parse mismatch: parse %s has tokenizer %s, not %s" % (parse, p.get("tokenizer"), tokenization)
            if remove:
                parses.remove(p)
            return p
            
    return None

# represents a token in the analysis XML.
class Token:
    def __init__(self, id, origId, pos, charOffset, text):
        self.id         = id
        self.origId     = origId
        self.pos        = pos
        self.charOffset = charOffset
        self.text       = text
        self.splitFromOffset = None

        # these oddities are used in re-connecting split tokens
        self.head = None
        self.depType = None

    def isPunct(self):
        return [t for t in self.text if t not in string.punctuation] == []

# given token start and end offsets and a list of (start,end) spans
# of entities, returns a list of the points at which the token would
# need to be "cut" to give parts that divide cleanly into entities.
def cutPoints(tokStart, tokEnd, entityOffsets):
    cutPoints = set()

    for start, end in entityOffsets:
        if start > tokStart and start <= tokEnd:
            # must be cut at the start of the entity
            cutPoints.add(start)

        if end >= tokStart and end < tokEnd:
            # must be cut after the end of the entity
            cutPoints.add(end+1)

    # "postprocess" the proposed cuts to remove all instances where a
    # cut would break an entity. This is to protect against e.g.
    # "H2A" in "H2A and 2B" from being cut (rather meaninglessly) into
    # "H" and "2A" to match annotated entities "H2A" and "H2B".
    for cut in cutPoints.copy():
        for start, end in entityOffsets:
            if cut > start and cut <= end:
                try:
                    cutPoints.remove(cut)
                except KeyError:
                    print >> sys.stderr, "!"

    return sorted(list(cutPoints))


# heuristically determines which of the given parts of what was originally
# a single token should be considered the "head" of the split token parts.
# Sets Token.head and Token.depType.
def resolveHeads(splitParts, logFile=None):
    # if there's only one part, there's nothing to resolve
    if len(splitParts) < 2:
        return

    # since tokens may be split at multiple places for various
    # reasons, start by first marking "head" locally, determining
    # for each split which of the tokens is the head. This will
    # then be further resolved transitively.
    for i, tok in enumerate(splitParts):
        # may need to refer to these
        prevTok = None
        if i-1 >= 0:
            prevTok = splitParts[i-1]
        nextTok = None
        if i+1 < len(splitParts):
            nextTok = splitParts[i+1]
        nextNextTok = None
        if i+2 < len(splitParts):
            nextNextTok = splitParts[i+2]

        # ignore all-punctuation tokens
        if tok.isPunct():
            continue

        # not a good idea --- these may resolve other heads in turn.
#         # ignore tokens for which the head has been already
#         # determined
#         if tok.head is not None:
#             assert tok.depType is not None
#             continue

        # if the next token is a hyphen or slash (etc.) and the next one
        # is not punctuation, we can resolve this bit..
        if (nextTok is not None and nextTok.text in ["-", "/", "("] and
            nextNextTok is not None and not nextNextTok.isPunct()):
            # for the hyphen case, the latter non-punct token is
            # the head
            if nextTok.text == "-":
                tok.head    = nextNextTok
                tok.depType = splitHyphenDepName

            # for slashes, the preceding token is assumed the head
            elif nextTok.text == "/":
                nextNextTok.head = tok
                nextNextTok.depType = splitSlashDepName

            # same for parens
            elif nextTok.text == "(":
                nextNextTok.head = tok
                nextNextTok.depType = splitParensDepName

    # if all but one non-punctuation token have a head, all is OK
    headLess = []
    for tok in splitParts:
        if tok.isPunct():
            continue
        if tok.head is None:
            headLess.append(tok)
    joinedText = " ".join([t.text for t in splitParts])
    if len(headLess) == 0:
        if logFile != None:
            logFile.write("NOTE: no head candidates for " + joinedText + "\n")
    if len(headLess) > 1:
        if logFile != None:
            logFile.write("NOTE: failed to resolve unique \"head\" for " + joinedText + ": " + " ".join([t.text for t in headLess]) + "\n")
        # assume the first candidate is the head, connect the other there.
        for h in headLess[1:]:
            h.head    = headLess[0]
            h.depType = splitDefaultDepName


# splits the <token>s in the given tokenization, attempting to split them
# so that each entity has its own token. Returns a list of Token objects
# representing the new split ones.
def splitTokens(tokenization, sentence, logFile=None):
    # store the tokens for the new split tokenization here
    sentenceId = sentence.get("id")
    if sentence.get("origId") != None:
        sentenceId += "/" + sentence.get("origId")
    splitTokens = []

    # get the character offsets of entities, and turn them into a list
    # of (from,to) tuples.
    entityOffsets = []
    for entity in sentence.getiterator("entity"):
        if entity.get("given") != None and entity.get("given") == "False":
            continue
        offsets = entity.get("charOffset")
        assert offsets is not None, "Missing charOffset!"
        # format is "NUM-NUM(,NUM-NUM)+". split by commas, parse ranges
        for offset in offsets.split(","):
            m = re.match(r'^(\d+)-(\d+)$', offset)
            assert m, "Failed to parse charOffset '%s'" % offset
            #start, end = int(m.group(1)), int(m.group(2))
            start, end = int(m.group(1)), int(m.group(2)) - 1
            entityOffsets.append((start,end))
    
    seqId = 0#1
    nextId = "%s%d" % (tokenIdPrefix, seqId)

    for token in tokenization.getiterator("token"):

        text   = token.get("text")
        origId = token.get("id")
        POS    = token.get("POS")
        off    = token.get("charOffset")

        # parse the token offset
        m = re.match(r'^(\d+)-(\d+)$', off)
        assert m, "Failed to parse token charOffset '%s'" % off
        #tokStart, tokEnd = int(m.group(1)), int(m.group(2))
        tokStart, tokEnd = int(m.group(1)), int(m.group(2)) - 1

        # determine points at which the token must be cut
        cuts = cutPoints(tokStart, tokEnd, entityOffsets)

        # go through the cuts, possibly adding more to further break e.g.
        # "actin" "-binding" into "actin" "-" "binding".
        newCuts = set(cuts)
        for cut in cuts:
            cutOffset = cut - tokStart
            firstPart, lastPart = text[:cutOffset], text[cutOffset:]

            # extra cut immediately after cut followed by hyphen,
            # slash etc. that precedes a non-punctuation character.
            if (lastPart[0] in ["-", "/"]  and
                len(lastPart) >= 2 and lastPart[1] not in string.punctuation):
                newCuts.add(cut+1)

            # same in reverse (sort of).
            if (firstPart[-1] in ["-", "/"] and
                len(firstPart) >= 2 and firstPart[-2] not in string.punctuation):
                newCuts.add(cut-1)

        cuts = sorted(list(newCuts))

        parts = []
        startOffset = 0
        for cut in cuts:
            cutOffset = cut - tokStart
            parts.append(text[startOffset:cutOffset])
            startOffset = cutOffset
        parts.append(text[startOffset:])

        if len(parts) > 1:
            # debug
            if logFile != None:
                logFile.write("Token %s in sentence %s: cut '%s' into %d parts:" % (origId, sentenceId, text, len(parts)) + " ".join(["'%s'" % p for p in parts]) + "\n")
                #print >> sys.stderr, "Token %s in sentence %s: cut '%s' into %d parts:" % (origId, sentenceId, text, len(parts)), " ".join(["'%s'" % p for p in parts])
            pass

        # sanity check
        assert text == "".join(parts), "INTERNAL ERROR: token parts don't add up to original!"


        # create a token for each part. For now, don't assign the
        # "head"; this will be determined later.
        currentOffset = tokStart
        splitParts = []
        for part in parts:
            #tOff = "%d-%d" % (currentOffset, currentOffset + len(part)-1)
            tOff = "%d-%d" % (currentOffset, currentOffset + len(part))

            t = Token(nextId, origId, POS, tOff, part)
            t.splitFromOffset = off
            splitParts.append(t)
            splitTokens.append(t)

            currentOffset += len(part)
            seqId += 1
            nextId = "%s%d" % (tokenIdPrefix, seqId)


        resolveHeads(splitParts, logFile)

    return splitTokens

# writes the given Tokens as <token>s into the given ElementTree element.
def addTokensToTree(tokens, element):
    for t in tokens:
        newToken = ElementTree.SubElement(element, "token")
        newToken.set("id", t.id)
        newToken.set("text", t.text)
        newToken.set("POS", t.pos)
        newToken.set("charOffset", t.charOffset)
        if t.splitFromOffset != None and t.splitFromOffset != t.charOffset:
            newToken.set("splitFrom", t.splitFromOffset)

#def indent(elem, level=0):
#    """Stolen from Antti's code stolen from Jari's code"""
#    i = "\n" + level*"  "
#    if len(elem):
#        if not elem.text or not elem.text.strip():
#            elem.text = i + "  "
#        for e in elem:
#            indent(e, level+1)
#        if not e.tail or not e.tail.strip():
#            e.tail = i
#    if level and (not elem.tail or not elem.tail.strip()):
#        elem.tail = i

def mainFunc(input, output=None, parseName="McCC", tokenizationName=None, newParseName=None, newTokenizationName=None, logFileName=None, removeOld=True):
    print >> sys.stderr, "Protein Name Splitter"
    if logFileName != None:
        print >> sys.stderr, "Writing log to", logFileName
        logFile = open(logFileName, "wt")
    else:
        logFile = None
    #if input.endswith(".gz"):
    #    inFile = gzip.GzipFile(input)
    #else:
    #    inFile = open(input)
    tree = ETUtils.ETFromObj(input)
    
    if tokenizationName == None:
        tokenizationName = parseName

    #tree = ElementTree.parse(inFile)
    root = tree.getroot()
    
    sentences = [x for x in root.getiterator("sentence")]
    counter = ProgressCounter(len(sentences), "Split Protein Names")
    counter.showMilliseconds = True
    missingTokCount = 0
    for sentence in sentences:
        sId = sentence.get("id")
        counter.update(1, "Splitting names ("+sId+"): ")

        tok   = getTokenization(tokenizationName, sentence, sId, remove=removeOld)
        if tok == None:
            missingTokCount += 1
            continue
        
        assert tok is not None, "Missing tokenization '%s' in sentence %s!" % (tokenizationName, sId)

        parse = getParse(parseName, tokenizationName, sentence, sId, remove=removeOld)
        assert parse is not None, "Missing parse '%s' in sentence %s!" % (parseName, sId)

        split = splitTokens(tok, sentence, logFile)
        
        # Default names
        if removeOld:
            if newTokenizationName == None:
                newTokenizationName = tok.get("tokenizer")
            if newParseName == None:
                newParseName = parse.get("parser")
        else:
            if newTokenizationName == None:
                newTokenizationName = "split-" + tok.get("tokenizer")
            if newParseName == None:
                newParseName = "split-" + parse.get("parser")

        # add a new tokenization with the split tokens.
        splittok = addTokenization(newTokenizationName, sentence, sId)
        addTokensToTree(split, splittok)
        for a in tok.attrib:
            if splittok.get(a) == None:
                splittok.set(a, tok.get(a))
        #splittok.set("split-")

        # make a mapping from original to split token ids. Store the
        # head token when given.
        tokenIdMap = {}
        for t in split:
            if t.head:
                head = t.head
                # traverse
                while head.head is not None:
                    assert head.head != t, "Cyclic heads"
                    head = head.head

                # should match (nah, punctuation problems)
                # assert t.origId not in tokenIdMap or tokenIdMap[t.origId] == head.id, "Head conflict"
                tokenIdMap[t.origId] = head.id
            else:
                # only allow overwrite of existing entry if the current token
                # is not punctuation.
                if t.origId not in tokenIdMap or not t.isPunct():
                    tokenIdMap[t.origId] = t.id

        # make a copy of the specified parse that refers to the split tokens
        # instead of the originals.
        newparse = addParse(newParseName, newTokenizationName, sentence, sId)
        for a in parse.attrib:
            if newparse.get(a) == None:
                newparse.set(a, parse.get(a))
        newparse.set("ProteinNameSplitter", "True")
        splittok.set("ProteinNameSplitter", "True")
        
        depSeqId = 0 #1
        for d in parse.getiterator("dependency"):
            t1, t2, dType = d.get("t1"), d.get("t2"), d.get("type")
            assert t1 in tokenIdMap and t2 in tokenIdMap, "INTERNAL ERROR"

            dep = ElementTree.SubElement(newparse, "dependency")
            dep.set("t1", tokenIdMap[t1])
            dep.set("t2", tokenIdMap[t2])
            dep.set("type", dType)
            dep.set("id", "sd_%d" % depSeqId)
            depSeqId += 1

        # Add in new dependencies between the split parts.
        for t in [tok for tok in split if tok.head is not None]:
            dep = ElementTree.SubElement(newparse, "dependency")
            dep.set("t1", t.head.id)
            dep.set("t2", t.id)
            dep.set("type", t.depType)
            dep.set("split", "PNS")
            dep.set("id", "spd_%d" % depSeqId)
            depSeqId += 1

        for phrase in parse.getiterator("phrase"):
            newparse.append(phrase)

            # debugging
            #print >> sys.stderr, "NEW DEP IN", sId
    
    print >> sys.stderr, "Tokenization missing from", missingTokCount, "sentences"

    #indent(root)
    if logFile != None:
        logFile.close()

    # debugging
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(tree, output)
    return tree
    #else:
    #    tree.write(options.output)

if __name__=="__main__":
    optParser = OptionParser(usage="%prog [OPTIONS]\nModifies one parse and associated tokenization to split (some) hyphenated\nwords, e.g. \"actin-binding\".")
    optParser.add_option("-f", "--analysisFile", dest="file", metavar="FILE", default=None, help = "Path to the xml-formatted analysis file")
    optParser.add_option("-o", "--output", dest="output", metavar="FILE", default=None, help = "Path to the xml-formatted analysis file")
    optParser.add_option("-p", "--parse", dest="parse", default = None, help = "Name of the parse to modify")
    optParser.add_option("-t", "--tokenization", dest="tokenization", default=None, help="Name of the tokenization to modify")
    optParser.add_option("-s", "--splittokenization", dest="splittokenization", default=splitTokenizationName, help="Name of the new split tokenization to create")
    optParser.add_option("-n", "--newparse", dest="newparse", default=newParseName, help="Name of the new parse to create")
    optParser.add_option("-l", "--logFile", dest="logFileName", default=None, help="Log for the splitter messages")
    (options, args) = optParser.parse_args()
    
    if (options.file is None or options.parse is None or
        options.tokenization is None):
        print >> sys.stderr, "The -f, -p and -t options are mandatory."
        optParser.print_help()
        sys.exit(1)

    mainFunc(options.file, options.output, options.parse, options.tokenization, options.splittokenization, options.newparse, options.logFileName)
