import os
import csv
import codecs
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET

def convertChemProt(inDir):
    filenames = os.listdir(inDir)
    filetypes = ["_abstracts.tsv", "_entities.tsv", "_relations.tsv"]
    documents = []
    for filename in filenames:
        if not (filename.endswith(".tsv") and any([filename.endswith(x) for x in filetypes])):
            continue
        docId, dataType = filename.rsplit("_", 1)
        dataType = dataType.split(".")[0]
        if docId not in documents:
            documents[docId] = {}
        assert dataType not in documents[docId]
        documents[docId][dataType] = os.path.join(inDir, filename)
    corpusName = "CP17"
    corpus = ET.Element("root", {"source":corpusName})
    docCount = 0
    for docId in sorted(documents.keys()):
        docFiles = documents[docId]
        document = ET.SubElement(corpus, "document", {"id":corpusName + ".d" + str(docCount)})
        docCount += 1
        with codecs.open(docFiles["abstracts"], "rt", "utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t", fieldnames=["id", "title", "abstract"]):
                
        
        