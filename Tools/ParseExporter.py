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
from collections import defaultdict

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
        tokens = []
        for token in tokenizationElement.findall("token"):
            begin, end = token.get("charOffset").split("-")
            tokens.append( [int(begin), int(end), token, token] )
        tokens.sort()
        return [x[2] for x in tokens]
    
    def getEscapedTokenTexts(self, tokens):
        tokenTextById = {}
        escDictKeys = sorted(self.unEscDict.keys())
        for token in tokens:
            for key in escDictKeys:
                tokenTextById[token.get("id")] = token.get("text").replace(key, self.unEscDict[key])
        return tokenTextById
    
    def getTokenIndexById(self, sortedTokens):
        return {sortedTokens[i].get("id"):i for i in range(len(sortedTokens))}
    
    def getDependenciesByHead(self, parseElement):
        dependenciesByHead = {}
        for dep in parseElement.findall("dependency"):
            if dep.get("t1") not in dependenciesByHead:
                dependenciesByHead[dep.get("t1")] = []
            dependenciesByHead[dep.get("t1")].append(dep)
        return dependenciesByHead
    
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
    
    def exportCoNLL(self, tokenizationElement, parseElement, outFile, conllFormat):
        tokens = self.getSortedTokens(tokenizationElement)
        tokenIndexById = self.getTokenIndexById(tokens)
        dependenciesByHead = self.getDependenciesByHead(parseElement)
        conllFormat = self.getCoNLLFormat(conllFormat=conllFormat)
        columns = self.getCoNLLColumns(conllFormat=conllFormat)
        for i in range(len(tokens)):
            token = tokens[i]
            row = {}
            for column in columns:
                if column == "ID":
                    row[column] = str(i + 1)
                elif column == "FORM":
                    row[column] = token.get("text")
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
                for dep in dependenciesByHead[tokenId]:
                    if dep == dependenciesByHead[tokenId][0]:
                        row["HEAD"] = str(tokenIndexById[dep.get("t2")] + 1)
                        row["DEPREL"] = dep.get("type")
                    elif conllFormat == "conllu":
                        if row["DEPS"] == "_":
                            row["DEPS"] = ""
                        else:
                            row["DEPS"] += "|"
                        row["DEPS"] += str(tokenIndexById[dep.get("t2")] + 1) + ":" + dep.get("type")
            outFile.write("\t".join(row[x] for x in columns) + "\n")
        outFile.write("\n") # one more newline to end the sentence (or to mark a sentence with no parse)
        return parseElement != None
    
    def export(self, input, output, parseName, tokenizerName=None, toExport=["tok", "ptb", "sd"], inputSuffixes=None, clear=False, tokenIdOffset=0, exportIds=None):
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
            counts = defaultdict(int)
            for document in documents:
                counter.update()
                exportId = IXMLUtils.getExportId(document, exportIds)
                counts["document"] += 1
                # Open document output files
                outfiles = {}
                for fileExt in toExport:
                    #print output, exportId , fileExt
                    outfilePath = output + "/" + exportId + "." + fileExt
                    if os.path.exists(outfilePath): # check for overlapping files
                        raise Exception("Export file '" + str(outfilePath) + "' already exists")
                    outfiles[fileExt] = codecs.open(outfilePath, "wt", "utf-8")
                # Export document text
                if "txt" in outfiles and document.get("text") != None:
                    outfiles["txt"].write(document.get("text"))
                    counts["txt"] += 1
                # Process all the sentences in the document
                for sentence in document.findall("sentence"):
                    counts["sentence"] += 1
                    parse = IXMLUtils.getParseElement(sentence, parseName)
                    tokenization = IXMLUtils.getTokenizationElement(sentence, tokenizerName)
                    if "sentences" in outfiles:
                        outfiles["sentences"].write(sentence.get("text").strip().replace("\n", " ").replace("\r", " ") + "\n")
                        counts["sentences"] += 1
                    if parse != None:
                        if "ptb" in outfiles:
                            if self.exportPennTreeBank(parse, outfiles["ptb"]):
                                counts["ptb"] += 1
                        if tokenization != None:
                            if "tok" in outfiles:
                                if self.exportTokenization(tokenization, parse, sentence, outfiles["tok"]):
                                    counts["tok"] += 1
                            if "sd" in outfiles:
                                if self.exportStanfordDependencies(parse, tokenization, outfiles["sd"], tokenIdOffset):
                                    counts["sd"] += 1
                            for conllFormat in ("conll", "conllx", "conllu"):
                                if conllFormat in outfiles:
                                    if self.exportCoNLL(tokenization, parse, outfiles[conllFormat], conllFormat):
                                        counts[conllFormat] += 1
                # Close document output files
                for fileExt in outfiles:
                    outfiles[fileExt].close()
                    outfiles[fileExt] = None
            
        print >> sys.stderr, "Parse export counts:"
        for k in sorted(counts.keys()):
            print >> sys.stderr, "  " + str(k) + ":", counts[k]