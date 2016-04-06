import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Download
import Utils.Settings as Settings
import Utils.Range as Range
import Utils.ElementTreeUtils as ETUtils
import codecs
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET

def readResources(extractPath):
    specAnn = {}
    for subPath in ("BB3/species-dictionary/", "BB3/stanford-ner/", "BB3/linnaeus/", "BB3/sr4gn"):
        for dataSet in ("dev", "train", "test"):
            for subtask in ("BioNLP-ST-2016_BB-event", "BioNLP-ST-2016_BB-event+ner"):
                sourcePath = os.path.join(extractPath, subPath, dataSet, subtask + "_" + dataSet)
                print >> sys.stderr, "Processing", sourcePath
                readDocuments(sourcePath, specAnn)
    return specAnn

def readDocuments(inPath, specAnn):
    for filename in os.listdir(inPath):
        ext = filename.split(".")[-1]
        if ext in ("spec", "sner", "tags"):
            filePath = os.path.join(inPath, filename)
            docId = filename.split(".")[0]
            #assert docId not in specAnn, docId
            if docId not in specAnn:
                specAnn[docId] = []
            specAnn[docId] += buildElements(filePath, ext)

def insertElements(corpus, specAnn):
    for document in corpus.iter('document'):
        docId = document.get("origId")
        assert docId in specAnn, docId
        for sentence in document.iter('sentence'):
            sentOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
            analyses = sentence.find("analyses")
            if not analyses:
                analyses = ET.SubElement(sentence, "analyses")
            #entitiesElement = sentence.find("entities")
            # Find the container
            container = analyses.find("entities") #None
#             for entitiesElement in entitiesElements:
#                 if entitiesElement.get("source") == "SPECIES":
#                     container = entitiesElement
#                     break
            if not container:
                container = ET.SubElement(analyses, "entities")
            #container.set("source", "SPECIES")
            # Map the spans
            for span in specAnn[docId][:]:
                offset = span.get("offset")
                if Range.overlap(offset, sentOffset):
                    if sentOffset[0] > offset[0] or sentOffset[1] < offset[1]:
                        continue
                    specAnn[docId].remove(span)
                    charOffset = (offset[0] - sentOffset[0], offset[1] - sentOffset[0])
                    matchingText = sentence.get("text")[charOffset[0]:charOffset[1]]
                    spanText = span.get("text")
                    #print matchingText, spanText
                    assert matchingText == spanText, (matchingText, spanText, charOffset)
                    span.set("charOffset", "-".join([str(x) for x in charOffset]))
                    assert not "--" in span.get("charOffset"), [str(x) for x in charOffset]
                    del span.attrib["offset"] #span.set("offset", "")
                    container.append(span)
            
def buildElements(filePath, sourceType):
    f = codecs.open(filePath, "rt", "utf-8")
    lines = f.readlines()
    f.close()
    spans = []
    for line in lines:
        if line.startswith("#"):
            continue
        splits = line.strip("\n").split("\t")
        identifier = ""
        category = ""
        source = sourceType
        if sourceType == "sner":
            text, offset, eType = splits
        elif sourceType == "spec":
            text, offset, identifier, category, eType = splits
        elif sourceType == "tags":
            identifier, documentId, start, end, text, comment = splits
            eType = identifier.split(":")[0]
            offset = start + " " + end
            source = "linnaeus"
        span = ET.Element('span')
        span.set("text", text)
        span.set("offset", [int(x) for x in offset.split()])
        #span.set("charOffset", "-".join(span.offset))
        span.set("identifier", identifier)
        span.set("category", category)
        span.set("type", eType)
        span.set("source", source)
        spans.append(span)
    return spans

def download(extractPath, downloadPath, redownload=False):
    for tag in ("SPECIES", "STANFORD_NER", "LINNAEUS", "SR4GN"):
        Utils.Download.downloadAndExtract(Settings.URL["BB16_" + tag + "_TRAIN_AND_DEVEL"], extractPath, downloadPath, redownload=redownload)
        Utils.Download.downloadAndExtract(Settings.URL["BB16_" + tag + "_TEST"], extractPath, downloadPath, redownload=redownload)

def process(input, output=None):
    download("/tmp/extract", "/tmp/download")
    specAnn = readResources("/tmp/extract")
    insertElements(input.getroot(), specAnn)
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(input.getroot(), output)
    return input

def test(extractPath, downloadPath, inCorpusPath, outCorpusPath):
    download(extractPath, downloadPath)
    specAnn = readResources(extractPath)
    inCorpus = ETUtils.ETFromObj(inCorpusPath)
    insertElements(inCorpus.getroot(), specAnn)
    ETUtils.write(inCorpus.getroot(), outCorpusPath)

#process("/tmp/extract", "/tmp/download", "/home/jari/Dropbox/data/BioNLP16/corpora/BB_EVENT_16-devel.xml", "/tmp/ner.xml")