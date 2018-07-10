import sys, os
import tempfile
import shutil
import subprocess
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
from Utils import Settings
from collections import defaultdict

#def loadEntities(filename):
#    f = open(filename)
#    entitiesPerSentence = defaultdict(lambda:list)
#    for line in f:
#        id, offset, name, type = line.split("|")
#        entitiesPerSentence[id].append([id, offset, name, type])
#    return entitiesPerSentence
#        
#def compareEntities(inputFile, goldFile):
#    input = loadEntities(inputFile)
#    gold = loadEntities(goldFile)
#    for id in gold:
#        for ge in gold[id]:
#            for ie in input[id]:
#                Range.charOffsetToSingleTuple(charOffset, offsetSep)

def evaluateXML(xml, goldPath=None, mode="interactions"):
    print >> sys.stderr, "Evaluating DDI13", mode
    xml = ETUtils.ETFromObj(xml)
    evaluatorDir = Settings.EVALUATOR["DDI13"]
    evaluatorProgram = "evaluateDDI.jar" if mode == "interactions" else "evaluateNER.jar"
    assert mode in ("interactions", "entities")
    tempDir = tempfile.mkdtemp()
    if goldPath == None:
        goldPath = Settings.EVALUATOR[("DDI13T92" if mode == "interactions" else "DDI13T91") + "_TEST-gold"]
    goldItems = [os.path.join(goldPath, x) for x in os.listdir(goldPath)]
    goldSubDirs = [x for x in goldItems if os.path.isdir(x)]
    goldFiles = [x for x in goldItems if not os.path.isdir(x)]
    goldHiddenFiles = [x for x in goldFiles if os.path.basename(x).startswith(".")]
    if len(goldSubDirs) > 0 and len(goldSubDirs) + len(goldHiddenFiles) != len(goldItems):
        print goldItems, goldSubDirs
        raise Exception("Gold directory " + goldPath + " contains both files and subdirectories")
    goldTempDir = os.path.join(tempDir, "gold")
    os.makedirs(goldTempDir)
    counts = defaultdict(int)
    if len(goldSubDirs) > 0:
        for goldSubDir in goldSubDirs:
            for item in os.listdir(goldSubDir):
                shutil.copy2(os.path.join(goldSubDir, os.path.basename(item)), os.path.join(goldTempDir, os.path.basename(item)))
                counts[goldSubDir] += 1
    else:
        for item in goldItems:
            shutil.copy2(os.path.join(goldPath, os.path.basename(item)), os.path.join(goldTempDir, os.path.basename(item)))
            counts[goldPath] += 1
    print >> sys.stderr, "Copied gold items to", goldTempDir, dict(counts)
    evaluatorTempDir = os.path.join(tempDir, "evaluator")
    os.makedirs(evaluatorTempDir)
    shutil.copy2(os.path.join(evaluatorDir, evaluatorProgram), os.path.join(evaluatorTempDir, evaluatorProgram))
    print >> sys.stderr, "Copied evaluator", evaluatorProgram, "to", evaluatorTempDir
    subFile = os.path.join(tempDir, "submission.txt")
    makeDDI13SubmissionFile(xml, subFile, mode)
    command = "java -jar " + os.path.join(evaluatorTempDir, evaluatorProgram) + " '" + goldTempDir + "' " + subFile
    print >> sys.stderr, command
    #currentDir = os.getcwd()
    #os.chdir(evaluatorDir)
    p = subprocess.Popen(command, shell=True) #, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate(input='\n')
    #for s in ["".join(x.readlines()).strip() for x in (p.stderr, p.stdout)]:
    #    if s != "":
    #        print >> sys.stderr, s
    #os.chdir(currentDir)
    #shutil.rmtree(tempDir)

def makeDDI13SubmissionFile(input, output, mode="interactions", idfilter=None):
    xml = ETUtils.ETFromObj(input)
    outFile = open(output, "wt")
    for sentence in xml.getiterator("sentence"):
        sentenceId = sentence.get("id")
        if idfilter != None and idfilter not in sentenceId:
            continue
        # Output entities
        if mode == "entities":
            for entity in sentence.findall("entity"):
                if entity.get("type") != "neg":
                    outFile.write(sentenceId)
                    offsets = Range.charOffsetToTuples(entity.get("charOffset"))
                    for i in range(len(offsets)):
                        offsets[i] = (offsets[i][0], offsets[i][1]-1)
                    outFile.write("|" + Range.tuplesToCharOffset(offsets, rangeSep=";"))
                    outFile.write("|" + entity.get("text"))
                    outFile.write("|" + entity.get("type"))
                    outFile.write("\n")    
        if mode == "interactions":
            # First determine which pairs interact
            intMap = defaultdict(lambda:defaultdict(lambda:None))
            for interaction in sentence.findall("interaction"):
                # Make mapping both ways to discard edge directionality. This isn't actually needed,
                # since MultiEdgeExampleBuilder builds entity pairs in the same order as this function,
                # but shouldn't harm to include it and now it works regardless of pair direction.
                if interaction.get("type") != "neg" and interaction.get("given") != "True":
                    intMap[interaction.get("e1")][interaction.get("e2")] = interaction
                    intMap[interaction.get("e2")][interaction.get("e1")] = interaction
            # Then write all pairs to the output file
            entities = sentence.findall("entity")
            for i in range(0, len(entities)-1):
                for j in range(i+1, len(entities)):
                    eIId = entities[i].get("id")
                    eJId = entities[j].get("id")
                    outFile.write(sentenceId + "|" + eIId + "|" + eJId + "|")
                    if intMap[eIId][eJId] != None:
                        interaction = intMap[eIId][eJId]
                        assert interaction.get("type") != "neg"
                        outFile.write("1|" + interaction.get("type") + "\n")
                    else:
                        outFile.write("0|null\n")
    outFile.close()

def makeDDISubmissionFile(input, output):
    xml = ETUtils.ETFromObj(input)
    outFile = open(output, "wt")
    for sentence in xml.getiterator("sentence"):
        # First determine which pairs interact
        intMap = defaultdict(lambda:defaultdict(lambda:None))
        for interaction in sentence.findall("interaction"):
            # Make mapping both ways to discard edge directionality. This isn't actually needed,
            # since MultiEdgeExampleBuilder builds entity pairs in the same order as this function,
            # but shouldn't harm to include it and now it works regardless of pair direction.
            if interaction.get("type") != "neg":
                intMap[interaction.get("e1")][interaction.get("e2")] = interaction
                intMap[interaction.get("e2")][interaction.get("e1")] = interaction
        # Then write all pairs to the output file
        entities = sentence.findall("entity")
        for i in range(0, len(entities)-1):
            for j in range(i+1, len(entities)):
                eIId = entities[i].get("id")
                eJId = entities[j].get("id")
                outFile.write(eIId + "\t" + eJId + "\t")
                if intMap[eIId][eJId] != None:
                    outFile.write("1\n")
                else:
                    outFile.write("0\n")

def transferClassifications(input, rls, output):
    assert os.path.exists(input), input
    f = open(input, "rt")
    inputLines = f.readlines()
    f.close()
    
    assert os.path.exists(rls), rls
    f = open(rls, "rt")
    rlsLines = f.readlines()
    f.close()
    
    outFile = open(output, "wt")
    assert len(inputLines) == len(rlsLines), (len(inputLines), len(rlsLines))
    for inputLine, rlsLine in zip(inputLines, rlsLines):
        outFile.write(inputLine.rsplit("\t", 1)[0] + "\t" + rlsLine)
    outFile.close()

def addMTMX(input, mtmxDir, output=None):
    from collections import defaultdict
    # read interaction XML
    print "Reading interaction XML"
    counts = defaultdict(int)
    xml = ETUtils.ETFromObj(input).getroot()
    docById = {}
    for document in xml.getiterator("document"):
        docId = document.get("origId")
        assert docId not in docById
        docById[docId] = document
        counts["document"] += 1
    for entity in xml.getiterator("entity"):
        counts["entity"] += 1
    
    # read MTMX files
    print "Processing MTMX"
    for filename in sorted(os.listdir(mtmxDir)):
        if filename.endswith(".xml"):
            print >> sys.stderr, filename,
            fileId = filename.split("_")[0]
            if fileId not in docById:
                print >> sys.stderr, "skipped"
                continue
            else:
                print >> sys.stderr, "processing"
            doc = docById[fileId]
            entityByOrigId = {}
            for entity in doc.getiterator("entity"):
                assert entity.get("origId") not in entityByOrigId, entity.get("origId")
                entityByOrigId[entity.get("origId")] = entity
            mtmx = ETUtils.ETFromObj(os.path.join(mtmxDir, filename)).getroot()
            for phrase in mtmx.getiterator("PHRASE"):
                if phrase.get("ID") in entityByOrigId:
                    entity = entityByOrigId[phrase.get("ID")]
                    mapCount = 0
                    for map in phrase.getiterator("MAP"):
                        if (map.get("NAME").lower() == entity.get("text").lower()) or (map.get("NAME_SHORT").lower() == entity.get("text").lower()):
                            if entity.get("mtmxProb") != None:
                                if int(entity.get("mtmxProb")) > int(map.get("PROB")):
                                    break
                                else:
                                    counts["mapped-multi"] += 1
                                    counts["mapped-multi-"+str(mapCount)] += 1
                                    #print filename, phrase.get("ID")
                            else:
                                counts["mapped-at-least-once"] += 1
                            entity.set("mtmxProb", str(map.get("PROB")))
                            entity.set("mtmxCui", str(map.get("CUI")))
                            entity.set("mtmxName", str(map.get("NAME")))
                            entity.set("mtmxNameShort", str(map.get("NAME_SHORT")))
                            entity.set("mtmxSemTypes", str(map.get("SEMTYPES")))
                            counts["mappings"] += 1
                            mapCount += 1
    print >> sys.stderr, counts
    if output != None:
        ETUtils.write(xml, output)

def addTestGold(input, testGoldPath, output=None):
    counts = defaultdict(int)
    print >> sys.stderr, "Reading interaction XML"
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    goldInteractions = {}
    goldEntities = {}
    if os.path.isfile(testGoldPath):
        print >> sys.stderr, "Reading gold interactions from file", testGoldPath
        with open(testGoldPath, "rt") as f:
            for line in f:
                e1, e2, isDDI = line.strip().split()
                assert isDDI in ("1", "0")
                isDDI = isDDI == "1"
                sentId = e1.rsplit(".", 1)[0]
                if sentId not in goldInteractions:
                    goldInteractions[sentId] = []
                goldInteractions[sentId].append(ET.Element("interaction", {"type":("DDI" if isDDI else "neg"), "e1":e1, "e2":e2, "interaction":("true" if isDDI else "false"), "id":sentId + "." + str(len(goldInteractions[sentId]))}))
    else:
        print >> sys.stderr, "Reading gold interactions from directory", testGoldPath
        assert os.path.isdir(testGoldPath), testGoldPath
        for subDir in ("DrugBank", "MedLine"):
            subPath = os.path.join(testGoldPath, subDir)
            assert os.path.isdir(subPath), subPath
            for filename in os.listdir(subPath):
                counts["subDir-" + subDir] += 1
                #print >> sys.stderr, "Processing", os.path.join(subPath, filename)
                if not filename.endswith(".xml"):
                    continue
                docXML = ETUtils.ETFromObj(os.path.join(subPath, filename)).getroot()
                for sentence in docXML.iter("sentence"):
                    sentId = sentence.get("id")
                    for entity in sentence.findall("entity"):
                        assert entity.get("id") not in goldEntities, entity.attrib
                        goldEntities[entity.get("id")] = entity
                    for interaction in sentence.findall("pair"):
                        interaction.tag = "interaction"
                        if interaction.get("type") == None:
                            assert interaction.get("ddi") == "false", interaction.attrib
                            interaction.set("type", "neg")
                        if sentId not in goldInteractions:
                            goldInteractions[sentId] = []
                        goldInteractions[sentId].append(interaction)
    for sentId in goldInteractions:
        counts["gold-sentences"] += 1
        for interaction in goldInteractions[sentId]:
            counts["gold-" + interaction.get("type")] += 1
    print >> sys.stderr, "Adding gold interactions to corpus"
    for sentence in corpusRoot.iter("sentence"):
        counts["corpus-sentences"] += 1
        entities = {}
        for entity in sentence.findall("entity"):
            assert entity.get("id") not in entities
            entities[entity.get("id")] = entity
        sentGoldInteractions = goldInteractions.get(sentence.get("id"), [])
        if len(sentGoldInteractions) > 0:
            counts["corpus-sentences-with-matching-gold"] += 1
        for interaction in sentGoldInteractions:
            goldE1 = goldEntities.get(interaction.get("e1"))
            goldE2 = goldEntities.get(interaction.get("e2"))
            for goldEntity in (goldE1, goldE2):
                if goldEntity != None:
                    corpusEntity = entities[goldEntity.get("id")]
                    assert goldEntity.get("text") == corpusEntity.get("text"), [goldEntity.attrib, corpusEntity.attrib]
            if interaction.get("type") != "neg":
                sentence.append(interaction)
                counts["added-" + interaction.get("type")] += 1
    print >> sys.stderr, dict(counts)
    if output != None:
        ETUtils.write(corpusTree, output)
    return corpusTree
                
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(description="Tools for the DDI'11 Shared Task")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input file (interaction XML)")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file (txt file)")
    optparser.add_option("-d", "--add", default=None, dest="add", help="data to be added, e.g. rls classifications")
    optparser.add_option("-a", "--action", default=None, dest="action", help="")
    optparser.add_option("-f", "--idfilter", default=None, dest="idfilter", help="")
    optparser.add_option("-m", "--mode", default=None, dest="mode", help="")
    (options, args) = optparser.parse_args()
    
    if options.action == "SUBMISSION_DDI11":
        makeDDISubmissionFile(options.input, options.output)
    if options.action == "SUBMISSION_DDI13":
        makeDDI13SubmissionFile(options.input, options.output, options.mode, options.idfilter)
    elif options.action == "TRANSFER_RLS":
        transferClassifications(options.input, options.add, options.output)
    elif options.action == "ADD_MTMX":
        addMTMX(options.input, options.add, options.output)
    elif options.action == "ADD_TEST_GOLD":
        addTestGold(options.input, options.add, options.output)
    elif options.action == "EVALUATE_DDI13":
        evaluateXML(options.input, None, options.mode)
    else:
        assert False, options.action
