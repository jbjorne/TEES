import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
from collections import defaultdict
import ExampleBuilders.PhraseTriggerExampleBuilder 

def tokenize(text):
    tokens = [""]
    inText = False
    for c in text:
        if c.isspace():
            if inText:
                tokens.append(c)
                inText = False
            else:
                tokens[-1] += c
        else: # text
            if inText:
                tokens[-1] += c
            else:
                tokens.append(c)
                inText = True
    if tokens[0] == "" and len(tokens) > 1:
        return tokens[1:]
    else:
        return tokens

def isExtraWord(token, toLower=True, relPos = None):
    if token[-1] == ".":
        token = token[:-1]
    if toLower:
        token = token.lower()
    
    if token in ["heliothrix", "caldicellulosiruptor"]:
        return True
    
    if token == "genus":
        return True
    if token == "bacterium":
        return True
    if token == "bacteria":
        return True
    elif token == "strain":
        return True
    elif token == "organisms":
        return True
    elif token == "fetus":
        return True
    elif token == "venerealis":
        return True
    elif token == "subsp":
        return True
    elif token == "subspecies":
        return True
    elif token == "ssp":
        return True
    elif token == "-like":
        return True
    elif token == "sp":
        return True
    #elif token == "species":
    #    return True
    elif token == "serotope":
        return True
    elif token == "psjn":
        return True
    #elif token == "phylum":
    #    return True
    return False

def isBacteriaToken(token, bacteriaTokens, relPos):
    while len(token) > 0 and not token[0].isalnum():
        token = token[1:]
    if relPos > 0:
        while len(token) > 0 and token[-1] == ")":
            token = token[:-1]
    
    # E., Y. etc.
    if len(token) == 2 and token[0].isupper() and token[1] == ".":
        return True
    # Chl. ja Cfl.
    if len(token) == 4 and token[0].isupper() and token[-1] == "." and token[1:3].islower():
        return True
    
    if len(token) == 0: return False
    if token[-1] == ".":
        token = token[:-1]
    if len(token) == 0: return False
    if token[-1] == ",":
        return False
        if relPos < 0: # no commas before head
            return False
        else:
            token = token[:-1]
    if len(token) == 0: return False
    
    tokenLower = token.lower()
    if tokenLower in bacteriaTokens:
        return True
    for split in tokenLower.split("-"):
        if split in bacteriaTokens:
            return True
    for split in tokenLower.split("/"):
        if split in bacteriaTokens:
            return True
    
    if token == "JIP":
        return True
    
    if tokenLower.endswith("lla"):
        return True
    elif tokenLower.endswith("ica"):
        return True
    elif tokenLower.endswith("us") and tokenLower != "thus":
        return True
    elif tokenLower.endswith("um") and tokenLower not in ["phylum"]:
        return True
    elif tokenLower.endswith("ans") and tokenLower != "humans":
        return True
    elif tokenLower.endswith("bacter"):
        return True
    elif tokenLower.endswith("is") and tokenLower not in ["is", "this"]:
        return True
    #elif tokenLower.endswith("es"):
    #    return True
    elif tokenLower.endswith("ma"):
        return True
    elif tokenLower.endswith("ia"):
        return True
    elif tokenLower.endswith("ii"):
        return True
    elif tokenLower.endswith("li"):
        return True
    elif tokenLower.endswith("nii"):
        return True
    elif tokenLower.endswith("plasma"):
        return True
    elif tokenLower.endswith("plasmas"):
        return True
    elif tokenLower.endswith("ae"):
        return True
    elif tokenLower.endswith("ri"):
        return True
    elif tokenLower.endswith("ni"):
        return True

    if isExtraWord(token, toLower=True):
        return True
    
    isTrue = True
    for c in token:
        if c.isdigit() or c == "-" or c.isupper():
            continue
        else:
            isTrue = False
            break
    if isTrue:
        return True

    return False

def extend(input, output=None, entityTypes=["Bacterium"], verbose=False):
    if not (ET.iselement(input) and input.tag == "sentence"):
        print >> sys.stderr, "Loading corpus file", input
        corpusTree = ETUtils.ETFromObj(input)
        corpusRoot = corpusTree.getroot()
    
    bacteriaTokens = ExampleBuilders.PhraseTriggerExampleBuilder.getBacteriaTokens()
    
    if not (ET.iselement(input) and input.tag == "sentence"):
        sentences = corpusRoot.getiterator("sentence")
    else:
        sentences = [input]
    counts = defaultdict(int)
    for sentence in sentences:
        incorrectCount = 0
        sentenceText = sentence.get("text")
        tokens = tokenize(sentenceText)
        for entity in sentence.findall("entity"):
            counts["all-entities"] += 1
            if entity.get("type") not in entityTypes:
                continue
            headOffset = entity.get("headOffset")
            if headOffset == None:
                if verbose: print "WARNING, no head offset for entity", entity.get("id")
                headOffset = entity.get("charOffset")
            headOffset = Range.charOffsetToTuples(headOffset)[0]
            charOffset = entity.get("charOffset")
            assert charOffset != None, "WARNING, no head offset for entity " + str(entity.get("id"))
            charOffset = Range.charOffsetToTuples(charOffset)[0]
            tokPos = [0,0]
            tokIndex = None
            # find main token
            for i in range(len(tokens)):
                token = tokens[i]
                tokPos[1] = tokPos[0] + len(token) # - 1
                if Range.overlap(headOffset, tokPos):
                    tokIndex = i
                    break
                tokPos[0] += len(token)
            assert tokIndex != None, (entity.get("id"), entity.get("text"), tokens)
            skip = False
            if tokPos[0] < headOffset[0]:
                tokPos = headOffset
                skip = True
            if not skip:
                # Extend before
                beginIndex = tokIndex
                for i in range(tokIndex-1, -1, -1):
                    token = tokens[i]
                    if token.isspace():
                        continue
                    if not isBacteriaToken(token, bacteriaTokens, i - tokIndex):
                        beginIndex = i + 1
                        break
                    if i == 0:
                        beginIndex = i
                while tokens[beginIndex].isspace() or isExtraWord(tokens[beginIndex], toLower=False):
                    beginIndex += 1
                    if beginIndex >= tokIndex:
                        beginIndex = tokIndex
                        break
                # Extend after
                endIndex = tokIndex
                if tokens[tokIndex][-1] != ",":
                    endIndex = tokIndex
                    for i in range(tokIndex+1, len(tokens)):
                        token = tokens[i]
                        if token.isspace():
                            continue
                        if not isBacteriaToken(token, bacteriaTokens, i - tokIndex):
                            endIndex = i - 1
                            break
                        if i == len(tokens) - 1:
                            endIndex = i
                    while tokens[endIndex].isspace():
                        endIndex -= 1
                # Modify range
                if tokIndex > beginIndex:
                    for token in reversed(tokens[beginIndex:tokIndex]):
                        tokPos[0] -= len(token)
                if tokIndex < endIndex:
                    for token in tokens[tokIndex+1:endIndex+1]:
                        tokPos[1] += len(token)
                # Attempt to remove trailing periods and commas
                while not sentenceText[tokPos[1] - 1].isalnum():
                    tokPos[1] -= 1
                    if tokPos[1] < tokPos[0] + 1:
                        tokPos[1] = tokPos[0] + 1
                        break
                while not sentenceText[tokPos[0]].isalnum():
                    tokPos[0] += 1
                    if tokPos[0] >= tokPos[1]:
                        tokPos[0] = tokPos[1] - 1
                        break
                # Split merged names
                #newPos = [tokPos[0], tokPos[1]]
                #for split in sentenceText[tokPos[0]:tokPos[1]+1].split("/"):
                #    newPos[0] += len(split)
                #    if                 
            # Insert changed charOffset
            counts["entities"] += 1
            newOffset = tuple(tokPos)
            newOffsetString = Range.tuplesToCharOffset([newOffset])
            if verbose:
                print "Entity", entity.get("id"), 
                #print [entity.get("text"), sentenceText[headOffset[0]:headOffset[1]+1], sentenceText[newOffset[0]:newOffset[1]+1]],
                print [entity.get("text"), sentenceText[headOffset[0]:headOffset[1]], sentenceText[newOffset[0]:newOffset[1]]], 
                print [entity.get("charOffset"), entity.get("headOffset"), newOffsetString], "Sent:", len(sentence.get("text")),
            if newOffset != headOffset:
                counts["extended"] += 1
                if verbose: print "EXTENDED",
            if newOffset == charOffset:
                counts["correct"] += 1
                if verbose: print "CORRECT"
            else:
                counts["incorrect"] += 1
                incorrectCount += 1
                if verbose: print "INCORRECT"
            entity.set("charOffset", newOffsetString)
            #entity.set("text", sentenceText[newOffset[0]:newOffset[1]+1])
            entity.set("text", sentenceText[newOffset[0]:newOffset[1]])
        if incorrectCount > 0 and verbose:
            print "TOKENS:", "|".join(tokens)
            print "--------------------------------"
    if verbose:
        print counts
    
    if not (ET.iselement(input) and input.tag == "sentence"):
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        return corpusTree                    

if __name__=="__main__":
    print >> sys.stderr, "##### Extend Triggers #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    #assert(options.output != None)
    
    extend(options.input, options.output, verbose=options.debug)
