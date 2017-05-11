import sys, os, shutil
import codecs
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
from Parser import Parser
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import Utils.Range
from collections import defaultdict, OrderedDict
import json

class ParseExporter(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.unEscDict = {}
        for k, v in self.escDict.iteritems():
            self.unEscDict[v] = k

    def getTokenText(self, tokenElement):
        # it's unlikely there would be newlines inside tokens
        return tokenElement.get("text").replace("\n", " ").replace("\r", " ").strip()
    
#     def getTokens(self, tokenizationElement):
#         # order tokens by charOffset
#         tokenObjs = []
#         for token in tokenizationElement.findall("token"):
#             charOffset = token.get("charOffset")
#             begin, end = charOffset.split("-")
#             tokenObjs.append( [int(begin), int(end), token] )
#         tokenObjs.sort()
#         
#         # Get token texts, and mark indices moved by splitting
#         index = 0
#         tokenTextById = {}
#         tokenById = {} #tokenIdMap = {} # zero-based
#         splitFrom = None
#         for tokenObj in tokenObj:
#             token = tokenObj[2]
#             tokenId = token.get("id")
#             if token.get("splitFrom") != None:
#                 if splitFrom != token.get("splitFrom"): # this token begins a new set of split tokens
#                     splitFrom = token.get("splitFrom")
#                     tokenTexts.append(self.getTokenText(token))
#                 else: # this token continues an existing set of split tokens
#                     tokenTexts[-1] = tokenTexts[-1] + self.getTokenText(token)
#             else: # a non-split token
#                 splitFrom = None
#                 tokenTexts.append(self.getTokenText(token))
#             #tokenIdMap[index] = len(tokenTexts) - 1
#             tokenById[token.get("id")] = token
#             index += 1
#         return tokenTexts, tokenById

#     def getTokens(self, tokenizationElement, escaping=False):
#         tokens = []
#         for token in tokenizationElement.findall("token"):
#             charOffset = token.get("charOffset")
#             begin, end = charOffset.split("-")
#             tokens.append( [int(begin), int(end), token, token.get("text")] )
#             if escaping:
    
    def getSortedTokens(self, tokenizationElement):
        tokens = sorted([(Utils.Range.charOffsetToSingleTuple(x.get("charOffset")), x) for x in tokenizationElement.findall("token")])
        return [x[1] for x in tokens]
    
    def getEscapedTokenTexts(self, tokens):
        tokenTextById = {}
        escDictKeys = sorted(self.unEscDict.keys())
        for token in tokens:
            for key in escDictKeys:
                tokenTextById[token.get("id")] = token.get("text").replace(key, self.unEscDict[key])
        return tokenTextById
    
    def getTokenIndexById(self, sortedTokens):
        return {sortedTokens[i].get("id"):i for i in range(len(sortedTokens))}
    
    def getDependenciesByToken(self, parseElement, tokenAttrName):
        assert tokenAttrName in ("t1", "t2")
        dependenciesByToken = {}
        for dep in parseElement.findall("dependency"):
            tId = dep.get(tokenAttrName)
            if tId not in dependenciesByToken:
                dependenciesByToken[tId] = []
            dependenciesByToken[tId].append(dep)
        return dependenciesByToken
    
    def exportTokenization(self, tokenizationElement, parseElement, sentenceElement, outFile):
        tokens = self.getSortedTokens(tokenizationElement)
        if len(tokens) > 0:
            outFile.write(" ".join([x.get("text") for x in tokens]) + "\n")
        else:
            outFile.write(" ".join(sentenceElement.get("text").strip().split()) + "\n")
        return True  
    
    def exportPennTreeBank(self, parseElement, outFile):
        pennstring = None
        if parseElement != None:
            pennstring = parseElement.get("pennstring")
        if pennstring != None and pennstring.strip() != "":
            outFile.write(pennstring.strip())
        outFile.write("\n")
        return pennstring != None
    
    def exportStanfordDependencies(self, parseElement, tokenizationElement, outFile, tokenIdOffset=0):
        #global unEscDict
        #escDictKeys = sorted(self.unEscDict.keys())
        
        tokens = []
        # Collect tokens
        if tokenizationElement != None:
            tokens = self.getSortedTokens(tokenizationElement)
            #tokenById = {x["id"]:x for x in tokens}
            tokenTextById = self.getEscapedTokenTexts(tokens)
            #for token in tokens:
            #    for key in escDictKeys:
            #        tokenTextById[token["id"]] = token["text"].replace(key, self.unEscDict[key])
            tokenIndexById = self.getTokenIndexById(tokens)
            
        # Process dependencies
        if parseElement != None:
            for dependency in parseElement.findall("dependency"):
                if dependency.get("split") != None: # ignore dependencies created by protein name splitter
                    continue
                t1Id = dependency.get("t1")
                t2Id = dependency.get("t2")
                #t1Index = tokenIdMap[int(dependency.get("t1").split("_")[-1]) + tokenIdOffset] # tokenIdOffset can convert to zero-based
                #t2Index = tokenIdMap[int(dependency.get("t2").split("_")[-1]) + tokenIdOffset] # tokenIdOffset can convert to zero-based
                #assert t1Index < len(tokens), (t1Index, tokens, tokenIdMap, dependency.attrib)
                #assert t2Index < len(tokens), (t2Index, tokens, tokenIdMap, dependency.attrib)
                t1 = tokenTextById[t1Id] + "-" + str(tokenIndexById[t1Id] + 1)
                t2 = tokenTextById[t2Id] + "-" + str(tokenIndexById[t2Id] + 1)
                outFile.write(dependency.get("type") + "(" + t1 + ", " + t2 + ")\n")
        outFile.write("\n") # one more newline to end the sentence (or to mark a sentence with no dependencies)
        return parseElement != None
    
    def exportCoNLL(self, tokenizationElement, parseElement, outFile, conllFormat, counts):
        tokens = self.getSortedTokens(tokenizationElement)
        tokenIndexById = self.getTokenIndexById(tokens)
        tokenIdMap = {key:str(tokenIndexById[key] + 1) for key in tokenIndexById}
        for token in tokens:
            if token.get("origId") != None:
                tokenIdMap[token.get("id")] = token.get("origId")
        if len(tokenIdMap.values()) != len(set(tokenIdMap.values())):
            raise Exception("Duplicate ids in exporting CoNLL format")
        dependenciesByHead = self.getDependenciesByToken(parseElement, "t2")
        conllFormat = self.getCoNLLFormat(conllFormat=conllFormat)
        columns = self.getCoNLLColumns(conllFormat=conllFormat)
        for metadata in parseElement.findall("meta"):
            metaline = u"# "
            if metadata.get("type") != None:
                metaline += metadata.get("type") + " = "
            metaline += metadata.get("text") + "\n"
            outFile.write(metaline)
        for i in range(len(tokens)):
            token = tokens[i]
            row = {}
            for column in columns:
                if column == "ID":
                    #if token.get("origId") != None:
                    #    tokenIdMap[token.get("id")] = token.get("origId")
                    row[column] = tokenIdMap[token.get("id")]
                elif column == "FORM":
                    row[column] = token.get("text")
                    if token.get("origText") != None:
                        row[column] = token.get("origText")
                else:
                    row[column] = "_"
                    for key in (column, column.lower()):
                        if token.get(key) != None:
                            row[column] = token.get(key)
            if conllFormat == "conllx" and row.get("POSTAG") == "_" and row.get("CPOSTAG") == "_":
                row["CPOSTAG"] = token.get("POS", "_")
            elif conllFormat == "conllu" and row.get("UPOSTAG") == "_" and row.get("XPOSTAG") == "_":
                row["UPOSTAG"] = token.get("POS", "_")
            # Add dependencies
            tokenId = token.get("id")
            if tokenId in dependenciesByHead:
                primaryDeps = [x for x in dependenciesByHead[tokenId] if x.get("secondary") == None]
                secondaryDeps = [x for x in dependenciesByHead[tokenId] if x.get("secondary") == "True"]
                # Check if any dependencies will be lost
                if len(primaryDeps) > 1:
                    if conllFormat == "conllx": # CoNLL-X can have only one dependency per token
                        counts["tokens-with-lost-deps"] += len(primaryDeps) - 1
                    else: # CoNLL-U can have only one primary dependency per token
                        counts["tokens-with-unranked-deps"] += len(primaryDeps) - 1
                        secondaryDeps += primaryDeps[1:]
                # Add the single primary dependency
                if len(primaryDeps) > 0:
                    row["HEAD"] = tokenIdMap[primaryDeps[0].get("t1")]
                    row["DEPREL"] = primaryDeps[0].get("type")
                # If the token is the root token, set the primary dependency as the root dependency
                if token.get("root") != None:
                    if "HEAD" in row:
                        counts["tokens-with-lost-root-dep"] += 1
                    else:
                        row["HEAD"] = 0
                        row["DEPREL"] = token.get("root")
                # In CoNLL-U format, add the secondary dependencies
                if len(secondaryDeps) > 0 and conllFormat == "conllu":
                    #secondaryDeps = [x[1] for x in sorted([(tokenIndexById[x.get("t1")], x) for x in secondaryDeps])] # Sort by token index
                    secondaryDeps.sort(key=lambda x: tokenIndexById[x.get("t1")])
                    row["DEPS"] = "|".join([tokenIdMap[x.get("t1")] + ":" + x.get("type") for x in secondaryDeps])
            outFile.write("\t".join(row[x] for x in columns) + "\n")
        outFile.write("\n") # one more newline to end the sentence (or to mark a sentence with no parse)
        return parseElement != None
    
    def exportEPE(self, tokenizationElement, parseElement, sentence, sentenceCount, outFile, propertyTypes="AUTO"):
        tokens = self.getSortedTokens(tokenizationElement) if tokenizationElement != None else []
        if len(tokens) == 0: # There is no parse for this sentence
            return False
        tokenIndexById = self.getTokenIndexById(tokens)
        dependenciesByHead = self.getDependenciesByToken(parseElement, "t1") if parseElement != None else {}
        obj = OrderedDict([("id",sentenceCount + 1), ("nodes",[])])
        basicKeys = set(["POS", "text", "origText", "charOffset", "headOffset"])
        if propertyTypes == "AUTO":
            propertyTypes = ("POS", "lemma")
        sentencePos = Utils.Range.charOffsetToSingleTuple(sentence.get("charOffset"))[0]
        for i in range(len(tokens)):
            token = tokens[i]
            #print token.attrib
            charOffset = Utils.Range.charOffsetToSingleTuple(token.get("charOffset"))
            node = OrderedDict([("id",i+1), ("form",token.get("text")), ("start",charOffset[0] + sentencePos), ("end",charOffset[1] + sentencePos)])
            if token.get("origText") != None:
                node["form"] = token.get("origText")
            if token.get("root") != None:
                node["top"] = True
            node["properties"] = OrderedDict([("pos",token.get("POS"))])
            for key in token.attrib:
                if key not in basicKeys:
                    if propertyTypes == None or key in propertyTypes:
                        node["properties"][key] = token.get(key)
            # Add dependencies
            tokenId = token.get("id")
            if tokenId in dependenciesByHead:
                #print token.attrib, [x.attrib for x in dependenciesByHead[tokenId]]
                edges = []
                for dep in dependenciesByHead[tokenId]:
                    edges.append(OrderedDict([("label",dep.get("type")), ("target",tokenIndexById[dep.get("t2")] + 1)]))
                edges.sort(key=lambda k: k["target"], reverse=True)
                node["edges"] = edges
            obj["nodes"].append(node)
        outFile.write(json.dumps(obj) + "\n")
        return True
    
    def export(self, input, output, parseName, tokenizerName=None, toExport=["tok", "ptb", "sd"], inputSuffixes=None, clear=False, tokenIdOffset=0, exportIds=None, useSetDirs=False):
        print >> sys.stderr, "##### Export Parse #####"
        if toExport == None:
            toExport = ["txt", "sentences", "tok", "ptb", "sd"]
        print >> sys.stderr, "Exporting parse formats", toExport
        
        if os.path.exists(output) and clear:
            shutil.rmtree(output)
        if not os.path.exists(output):
            os.makedirs(output)
        if inputSuffixes != None:
            inputFileNames = []
            for suffix in inputSuffixes:
                inputFileNames.append(input + suffix)
        else:
            inputFileNames = [input]
    
        for inputFileName in inputFileNames:
            print >> sys.stderr, "Processing input file", inputFileName
            corpusRoot = ETUtils.ETFromObj(inputFileName).getroot()
            documents = corpusRoot.findall("document")
            counter = ProgressCounter(len(documents), "Documents")
            counts = {"corpus":defaultdict(int)}
            for fileExt in toExport:
                counts[fileExt] = defaultdict(int)
            for document in documents:
                counter.update()
                counts["corpus"]["documents"] += 1
                exportId = IXMLUtils.getExportId(document, exportIds)
                # Open document output files
                outfiles = {}
                for fileExt in toExport:
                    #print output, exportId , fileExt
                    if useSetDirs:
                        outfilePath = os.path.join(output, document.get("set"), exportId + "." + fileExt)
                    else:
                        outfilePath = os.path.join(output, exportId + "." + fileExt)
                    if os.path.exists(outfilePath): # check for overlapping files
                        raise Exception("Export file '" + str(outfilePath) + "' already exists")
                    if not os.path.exists(os.path.dirname(outfilePath)):
                        os.makedirs(os.path.dirname(outfilePath))
                    outfiles[fileExt] = codecs.open(outfilePath, "wt", "utf-8")
                # Export document text
                if "txt" in outfiles and document.get("text") != None:
                    outfiles["txt"].write(document.get("text"))
                    if "txt" not in counts:
                        counts["txt"] = defaultdict(int)
                    counts["txt"]["documents"] += 1
                # Process all the sentences in the document
                sentenceCount = 0
                for sentence in document.findall("sentence"):
                    counts["corpus"]["sentences"] += 1
                    parse = IXMLUtils.getParseElement(sentence, parseName)
                    tokenization = IXMLUtils.getTokenizationElement(sentence, tokenizerName)
                    if "sentences" in outfiles:
                        outfiles["sentences"].write(sentence.get("text").strip().replace("\n", " ").replace("\r", " ") + "\n")
                        counts["sentences"]["sentences"] += 1
                    if "ptb" in outfiles:
                        if self.exportPennTreeBank(parse, outfiles["ptb"]):
                            counts["ptb"]["sentences"] += 1
                    if tokenization != None:
                        if "tok" in outfiles:
                            if self.exportTokenization(tokenization, parse, sentence, outfiles["tok"]):
                                counts["tok"]["sentences"] += 1
                        if "sd" in outfiles:
                            if self.exportStanfordDependencies(parse, tokenization, outfiles["sd"], tokenIdOffset):
                                counts["sd"]["sentences"] += 1
                        for conllFormat in ("conll", "conllx", "conllu"):
                            if conllFormat in outfiles:
                                if self.exportCoNLL(tokenization, parse, outfiles[conllFormat], conllFormat, counts[conllFormat]):
                                    counts[conllFormat]["sentences"] += 1
                        if "epe" in outfiles:
                            if self.exportEPE(tokenization, parse, sentence, sentenceCount, outfiles["epe"]):
                                counts["epe"]["sentences"] += 1
                    sentenceCount += 1
                # Close document output files
                for fileExt in outfiles:
                    outfiles[fileExt].close()
                    outfiles[fileExt] = None
            
        print >> sys.stderr, "Parse export counts:"
        for k in sorted(counts.keys()):
            print >> sys.stderr, "  " + str(k) + ":", dict(counts[k])