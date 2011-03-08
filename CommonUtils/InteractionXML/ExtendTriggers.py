try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import Range

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

def isBacteriaToken(token):
    if len(token) == 2 and token[0].isupper() and token[1] == ".":
        return True
    elif token.endswith("lla"):
        return True
    elif token.endswith("us"):
        return True
    elif token.endswith("um"):
        return True
    elif token.endswith("ans"):
        return True
    elif token.endswith("bacter"):
        return True
    elif token.endswith("is"):
        return True
    elif token.endswith("es"):
        return True
    elif token.endswith("ma"):
        return True
    elif token.endswith("ia"):
        return True
    elif token.endswith("ii"):
        return True
    elif token.endswith("li"):
        return True
    elif token.endswith("plasma"):
        return True
    elif token.endswith("plasmas"):
        return True
    elif token.endswith("ae"):
        return True
    elif token.endswith("ri"):
        return True
    elif token.endswith("ni"):
        return True

    elif token.lower == "strain":
        return True
    elif token.lower == "organisms":
        return True
    elif token.lower == "fetus":
        return True
    elif token.lower == "subsp.":
        return True
    elif token.lower == "subspecies":
        return True
    elif token.lower == "-like":
        return True
    elif token.lower == "sp.":
        return True
    elif token.lower == "species":
        return True
    
    isTrue = True
    for c in token:
        if c.isdigit() or c == "-" or c.isupper():
            pass
        else:
            isTrue = False
            break
    if isTrue:
        return True
    
    return False

def extend(input, task="BB", simulation=True):
    print >> sys.stderr, "Loading corpus file", input
    corpusRoot = ETUtils.ETFromObj(input).getroot()
    
    sentences = corpusRoot.findall("sentence")
    for sentence in sentences:
        sentenceText = sentence.get("text")
        tokens = tokenize(sentenceText)
        for entity in sentence.findall("entity"):
            headOffset = Range.charOffsetToSingleTuple(entity.get("headOffset"))
            charOffset = Range.charOffsetToSingleTuple(entity.get("charOffset"))
            origCharOffset = None
            if headOffset != charOffset:
                origCharOffset = charOffset
            tokPos = [0,0]
            tokIndex = None
            # find main token
            for i in range(len(tokens)):
                token = tokens[i]
                tokPos[1] = tokPos[0] + len(token) - 1
                if Range.overlap(headOffset):
                    tokIndex = i
                    break
                tokPos[0] += len(token)
            assert tokIndex != None, (entity.get("id"), entity.get("text"), tokens)
            # Extend before
            for i in range(tokIndex-1, 0, -1):
                token = tokens[i]
                if token.isspace():
                    continue
                if not isBacteriaToken(token):
                    beginPos = i + 1
            # Extend after
            for i in range(tokIndex+1, len(tokens)):
                token = tokens[i]
                if token.isspace():
                    continue
                if not isBacteriaToken(token):
                    endPos = i - 1
                    
