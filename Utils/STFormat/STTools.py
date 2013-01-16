import sys, os, types
import codecs
import Validate

class Document:
    def __init__(self, id=None, loadFromDir=None, a2Tags=["a2"], readScores=False, debug=False):
        self.id = id
        self.text = None
        self.proteins = []
        self.triggers = []
        self.events = []
        self.words = []
        self.dependencies = []
        self.extras = []
        self.dataSet = None
        self.license = None
        self.debug = debug
        if loadFromDir != None:
            self.load(loadFromDir)
    
    def getEventOrRelationCount(self, countRelations=False):
        count = 0
        for event in self.events:
            if countRelations == event.isRelation():
                count += 1
        return count
    
    def getIdMap(self):
        idMap = {}
        for ann in self.proteins + self.triggers + self.events + self.dependencies + self.words:
            if ann.id in idMap:
                raise Exception("Duplicate id " + str(ann.id) + " in document " + str(self.id))
            idMap[ann.id] = ann
        return idMap
    
    def connectObjects(self):
        idMap = self.getIdMap()
        for ann in self.proteins + self.triggers + self.events + self.dependencies:
            ann.connectObjects(idMap)
    
    def unlinkSites(self):
        for event in self.events:
            event.unlinkSites()
    
    def connectSites(self):
        for event in self.events:
            event.connectSites()

    def load(self, dir, a2Tags=["a2", "rel"], readExtra=False):
        if self.debug:
            print >> sys.stderr, "Loading document", self.id
        a1Path = os.path.join(dir, self.id + ".a1")
        if os.path.exists(a1Path):
            self.loadA1(a1Path, readExtra)
        if a2Tags == None:
            return proteins, [], [], [], [], []
        for a2Tag in a2Tags:
            a2Path = os.path.join(dir, self.id + "." + a2Tag)
            if os.path.exists(a2Path):
                self.loadA2(a2Path, readExtra)
        self.text = None
        txtPath = os.path.join(dir, self.id + ".txt")
        if os.path.exists(txtPath):
            self.loadText(txtPath)
    
    def loadA1(self, filename, readExtra=False):
        #f = open(filename)
        f = codecs.open(filename, "rt", "utf-8")
        lines = f.readlines()
        count = 0
        for line in lines:
            if line[0] == "T":
                self.proteins.append(readTAnnotation(line, self.debug))
                count += 1
        for line in lines:
            if line[0] == "*":
                readStarAnnotation(line, proteins)
                count += 1
        for line in lines:
            if line[0] == "W":
                self.words.append(readTAnnotation(line))
                count += 1
        for line in lines:
            if line[0] == "R": # in a1-files, "R" refers to dependencies
                self.dependencies.append(readDependencyAnnotation(line))
                count += 1
        for line in lines:
            if line[0] == "X":
                count += 1
        assert count == len(lines), lines # check that all lines were processed
        f.close()
        # Mark source file type
        for ann in self.proteins + self.words + self.dependencies:
            ann.fileType = "a1"
        if len(self.dependencies) > 0:
            self.connectObjects()

    def loadA2(self, filename, readExtra=False):
        f = codecs.open(filename, "rt", "utf-8")
        lines = f.readlines()
        f.close()
        count = 0
        eventMap = {}
        for line in lines:
            if line[0] == "T":
                self.triggers.append( readTAnnotation(line, self.debug) )
                self.triggers[-1].fileType = "a2"
                count += 1
        for line in lines:
            if line[0] == "E" or line[0] == "R":
                event = readEvent(line, self.debug)
                self.events.append(event)
                if event.id in eventMap:
                    raise Exception("Duplicate event id " + str(event.id) + " in document " + str(self.id))
                eventMap[self.events[-1].id] = self.events[-1]
                self.events[-1].fileType = "a2"
                count += 1
        for line in lines:
            if line[0] == "M":
                mId, rest = line.strip().split("\t")
                mType, eventId = rest.split()
                assert mType in ["Speculation", "Negation"]
                if mType == "Speculation":
                    eventMap[eventId].speculation = mId
                elif mType == "Negation":
                    eventMap[eventId].negation = mId
                count += 1
        for line in lines:
            if line[0] == "*":
                readStarAnnotation(line, self.proteins + self.triggers)
                count += 1
        for line in lines:
            if line[0] == "X":
                count += 1
        assert count == len(lines), lines # check that all lines were processed
        self.connectObjects()
        self.connectSites()
    
    def loadText(self, filename):
        f = codecs.open(filename, "rt", "utf-8")
        self.text = f.read()
        f.close()

    def save(self, dir, resultFileTag="a2", debug=False, writeScores=False):
        id = str(self.id)
        if debug:
            print id
        if not os.path.exists(dir):
            os.makedirs(dir)
        
        updateIds(self.proteins)
        updateIds(self.triggers, getMaxId(self.proteins) + 1)
        updateIds(self.events)
        
        # write a1 file
        if self.proteins != None:
            out = codecs.open(os.path.join(dir, id + ".a1"), "wt", "utf-8")
            out.write(self.entitiesToString(self.proteins, writeScores))
            out.close()
        # write a2 (or rel) file
        resultFile = codecs.open(os.path.join(dir, id + "." + resultFileTag), "wt", "utf-8")
        resultFile.write(self.entitiesToString(self.triggers, writeScores, getMaxId(self.proteins) + 1))
        if debug: print >> sys.stderr, "Writing events"
        resultFile.write(self.eventsToString(writeScores))
        resultFile.close()
        # Write txt file
        out = codecs.open(os.path.join(dir, str(self.id) + ".txt"), "wt", "utf-8")
        out.write(self.text)
        out.close()

    def entitiesToString(self, entities, writeScores=False, idStart=0):
        updateIds(entities, idStart)
        s = u""
        for entity in entities:
            assert entity.id[0] == "T", (entity.id, entity.text)
            s += entity.toString(writeScores) + "\n"
        return s

    def eventsToString(self, writeScores=False):
        updateIds(self.events)
        s = u""
        mCounter = 1
        eventLines = []
        for event in self.events:
            s += event.toString(writeScores) + "\n"
            for modString in event.getModifierStrings(writeScores, mCounter):
                s += modString + "\n"
                mCounter += 1
        return s

class Annotation:
    def __init__(self, id = None, type = None, text=None, trigger=None, arguments=None, debug=False):
        self.id = id # protein/word/dependency/trigger/event
        self.type = type # protein/word/dependency/trigger/event
        self.text = text # protein/word/trigger
        self.charBegin = -1 # protein/word/trigger
        self.charEnd = -1 # protein/word/trigger
        self.alternativeOffsets = []
        self.equiv = [] # group of elements that are equivalent
        self.trigger = trigger # event (None for triggerless events / relations)
        self.arguments = [] # event/dependency/relation
        if arguments != None:
            self.arguments = arguments
        self.sites = []
        self.speculation = None # event 
        self.negation = None # event
        self.fileType = None # "a1" or "a2"
        self.extra = {}
        self.debug = debug
#        # Optional confidence scores
#        self.triggerScores = None
#        self.unmergingScores = None
#        self.speculationScores = None
#        self.negationScores = None
    
    def isNegated(self):
        return self.negation != None
    
    def isSpeculative(self):
        return self.speculation != None
    
    def isName(self):
        return self.type == "Protein" or self.type == "Gene"
    
    def isRelation(self):
        return self.trigger == None

    # for debugging
    def __repr__(self):
        s = "<Ann " + str(self.id) + "," + str(self.type)
        if self.trigger != None:
            s += ",R=" + str(self.trigger)
        if self.text != None:
            s += ",T=" + str(self.text)
        if self.arguments != None and len(self.arguments) > 0:
            s += ",A=" + str(self.arguments)
        return s + ">"
    
    def addArgument(self, type, target, siteOf=None, weights=None):
        newArgument = Argument(type, target, siteOf, weights)
        self.arguments.append(newArgument)
        return newArgument
    
    def connectObjects(self, idMap):
        # connect trigger
        if self.trigger != None and type(self.trigger) in types.StringTypes:
            self.trigger = idMap[self.trigger]
#            # Move scores from event to trigger
#            trigger.unmergingScores = self.unmergingScores
#            trigger.negationScores = self.negationScores
#            trigger.speculationScores = self.speculationScores
#            self.unmergingScores = None
#            self.negationScores = None
#            self.speculationScores = None
        # connect arguments
        for arg in self.arguments:
            arg.connectToObj(idMap)
    
    def unlinkSites(self):
        for arg in self.arguments:
            arg.siteOf = None
    
    def connectSites(self):
        for site in self.arguments:
            if site.type == "Site":
                for argument in self.arguments:
                    if argument.siteIdentifier == site.siteIdentifier and argument.type in ("Theme", "Cause") and argument.target.fileType == "a1":
                        assert site.siteOf == None, (site, self.arguments)
                        site.siteOf = argument
                        if self.debug:
                            print >> sys.stderr, "Connected site", site

    def _getArgumentIndex(self, argument):
        count = 1
        for currentArg in self.arguments:
            if argument == currentArg:
                if count == 1:
                    return ""
                else:
                    return str(count)
            elif argument.type == currentArg.type:
                count += 1
        assert False, (argument, self)
    
    def getArgumentFullType(self, argument):
        if argument.siteOf == None:
            return argument.type + self._getArgumentIndex(argument)
        else:
            indexSuffix = self._getArgumentIndex(argument.siteOf)
            if argument.siteOf.type == "Cause":
                return "C" + argument.type + indexSuffix
            else:
                return argument.type + indexSuffix
    
    def argumentToString(self, argument):
        return self.getArgumentFullType(argument) + ":" + argument.target.id
    
    def toString(self, addScores=False):
        s = self.id + "\t"
        s += self.type
        if self.trigger != None: # event
            s += ":" + self.trigger.id
        if self.charBegin != -1: # protein
            if self.trigger != None:
                raise Exception("A text-bound annotation cannot be an event (have a trigger): " + str(self) + ":" + str(self.arguments))
            s += " " + str(self.charBegin) + " " + str(self.charEnd) + "\t" + str(self.text).replace("\n", "&#10;").replace("\r", "&#10;")
        argStrings = []
        corefTargetProteins = set()
        for argument in self.arguments:
            if argument.type == "CorefTarget":
                assert self.type == "Coref"
                corefTargetProteins.add(argument.target.id)
            else:
                argStrings.append(self.argumentToString(argument))
        s += " " + " ".join(argStrings)
        if len(corefTargetProteins) > 0:
            s += "\t[" + ", ".join(sorted(list(corefTargetProteins))) + "]"
        return s
    
    def getModifierStrings(self, addScores=False, modCount=0):
        modStrings = []
        if self.speculation:
            modStrings.append("M" + str(modCount) + "\tSpeculation " + self.id)
            modCount += 1
#            if addScores and self.speculationScores != None:
#                modStrings[-1] += ":" + self.speculationScores.replace(":", "=")
        if self.negation:
            modStrings.append("M" + str(modCount) + "\tNegation " + self.id)
            modCount += 1
#            if addScores and self.negationScores != None:
#                modStrings[-1] += ":" + self.negationScores.replace(":", "=")
        return modStrings
    
    def getExtraStrings(self):
        pass

class Argument:
    def __init__(self, type, target, siteOf=None, extra=None):
        self.type, self.siteIdentifier = self._processType(type)
        self.target = target
        self.siteOf = siteOf
        if extra != None:
            self.extra = extra
        else:
            self.extra = {}
    
    # for debugging
    def __repr__(self):
        s = "<Arg " + str(self.type) + ",T=" + str(self.target)
        if self.siteOf != None:
            s += ",S=" + str(self.siteOf)
        if self.extra != None and len(self.extra) != 0:
            s += ",E=" + str(self.extra)
        if self.siteIdentifier != "":
            s += ",SI=" + str(self.siteIdentifier)
        return s + ">"
        
    def connectToObj(self, idMap):
        if self.target != None and type(self.target) in types.StringTypes:
            self.target = idMap[self.target]
            return
    
    def _processType(self, type):
        argType = type
        siteIdentifier = ""
        while argType[-1].isdigit():
            siteIdentifier = siteIdentifier + argType[-1]
            argType = argType[:-1]
        if argType == "CSite":
            siteIdentifier = "C" + siteIdentifier
            argType = "Site"
        elif argType == "Cause":
            siteIdentifier = "C" + siteIdentifier
        return argType, siteIdentifier

def getStatistics(documents, printStats=True, statSeparator="\n"):
    from collections import defaultdict
    import types
    if type(documents) in types.StringTypes:
        documents = loadSet(documents)
    
    stats = defaultdict(int)
    for document in documents:
        stats["total-docs"] += 1
        stats["total-events"] += document.getEventOrRelationCount()
        stats["total-relations"] += document.getEventOrRelationCount(True)
        stats["total-proteins"] += len(document.proteins)
        stats["doc-events-"+str(document.getEventOrRelationCount(True))] += 1
        stats["doc-relations-"+str(document.getEventOrRelationCount())] += 1
        stats["doc-proteins-"+str(len(document.proteins))] += 1
        for event in document.events:
            stats["events-"+event.type] += 1
            if event.speculation != None:
                stats["events-"+event.type+"-spec"] += 1
            if event.negation != None:
                stats["events-"+event.type+"-neg"] += 1
            argStats = defaultdict(int)
            nesting = False
            for arg in event.arguments:
                argType = arg.type
                if not arg.target.isName():
                    nesting = True
                argStats[argType] += 1
            if nesting:
                stats["events-"+event.type+"-parent"] += 1
            stats["args-"+event.type+"-"+"-".join([str(key)+"_"+str(argStats[key]) for key in sorted(argStats.keys())]) ] += 1
    if printStats:
        print >> sys.stderr, "Event Statistics:"
        print >> sys.stderr, statSeparator.join([str(key)+":"+str(stats[key]) for key in sorted(stats.keys())])
    return stats

def readTAnnotation(string, debug=False):
    #print string
    assert string[0] == "T" or string[0] == "W", string
    string = string.strip()
    ann = Annotation(debug=debug)
    splits = string.split("\t")
    ann.id = splits[0]
    middle = splits[1]
    ann.text = splits[2]
    ann.type, ann.charBegin, ann.charEnd = middle.split()
    ann.charBegin = int(ann.charBegin)
    ann.charEnd = int(ann.charEnd)
    # Process CoRef alternative offsets
    if len(splits) > 3:
        skip = False
        for split in splits[3:]:
            if not skip:
                cSplits = split.split()
                assert len(cSplits) == 2, (cSplits, string)
                c1 = int(cSplits[0])
                c2 = int(cSplits[1])
                ann.alternativeOffsets.append( (c1, c2) )
            skip = not skip
    return ann

def readStarAnnotation(string, proteins):
    assert string[0] == "*", string
    string = string.strip()
    star, rest = string.split("\t")
    equivs = []
    if rest.find("Equiv") == 0:
        splits = rest.split(" ")
        type = splits[0]
        assert type == "Equiv"
        entities = splits[1:] 
        equivs.append( entities )
    if len(equivs) > 0:
        protMap = {}
        for protein in proteins:
            protMap[protein.id] = protein
        for equiv in equivs:
            for member in equiv:
                for other in equiv:
                    if member == other:
                        continue
                    if not protMap[other] in protMap[member].equiv:
                        protMap[member].equiv.append(protMap[other])

def readEvent(string, debug=False):
    string = string.strip()
    event = Annotation(debug=debug)
    tabSplits = string.split("\t")
    event.id, rest = tabSplits[0], tabSplits[1]
    args = rest.split()
    eventType = args[0]
    eventArguments = args[1:]
    eventTypeSplits = eventType.split(":")
    event.type = eventType
    event.trigger = None
    if len(eventTypeSplits) > 1:
        event.trigger = eventTypeSplits[1]
    
    for argString in eventArguments:
        argSplits = argString.split(":")
        argType = argSplits[0]
        argTarget = argSplits[1]    
        event.addArgument(argType, argTarget)
    
    if len(tabSplits) == 3:
        assert event.type == "Coref", event
        assert tabSplits[2][0] == "[" and tabSplits[2][-1] == "]", (event, string, tabSplits)
        protIds = tabSplits[2][1:-1].split(",")
        for protId in protIds:
            event.addArgument("CorefTarget", protId.strip())
    return event

def readDependencyAnnotation(string):
    string = string.strip()
    id, depType, word1, word2 = string.split()
    assert word1[0] == "W" and word2[0] == "W", string
    ann = Annotation()
    ann.id = id
    ann.type = depType
    ann.addArgument("Word", word1)
    ann.addArgument("Word", word2)
    return ann

def loadSet(path, setName=None, level="a2", sitesAreArguments=False, a2Tag="a2", readScores=False, debug=False):
    assert level in ["txt", "a1", "a2"]
    if path.endswith(".tar.gz"):
        import tempfile
        import tarfile
        import shutil
        dir = tempfile.mkdtemp()
        f = tarfile.open(path, "r")
        f.extractall(dir)
        # Check if compressed directory is included in the package, like in the ST'11 corpus files
        compressedFilePath = os.path.join(dir, os.path.basename(path)[:-len(".tar.gz")])
        if not os.path.exists(compressedFilePath): # at least CO training set has a different dirname inside the tarfile
            compressedFilePath = compressedFilePath.rsplit("_", 1)[0]
            print >> sys.stderr, "Package name directory does not exist, trying", compressedFilePath
        if os.path.exists(compressedFilePath):
            print >> sys.stderr, "Reading document set from compressed filename directory", compressedFilePath
            dir = compressedFilePath
        f.close()
    elif path.endswith(".txt"):
        import tempfile
        import shutil
        dir = tempfile.mkdtemp()
        shutil.copy2(path, os.path.join(dir, os.path.basename(path)))
    else:
        dir = path
    
    ids = set()
    documents = []
    license = None
    if os.path.exists(os.path.join(dir, "LICENSE")):
        licenseFile = open(os.path.join(dir, "LICENSE"), "rt")
        license = "".join(licenseFile.readlines())
        licenseFile.close()
    for filename in os.listdir(dir):
        if filename.endswith(".txt"):
            ids.add(filename.split(".")[0])
    for id in sorted(list(ids)):
        #print "Loading", id
        doc = Document(id, dir, ["a2"], readScores, debug)
        doc.dataSet = setName
        doc.license = license
        documents.append(doc)
    
    if dir != path:
        shutil.rmtree(dir)
    return documents

def writeSet(documents, output, resultFileTag="a2", debug=False, writeScores=False):
    from collections import defaultdict
    import shutil
    counts = defaultdict(int)
    
    while output.endswith("/"):
        output = output[:-1]
    if output.endswith(".tar.gz"):
        outdir = output + "-temp"
    else:
        outdir = output
    if os.path.exists(outdir):
        shutil.rmtree(outdir)

#    if not validate:
#        print "Warning! No validation."
    for doc in documents:
#        if validate:
#            if debug: print >> sys.stderr, "Validating", doc.id
#            Validate.allValidate(doc, counts, task, verbose=debug)
        if debug: print >> sys.stderr, "Writing", doc.id
        doc.save(outdir, resultFileTag, writeScores=writeScores)
        
    if output.endswith(".tar.gz"):
        package(outdir, output, ["a1", "txt", resultFileTag, resultFileTag+".scores"])
        shutil.rmtree(outdir)
#    print counts

# Convenience functions  

def getMaxId(annotations):
    nums = [0]
    for annotation in annotations:
        if annotation.id != None:
            assert annotation.id[1:].isdigit(), annotation.id
            nums.append(int(annotation.id[1:]))
    return max(nums)

def updateIds(annotations, minId=0):
    newIds = False
    for ann in annotations:
        if ann.id == None:
            newIds = True
            break
    if newIds:
        idCount = max(getMaxId(annotations) + 1, minId)
        for ann in annotations:
            if len(ann.arguments) == 0 and ann.trigger == None:
                ann.id = "T" + str(idCount)
            elif ann.trigger == None: #ann.type in ["Subunit-Complex", "Protein-Component", "Coref", "Renaming", "SR-subunitof", "SR-equivto", "SR-partof", "SR-memberof"]:
                ann.id = "R" + str(idCount)
            #elif ann.trigger != None or ann.type in ["ActionTarget", "Interaction", "TranscriptionBy", ""]:
            else:
                ann.id = "E" + str(idCount)
            idCount += 1

def package(sourceDir, outputFile, includeTags=["a2", "a2.scores"]):
    import tarfile
    allFiles = os.listdir(sourceDir)
    tarFiles = []
    for file in allFiles:
        for tag in includeTags:
            if file.endswith(tag):
                tarFiles.append(file)
                break
    packageFile = tarfile.open(outputFile, "w:gz")
    tempCwd = os.getcwd()
    os.chdir(sourceDir)
    for file in tarFiles:
        packageFile.add(file)#, exclude = lambda x: x == submissionFileName)
    #if "final" in outputFile:
    #    packageFile.add("/home/jari/data/BioNLP11SharedTask/resources/questionnaire.txt", "questionnaire.txt")
    os.chdir(tempCwd)
    packageFile.close()

if __name__=="__main__":
    import sys
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    optparser = OptionParser(usage="%prog [options]\nST format input and output.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--outputTag", default="a2", dest="outputTag", help="a2 file extension.")
    optparser.add_option("-s", "--sentences", default=False, action="store_true", dest="sentences", help="Write each sentence to its own document")
    optparser.add_option("-r", "--origIds", default=False, action="store_true", dest="origIds", help="Use stored original ids (can cause problems with duplicates).")
    optparser.add_option("-a", "--task", default=2, type="int", dest="task", help="1 or 2")
    optparser.add_option("-d", "--debug", default=False, action="store_true", dest="debug", help="Verbose output.")
    (options, args) = optparser.parse_args()
    
    assert options.input != options.output
    documents = loadSet(options.input, "GE", level="a2", sitesAreArguments=False, a2Tag="a2", readScores=False, debug=options.debug)
    writeSet(documents, options.output, resultFileTag=options.outputTag, debug=options.debug, task=options.task, validate=True, writeScores=False)
