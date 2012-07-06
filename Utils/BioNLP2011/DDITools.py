import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict

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
                
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input file (interaction XML)")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file (txt file)")
    optparser.add_option("-d", "--add", default=None, dest="add", help="data to be added, e.g. rls classifications")
    optparser.add_option("-a", "--action", default=None, dest="action", help="")
    (options, args) = optparser.parse_args()
    assert options.action in ["SUBMISSION", "TRANSFER_RLS", "ADD_MTMX"]
    
    if options.action == "SUBMISSION":
        makeDDISubmissionFile(options.input, options.output)
    elif options.action == "TRANSFER_RLS":
        transferClassifications(options.input, options.add, options.output)
    elif options.action == "ADD_MTMX":
        addMTMX(options.input, options.add, options.output)
    else:
        assert False, options.action
