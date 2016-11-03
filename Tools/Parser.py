import sys
import codecs
import time
import Utils.ElementTreeUtils as ETUtils
from ProcessUtils import *
import Utils.Align as Align
from collections import defaultdict
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

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
        print >> sys.stderr, "Constituency parsing time stamp:", parseTimeStamp
        #failCount = 0
        counts = defaultdict(int)
        for sentence in self.getSentences(corpusRoot, requireEntities, skipIds, skipParsed):        
            treeLine = treeFile.readline()
            extraAttributes={"source":"TEES"} # parser was run through this wrapper
            if addTimeStamp:
                extraAttributes["date"] = parseTimeStamp # links the parse to the log file
            if not self.insertPennTree(sentence, treeLine, parseName, makePhraseElements=makePhraseElements, extraAttributes=extraAttributes, counts=counts):
                counts["fail"] += 1
            counts["sentences"] += 1
        treeFile.close()
        # Show statistics
        print >> sys.stderr, "Parsed", counts["sentences"], "sentences"
        print >> sys.stderr, dict(counts)
        if counts["sentences-without-penn-tree"] == 0:
            print >> sys.stderr, "All sentences had a Penn tree"
        else:
            print >> sys.stderr, "Warning, no penn tree for", counts["sentences-without-penn-tree"], "out of", counts["sentences"], "sentences"
            print >> sys.stderr, "The \"pennstring\" attribute of these sentences has an empty string."  
        return counts
    
    def insertPennTree(self, sentence, treeLine, parseName="McCC", tokenizationName = None, makePhraseElements=True, extraAttributes={}, docId=None, counts=None):
        # Find or create container elements
        analyses = setDefaultElement(sentence, "analyses")#"sentenceanalyses")
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
            counts["sentences-without-penn-tree"] += 1
        else:
            tokens, phrases = self.readPennTree(treeLine, sentence.get("id"))
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
                self.insertTokens(tokens, sentence, tokenization, counts=counts)
            else:
                tokenization = getElementByAttrib(analyses, "tokenization", {"tokenizer":tokenizationName})
            # Insert phrases to parse
            if makePhraseElements:
                self.insertPhrases(phrases, parse, tokens)
            counts["sentences-with-penn-tree"]
    
    def readPennTree(self, treeLine, sentenceDebugId=None):
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
                        phrases.append({"begin":stack[-1][1], "end":tokenCount - 1, "type":splits[0]})
                    else:
                        #if len(splits) == 2:
                        origTokenText = splits[1]
                        tokenText = self.unescape(origTokenText).strip()
                        pos = self.unescape(splits[0])
                        tokens.append({"text":tokenText, "POS":pos, "origText":origTokenText, "index":tokenCount})
                        #else:
                        #    print >> sys.stderr, "Warning, unreadable token '", repr(span), "' in", sentenceDebugId
                        tokenCount += 1
                    stack.pop()
                index += 1
        return tokens, phrases
    
    def alignTokens(self, tokens, tokenization, counts=None, tag="dep-"):
        if counts == None:
            counts = defaultdict(int)
        elements = tokenization.findall("token")
        weights = None #{"match":1, "mismatch":-2, "space":-3, "open":-3, "extend":-3}
        alignedSentence, alignedCat, diff, alignedOffsets = Align.align([x.get("text") for x in elements], [x["text"] for x in tokens], weights=weights)
        if diff.count("|") + diff.count("-") != len(diff):
            print >> sys.stderr, alignedSentence
            print >> sys.stderr, diff
            print >> sys.stderr, alignedCat
            #print alignedOffsets
#        pos = 0
        for i in range(len(tokens)):
            counts[tag + "tokens-total"] += 1
            elementOffset = alignedOffsets[i]
            if elementOffset != None:
                tokens[i]["element"] = elements[elementOffset]
                counts[tag + "tokens-align"] += 1
            else:
                counts[tag + "tokens-no-align"] += 1

    def insertTokens(self, tokens, sentence, tokenization, idStem="t", counts=None):
        #catenatedTokens, catToToken = self.mapTokens([x["text"] for x in tokens])
        if counts == None:
            counts = defaultdict(int)
        tokenSep = " "
        tokensText = tokenSep.join([x["text"] for x in tokens])
        sentenceText = sentence.get("text")
        alignedSentence, alignedCat, diff, alignedOffsets = Align.align(sentenceText, tokensText)
        if diff.count("|") + diff.count("-") != len(diff):
            print >> sys.stderr, alignedSentence
            print >> sys.stderr, diff
            print >> sys.stderr, alignedCat
            #print alignedOffsets
        pos = 0
        tokenIndex = 0
        for token in tokens:
            counts["tokens-parse"] += 1
            tokenOffsets = [x for x in alignedOffsets[pos:pos + len(token["text"])] if x != None]
            if len(tokenOffsets) > 0:
                #tokenIndex = max(matching, key=lambda key: matching[key])
                # Make element
                element = ET.Element("token")
                element.set("id", idStem + str(tokenIndex))
                #element.set("i", str(token["index"]))
                element.set("text", token["text"])
                offset = (min(tokenOffsets), max(tokenOffsets) + 1)
                matchingText = sentenceText[offset[0]:offset[1]]
                if token["text"] != matchingText:
                    element.set("match", "part")
                    element.set("matchText", matchingText)
                    counts["tokens-partial-match"] += 1
                else:
                    element.set("match", "exact")
                    counts["tokens-exact-match"] += 1
                if "POS" in token:
                    element.set("POS", token["POS"])
                element.set("charOffset", str(offset[0]) + "-" + str(offset[1]))
                tokenization.append(element)
                token["element"] = element
                counts["tokens-elements"] += 1
            else:
                counts["tokens-no-match"] += 1
            tokenIndex += 1
            pos += len(token["text"]) + len(tokenSep)
        if len(tokens) > 0:
            counts["sentences-with-tokens"] += 1

    def insertPhrases(self, phrases, parse, tokens, idStem="p"):
        count = 0
        phrases.sort()
        tokenByIndex = {x["index"]:x for x in tokens}
        for phrase in phrases:
            phraseElement = ET.Element("phrase")
            phraseElement.set("type", phrase["type"])
            phraseElement.set("id", idStem + str(count))
            begin = phrase["begin"]
            end = phrase["end"]
            phraseElement.set("begin", str(phrase["begin"]))
            phraseElement.set("end", str(phrase["end"]))
            t1 = tokenByIndex[begin].get("element")
            t2 = tokenByIndex[end].get("element")
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
                depType, rest = line.strip()[:-1].split("(", 1)
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
            
    def insertDependencies(self, dependencies, sentence, parse, tokenization, idStem="d", counts=None):
        tokensById = {}
        dependencies = [x for x in dependencies if x["type"] != "root"]
        for dep in dependencies:
            t1, t2 = int(dep["t1"]), int(dep["t2"])
            tokensById[t1] = {"text":dep["t1Word"], "index":t1}
            tokensById[t2] = {"text":dep["t2Word"], "index":t2}
        depTokens = [tokensById[i] for i in sorted(tokensById.keys())]
        if tokenization != None:
            self.alignTokens(depTokens, tokenization, counts=counts, tag="dep-")
        else:
            self.insertTokens(depTokens, sentence, tokenization, counts=counts)
        count = 0
        elements = []
        for dep in dependencies:
            counts["deps-total"] += 1
            t1, t2 = int(dep["t1"]), int(dep["t2"])
            if "element" in tokensById[t1] and "element" in tokensById[t2]:
                element = ET.Element("dependency")
                element.set("type", dep["type"])
                element.set("id", idStem + str(count))
                element.set("t1", tokensById[t1]["element"].get("id"))
                element.set("t2", tokensById[t2]["element"].get("id"))
                elements.append(element)
                parse.insert(count, element)
                count += 1
                counts["deps-elements"] += 1
            else:
                counts["deps-skipped"] += 1
        if count == 0:
            if len(dependencies) == 0:
                counts["sentences-with-no-parser-deps"] += 1
            else:
                counts["sentences-with-no-element-deps"] += 1
        else:
            counts["sentences-with-deps"] += 1
        return elements
            
    def insertDependencyParses(self, depFile, sentence, parse, tokenization, skipExtra=0, counts=None):
        deps = self.readDependencies(depFile, skipExtra, sentence.get("id"))
        elements = self.insertDependencies(deps, sentence, parse, tokenization, counts=counts)
        return elements
    
    def getTokenByIndex(self, sentence, parse, ignore=None):
        tokenization = self.getAnalysis(sentence, "tokenization", {"tokenizer":parse.get("tokenizer")}, "tokenizations")
        assert tokenization != None
        count = 0
        tokenByIndex = {}
        for token in tokenization.findall("token"):
            tokenText = token.get("text")
            if ignore != None:
                for char in ignore:
                    tokenText = tokenText.replace(char, "")
                tokenText = tokenText.strip()
            if tokenText != "":
                token = ET.Element(token.tag, token.attrib) # copy the element so it can be modified
                token.set("filteredText", tokenText)
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
    
    def addAnalysis(self, sentence, name, group, attrib=None):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            groupElement = setDefaultElement(sentenceAnalyses, group)
            element = setDefaultElement(groupElement, name)
        else:
            analyses = setDefaultElement(sentence, "analyses")
            element = setDefaultElement(analyses, name)
        if attrib != None:
            for key in attrib:
                element.set(key, attrib[key])
        return element
    
    def getAnalysis(self, sentence, name, attrib, group, addIfNotExist=False):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            groupElement = setDefaultElement(sentenceAnalyses, group)
            element = getElementByAttrib(groupElement, name, attrib)
        else:
            analyses = setDefaultElement(sentence, "analyses")
            element = getElementByAttrib(analyses, name, attrib)
        if element == None and addIfNotExist:
            element = self.addAnalysis(sentence, name, group=group, attrib=attrib)
        return element
            