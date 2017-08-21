import os, sys
import csv
import codecs
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Range as Range

def convertChemProt(inDir):
    filenames = os.listdir(inDir)
    filetypes = ["_abstracts.tsv", "_entities.tsv", "_relations.tsv"]
    dataSets = []
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
    # Build the Interaction XML
    corpusName = "CP17"
    corpus = ET.Element("root", {"source":corpusName})
    docCount = 0
    docById = {}
    entityById = {}
    for dataSetId in sorted(dataSets.keys()):
        dataSet = dataSets[dataSetId]
        with codecs.open(dataSet["abstracts"], "rt", "utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t", fieldnames=["id", "title", "abstract"]):
                document = ET.SubElement(corpus, "document", {"id":corpusName + ".d" + str(docCount), "origId":row["id"], "text":row["text"], "title":row["title"], "set":dataSetId})
                docCount += 1
                assert document.get("origId") not in docById
                docById[document.get("origId")] = document
        with codecs.open(dataSet["entities"], "rt", "utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t", fieldnames=["docId", "id", "type", "begin", "end", "text"]):
                document = docById[row["docId"]]
                entity = ET.SubElement(document, "entity", {"id":document.get("id") + ".e" + len([x for x in document.findall("entity")])})
                entity.set("origId", row["id"])
                entity.set("type", row["type"].split("-")[0])
                entity.set("normalized", "True" if row["type"].endswith("Y") else "False")
                docSpan = document.get("text")[row["begin"]:row["end"]]
                assert docSpan == row["text"], (docSpan, row)
                entity.set("charOffset", Range.tuplesToCharOffset((row["begin"], row["end"])))
                entity.set("text", row["text"])
                if row["docId"] not in entityById:
                    entityById[row["docId"]] = {}
                assert entity.get("origId") not in entityById[row["docId"]]
                entityById[row["docId"]][entity.get("origId")] = entity
        with codecs.open(dataSet["entities"], "rt", "utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t", fieldnames=["docId", "group", "groupEval", "type", "arg1", "arg2"]):
                document = docById[row["docId"]]
                interaction = ET.SubElement(document, "interaction", {"id":document.get("id") + ".i" + len([x for x in document.findall("interaction")])})
                interaction.set("type", row["type"])
                interaction.set("group", row["group"])
                interaction.set("groupEval", "True" if row["groupEval"] == "Y" else "False")
                interaction.set("e1", entityById[row["docId"]][row["arg1"]].get("id"))
                interaction.set("e2", entityById[row["docId"]][row["arg2"]].get("id"))
    return ET.ElementTree(corpus)
        