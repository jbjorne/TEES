import os, sys
import csv
import codecs
from collections import defaultdict
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Range as Range
import Utils.ElementTreeUtils as ETUtils

def UnicodeDictReader(utf8_data, **kwargs):
    csv_reader = csv.DictReader(utf8_data, **kwargs)
    for row in csv_reader:
        yield {unicode(key, 'utf-8'):unicode(value, 'utf-8') for key, value in row.iteritems()}

def convertChemProt(inDir, outPath=None):
    filenames = os.listdir(inDir)
    filetypes = ["_abstracts.tsv", "_entities.tsv", "_relations.tsv"]
    dataSets = {}
    # Collect the file paths for the data types
    for filename in filenames:
        if not (filename.endswith(".tsv") and any([filename.endswith(x) for x in filetypes])):
            continue
        dataSetId, dataType = filename.rsplit("_", 1)
        dataType = dataType.split(".")[0]
        if dataSetId not in dataSets:
            dataSets[dataSetId] = {}
        assert dataType not in dataSets[dataSetId]
        dataSets[dataSetId][dataType] = os.path.join(inDir, filename)
    print >> sys.stderr, "Found", len(dataSets), "ChemProt datasets at", inDir
    # Build the Interaction XML
    corpusName = "CP17"
    corpus = ET.Element("root", {"source":corpusName})
    counts = defaultdict(int)
    docById = {}
    entityById = {}
    for dataSetId in sorted(dataSets.keys()):
        dataSet = dataSets[dataSetId]
        counts["set"] += 1
        with open(dataSet["abstracts"], "rt") as f:
            for row in UnicodeDictReader(f, delimiter="\t", fieldnames=["id", "title", "abstract"]):
                document = ET.SubElement(corpus, "document", {"id":corpusName + ".d" + str(counts["document"]), "origId":row["id"], "set":dataSetId})
                document.set("text", row["title"] + "\t" + row["abstract"])
                counts["document"] += 1
                assert document.get("origId") not in docById
                docById[document.get("origId")] = document
        with open(dataSet["entities"], "rt") as f:
            for row in UnicodeDictReader(f, delimiter="\t", fieldnames=["docId", "id", "type", "begin", "end", "text"]):
                document = docById[row["docId"]]
                entity = ET.SubElement(document, "entity", {"id":document.get("id") + ".e" + str(len([x for x in document.findall("entity")]))})
                entity.set("origId", row["id"])
                entity.set("type", row["type"].split("-")[0])
                entity.set("normalized", "True" if row["type"].endswith("Y") else "False")
                offset = (int(row["begin"]), int(row["end"]))
                docSpan = document.get("text")[offset[0]:offset[1]]
                assert docSpan == row["text"], (offset, docSpan, row)
                entity.set("charOffset", Range.tuplesToCharOffset((offset[0], offset[1])))
                entity.set("text", row["text"])
                if row["docId"] not in entityById:
                    entityById[row["docId"]] = {}
                assert entity.get("origId") not in entityById[row["docId"]]
                entityById[row["docId"]][entity.get("origId")] = entity
                counts["entity"] += 1
        with open(dataSet["relations"], "rt") as f:
            for row in UnicodeDictReader(f, delimiter="\t", fieldnames=["docId", "group", "groupEval", "type", "arg1", "arg2"]):
                for argId in ("1", "2"):
                    assert row["arg" + argId].startswith("Arg" + argId + ":")
                    row["arg" + argId] = row["arg" + argId][5:]
                document = docById[row["docId"]]
                interaction = ET.SubElement(document, "interaction", {"id":document.get("id") + ".i" + str(len([x for x in document.findall("interaction")]))})
                interaction.set("type", row["type"])
                interaction.set("group", row["group"])
                interaction.set("groupEval", "True" if row["groupEval"] == "Y" else "False")
                interaction.set("e1", entityById[row["docId"]][row["arg1"]].get("id"))
                interaction.set("e2", entityById[row["docId"]][row["arg2"]].get("id"))
                counts["interaction"] += 1
    print >> sys.stderr, "ChemProt conversion:", counts
    if outPath != None:
        ETUtils.write(corpus, outPath)
    return ET.ElementTree(corpus)
        