from ProcessUtils import *

class Parser:
    def __init__(self):
        self.escDict={"-LRB-":"(",
                 "-RRB-":")",
                 "-LCB-":"{",
                 "-RCB-":"}",
                 "-LSB-":"[",
                 "-RSB-":"]",
                 "``":"\"",
                 "''":"\"",
                 "\\/":"/",
                 "\\*":"*"}
        self.escSymbols = sorted(self.escDict.keys())

    def unescape(self, text):
        for escSymbol in self.escSymbols:
            text = text.replace(escSymbol, self.escDict[escSymbol])
        return text
    
    ###########################################################################
    # Parsing Elements
    ###########################################################################
    
    def readPenn(self, treeLine, sentenceDebugId=None):
        #global escDict
        #escSymbols = sorted(escDict.keys())
        tokens = []
        phrases = []
        stack = []
        treeLine = treeLine.strip()
        if treeLine != "":
            # Add tokens
            #prevSplit = None
            tokenCount = 0
            #splitCount = 0
            index = 0
            for char in treeLine:
                if char == "(":
                    stack.append( (index + 1, tokenCount) )
                elif char == ")":
                    span = treeLine[stack[-1][0]:index]
                    splits = span.split(None, 1) # span.split(string.whitespace)
                    if span.endswith(")"):
                        phrases.append( (stack[-1][1], tokenCount, splits[0]) )
                    else:
                        #if len(splits) == 2:
                        origTokenText = splits[1]
                        tokenText = self.unescape(origTokenText).strip()
                        pos = self.unescape(splits[0])
                        tokens.append( (tokenText, pos, origTokenText) )
                        #else:
                        #    print >> sys.stderr, "Warning, unreadable token '", repr(span), "' in", sentenceDebugId
                        tokenCount += 1
                    stack.pop()
                index += 1
        return tokens, phrases

    def insertTokens(self, tokens, sentence, tokenization, idStem="bt_", errorNotes=None):
        tokenCount = 0
        start = 0
        prevStart = None
        for tokenText, posTag, origTokenText in tokens:
            sText = sentence.get("text")
            # Determine offsets
            cStart = sText.find(tokenText, start)
            #assert cStart != -1, (tokenText, tokens, posTag, start, sText)
            if cStart == -1: # Try again with original text (sometimes escaping can remove correct text)
                cStart = sText.find(origTokenText, start)
            if cStart == -1 and prevStart != None: # Try again with the previous position, sometimes the parser duplicates tokens
                cStart = sText.find(origTokenText, prevStart)
                if cStart != -1:
                    start = prevStart
                    print >> sys.stderr, "Warning, token duplication", (tokenText, tokens, posTag, start, sText, errorNotes)
            if cStart == -1:
                print >> sys.stderr, "Token alignment error", (tokenText, tokens, posTag, start, sText, errorNotes)
                for subElement in [x for x in tokenization]:
                    tokenization.remove(subElement)
                return False
            cEnd = cStart + len(tokenText)
            prevStart = start
            start = cStart + len(tokenText)
            # Make element
            token = ET.Element("token")
            token.set("id", idStem + str(tokenCount))
            token.set("text", tokenText)
            token.set("POS", posTag)
            token.set("charOffset", str(cStart) + "-" + str(cEnd)) # NOTE: check
            tokenization.append(token)
            tokenCount += 1
        return True

    def insertPhrases(self, phrases, parse, tokenElements, idStem="bp_"):
        count = 0
        phrases.sort()
        for phrase in phrases:
            phraseElement = ET.Element("phrase")
            phraseElement.set("type", phrase[2])
            phraseElement.set("id", idStem + str(count))
            phraseElement.set("begin", str(phrase[0]))
            phraseElement.set("end", str(phrase[1]))
            t1 = None
            t2 = None
            if phrase[0] < len(tokenElements):
                t1 = tokenElements[phrase[0]]
            if phrase[1] < len(tokenElements):
                t2 = tokenElements[phrase[1]]
            if t1 != None and t2 != None:
                phraseElement.set("charOffset", t1.get("charOffset").split("-")[0] + "-" + t2.get("charOffset").split("-")[-1])
            parse.append(phraseElement)
            count += 1

    def insertDependencies(self, outfile, parse, tokenByIndex=None, sentenceId=None, skipExtra=0):
        # A list of tokens for debugging
        tokens = []
        for key in sorted(tokenByIndex):
            tokens.append(tokenByIndex[key].get("text"))
    
        depCount = 1
        line = outfile.readline()
        #line = line.encode('raw_unicode_escape').decode('utf-8') # fix latin1?
        #line = getUnicode(line)
        deps = []
        # BioNLP'09 Shared Task GENIA uses _two_ newlines to denote a failed parse (usually it's one,
        # the same as the BLLIP parser. To survive this, skipExtra can be used to define the number
        # of lines to skip, if the first line of a dependency parse is empty (indicating a failed parse) 
        if line.strip() == "" and skipExtra > 0:
            for i in range(skipExtra):
                outfile.readline()
        while line.strip() != "":
            #if "," not in line or "(" not in line:
            #    print >> sys.stderr, "Warning, unreadable dependency '", line.strip(), "', in sentence", sentenceId
            depType = t1 = t2 = t1Word = t2Word = t1Index = t2Index = None
            try:
                # Add dependencies
                depType, rest = line.strip()[:-1].split("(")
                t1, t2 = rest.split(", ")
                t1Word, t1Index = t1.rsplit("-", 1)
                #for escSymbol in escSymbols:
                #    t1Word = t1Word.replace(escSymbol, escDict[escSymbol])
                t1Word = self.unescape(t1Word).strip()
                while not t1Index[-1].isdigit(): t1Index = t1Index[:-1] # invalid literal for int() with base 10: "7'"
                t1Index = int(t1Index)
                t2Word, t2Index = t2.rsplit("-", 1)
                #for escSymbol in escSymbols:
                #    t2Word = t2Word.replace(escSymbol, escDict[escSymbol])
                t2Word = self.unescape(t2Word).strip()
                while not t2Index[-1].isdigit(): t2Index = t2Index[:-1] # invalid literal for int() with base 10: "7'"
                t2Index = int(t2Index)
            except Exception as e:
                print >> sys.stderr, e
                print >> sys.stderr, "Warning, unreadable dependency '", line.strip(), "', in sentence", sentenceId, [depType, t1, t2, (t1Word, t1Index), (t2Word, t2Index)]
                depType = None
            # Make element
            if depType != None and depType != "root":
                dep = ET.Element("dependency")
                dep.set("id", "sd_" + str(depCount))
                alignmentError = False
                if tokenByIndex != None:
                    if t1Index-1 not in tokenByIndex:
                        print >> sys.stderr, "Token not found", (t1Index-1, t1Word, depCount, sentenceId)
                        deps = []
                        while line.strip() != "": line = outfile.readline()
                        break
                    if t2Index-1 not in tokenByIndex:
                        print >> sys.stderr, "Token not found", (t2Index-1, t2Word, depCount, sentenceId)
                        deps = []
                        while line.strip() != "": line = outfile.readline()
                        break
                    if t1Word != tokenByIndex[t1Index-1].get("text"):
                        print >> sys.stderr, "Alignment error", (t1Word, tokenByIndex[t1Index-1].get("text"), t1Index-1, depCount, sentenceId, tokens)
                        alignmentError = True
                        if parse.get("stanfordAlignmentError") == None:
                            parse.set("stanfordAlignmentError", t1Word)
                    if t2Word != tokenByIndex[t2Index-1].get("text"):
                        print >> sys.stderr, "Alignment error", (t2Word, tokenByIndex[t2Index-1].get("text"), t2Index-1, depCount, sentenceId, tokens)
                        alignmentError = True
                        if parse.get("stanfordAlignmentError") == None:
                            parse.set("stanfordAlignmentError", t2Word)
                    dep.set("t1", tokenByIndex[t1Index-1].get("id"))
                    dep.set("t2", tokenByIndex[t2Index-1].get("id"))
                else:
                    dep.set("t1", "bt_" + str(t1Index))
                    dep.set("t2", "bt_" + str(t2Index))
                dep.set("type", depType)
                parse.insert(depCount-1, dep)
                depCount += 1
                if not alignmentError:
                    deps.append(dep)
            line = outfile.readline()
        return deps
    
    ###########################################################################
    # Analysis Elements
    ###########################################################################
    
    def addAnalysis(self, sentence, name, group):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            groupElement = setDefaultElement(sentenceAnalyses, group)
            return setDefaultElement(groupElement, name)
        else:
            analyses = setDefaultElement(sentence, "analyses")
            return setDefaultElement(analyses, name)
    
    def getAnalysis(self, sentence, name, attrib, group):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            groupElement = setDefaultElement(sentenceAnalyses, group)
            return getElementByAttrib(groupElement, name, attrib)
        else:
            analyses = setDefaultElement(sentence, "analyses")
            return getElementByAttrib(analyses, name, attrib)