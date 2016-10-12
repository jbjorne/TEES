import Utils.ElementTreeUtils as ETUtils
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
    
    def getCorpus(self, input):
        print >> sys.stderr, "Loading corpus", input
        corpusTree = ETUtils.ETFromObj(input)
        print >> sys.stderr, "Corpus file loaded"
        corpusRoot = corpusTree.getroot()
        return corpusTree, corpusRoot
    
    ###########################################################################
    # Parsing Elements
    ###########################################################################
    
    def insertPennTrees(self, treeFileName, corpusRoot, parseName, requireEntities=False, makePhraseElements=True, skipIds=[], skipParsed=True, addTimeStamp=True):
        print >> sys.stderr, "Inserting parses"
        treeFile = codecs.open(treeFileName, "rt", "utf-8")
        # Add output to sentences
        parseTimeStamp = time.strftime("%d.%m.%y %H:%M:%S")
        print >> sys.stderr, "BLLIP time stamp:", parseTimeStamp
        failCount = 0
        for sentence in self.getSentences(corpusRoot, requireEntities, skipIds, skipParsed):        
            treeLine = treeFile.readline()
            extraAttributes={"source":"TEES"} # parser was run through this wrapper
            if addTimeStamp:
                extraAttributes["date"] = parseTimeStamp # links the parse to the log file
            if not self.insertPennTree(sentence, treeLine, parseName, makePhraseElements=makePhraseElements, extraAttributes=extraAttributes):
                failCount += 1
        treeFile.close()
        return failCount
    
    def insertPennTree(self, sentence, treeLine, parseName="McCC", tokenizationName = None, makePhraseElements=True, extraAttributes={}, docId=None):
        # Find or create container elements
        analyses = setDefaultElement(sentence, "analyses")#"sentenceanalyses")
        #tokenizations = setDefaultElement(sentenceAnalyses, "tokenizations")
        #parses = setDefaultElement(sentenceAnalyses, "parses")
        # Check that the parse does not exist
        for prevParse in analyses.findall("parse"):
            assert prevParse.get("parser") != parseName
        # Create a new parse element
        parse = ET.Element("parse")
        parse.set("parser", parseName)
        if tokenizationName == None:
            parse.set("tokenizer", parseName)
        else:
            parse.set("tokenizer", tokenizationName)
        analyses.insert(getPrevElementIndex(analyses, "parse"), parse)
        
        parse.set("pennstring", treeLine.strip())
        for attr in sorted(extraAttributes.keys()):
            parse.set(attr, extraAttributes[attr])
        if treeLine.strip() == "":
            return False
        else:
            tokens, phrases = self.readPenn(treeLine, sentence.get("id"))
            # Get tokenization
            if tokenizationName == None: # Parser-generated tokens
                for prevTokenization in analyses.findall("tokenization"):
                    assert prevTokenization.get("tokenizer") != tokenizationName
                tokenization = ET.Element("tokenization")
                tokenization.set("tokenizer", parseName)
                for attr in sorted(extraAttributes.keys()): # add the parser extra attributes to the parser generated tokenization 
                    tokenization.set(attr, extraAttributes[attr])
                analyses.insert(getElementIndex(analyses, parse), tokenization)
                # Insert tokens to parse
                self.insertTokens(tokens, sentence, tokenization, errorNotes=(sentence.get("id"), docId))
            else:
                tokenization = getElementByAttrib(analyses, "tokenization", {"tokenizer":tokenizationName})
            # Insert phrases to parse
            if makePhraseElements:
                self.insertPhrases(phrases, parse, tokenization.findall("token"))
        return True  
    
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
    
    def readDependencies(self, depFile, skipExtra=0, sentenceId=None):
        line = depFile.readline()
        deps = []
        # BioNLP'09 Shared Task GENIA uses _two_ newlines to denote a failed parse (usually it's one,
        # the same as the BLLIP parser. To survive this, skipExtra can be used to define the number
        # of lines to skip, if the first line of a dependency parse is empty (indicating a failed parse) 
        if line.strip() == "" and skipExtra > 0:
            for i in range(skipExtra):
                depFile.readline()
        while line.strip() != "":
            depType = t1 = t2 = t1Word = t2Word = t1Index = t2Index = None
            try:
                depType, rest = line.strip()[:-1].split("(")
                t1, t2 = rest.split(", ")
                t1Word, t1Index = t1.rsplit("-", 1)
                t1Word = self.unescape(t1Word).strip()
                while not t1Index[-1].isdigit(): t1Index = t1Index[:-1] # invalid literal for int() with base 10: "7'"
                t1Index = int(t1Index) - 1
                t2Word, t2Index = t2.rsplit("-", 1)
                t2Word = self.unescape(t2Word).strip()
                while not t2Index[-1].isdigit(): t2Index = t2Index[:-1] # invalid literal for int() with base 10: "7'"
                t2Index = int(t2Index) - 1
                deps.append({"type":depType, "t1Word":t1Word, "t1":t1Index, "t2Word":t2Word, "t2":t2Index})
            except Exception as e:
                print >> sys.stderr, e
                print >> sys.stderr, "Warning, unreadable dependency '", line.strip(), "', in sentence", sentenceId, [depType, t1, t2, (t1Word, t1Index), (t2Word, t2Index)]
            line = depFile.readline()
        return deps
    
    def insertDependencies(self, depFile, parse, tokenByIndex=None, sentenceId=None, skipExtra=0):
        # A list of tokens for debugging
        tokens = []
        for key in sorted(tokenByIndex):
            tokens.append(tokenByIndex[key].get("text"))
    
        depCount = 1
        deps = self.readDependencies(depFile, skipExtra, sentenceId)
        elements = []
        for dep in deps:
            # Make element
            if dep["type"] != None and dep["type"] != "root":
                element = ET.Element("dependency")
                element.set("id", "sd_" + str(depCount))
                element.set("type", dep["type"])
                skip = True
                if tokenByIndex != None:
                    if dep["t1"] not in tokenByIndex:
                        print >> sys.stderr, "Token 1 not found", (dep, depCount, sentenceId)
                    elif dep["t2"] not in tokenByIndex:
                        print >> sys.stderr, "Token 2 not found", (dep, depCount, sentenceId)
                    else:
                        skip = False
                        if dep["t1Word"] != tokenByIndex[dep["t1"]].get("text"):
                            print >> sys.stderr, "Alignment error for token 1", (dep, tokenByIndex[dep["t1"]].get("text"), depCount, sentenceId, tokens)
                            skip = True
                            if parse.get("stanfordAlignmentError") == None:
                                parse.set("stanfordAlignmentError", dep["t1Word"])
                        if dep["t2Word"] != tokenByIndex[dep["t2"]].get("text"):
                            print >> sys.stderr, "Alignment error for token 2", (dep, tokenByIndex[dep["t2"]].get("text"), depCount, sentenceId, tokens)
                            skip = True
                            if parse.get("stanfordAlignmentError") == None:
                                parse.set("stanfordAlignmentError", dep["t2Word"])
                        element.set("t1", tokenByIndex[dep["t1"]].get("id"))
                        element.set("t2", tokenByIndex[dep["t2"]].get("id"))
                else:
                    element.set("t1", "bt_" + str(dep["t1"]))
                    element.set("t2", "bt_" + str(dep["t2"]))
                    skip = False
                if not skip:
                    parse.insert(depCount - 1, element)
                    depCount += 1
                    elements.append(element)
        return elements
    
    def getTokenByIndex(self, sentence, parse):
        tokenization = self.getAnalysis(sentence, "tokenization", {"tokenizer":parse.get("tokenizer")}, "tokenizations")
        assert tokenization != None
        count = 0
        tokenByIndex = {}
        for token in tokenization.findall("token"):
            tokenByIndex[count] = token
            count += 1
        return tokenByIndex
    
    def getDocumentOrigId(self, document):
        origId = document.get("pmid")
        if origId == None:
            origId = document.get("origId")
        if origId == None:
            origId = document.get("id")
        return origId
    
    def getSentences(self, corpusRoot, requireEntities=False, skipIds=[], skipParsed=True):
        for sentence in corpusRoot.getiterator("sentence"):
            if sentence.get("id") in skipIds:
                print >> sys.stderr, "Skipping sentence", sentence.get("id")
                continue
            if requireEntities:
                if sentence.find("entity") == None:
                    continue
            if skipParsed:
                if ETUtils.getElementByAttrib(sentence, "parse", {"parser":"McCC"}) != None:
                    continue
            yield sentence
    
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