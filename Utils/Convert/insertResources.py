import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Download
import Utils.Settings as Settings
import codecs
import xml.etree.ElementTree as ET

def readResources(extractPath, subPath="BB3/species-dictionary/"):
    specAnn = {}
    for dataSet in ("dev", "train", "test"):
        for subtask in ("BioNLP-ST-2016_BB-event", "BioNLP-ST-2016_BB-event+ner"):
            sourcePath = os.path.join(extractPath, subPath, dataSet, subtask + dataSet)
            print >> sys.stderr, "Processing", sourcePath
            readDocuments(sourcePath, specAnn)
    return specAnn

def readDocuments(inPath, specAnn):
    for filename in os.listdir(inPath):
        if filename.endswith(".spec"):
            filePath = os.path.join(inPath, filename)
            docId = filename.split(".")[0]
            assert docId not in specAnn, docId
            specAnn[docId] = buildElements(filePath)
            
def buildElements(filePath):
    f = codecs.open(filePath, "rt", "utf-8")
    lines = f.readlines()
    f.close()
    spans = []
    for line in lines:
        text, offset, identifier, category, eType = line.strip().split("\t")
        span = ET.Element('span')
        span["text"] = text
        span["charOffset"] = "-".join(offset.split())
        span["identifier"] = identifier
        span["category"] = category
        span["type"] = eType
        spans.append(span)
    return spans

def download(extractPath, downloadPath, redownload=False):
    Utils.Download.downloadAndExtract(Settings.URL["BB16_SPECIES_TRAIN_AND_DEVEL"], extractPath, downloadPath, redownload=redownload)
    Utils.Download.downloadAndExtract(Settings.URL["BB16_SPECIES_TEST"], extractPath, downloadPath, redownload=redownload)

def process(extractPath, downloadPath):
    download(extractPath, downloadPath)
    readResources(extractPath)

process("/tmp/extract", "/tmp/download")