import sys,os
import re
import zipfile
import xml.etree.ElementTree as ET
import Utils.ElementTreeUtils as ETUtils

class Sentence():
    def __init__(self, origId, text, corpusId):
        self.origId = origId
        self.id = "SE10T8.d" + origId + ".s" + origId
        self.text = text
        self.entities = []
        self.relation = None
        self.comment = None
    
    def process(self):
        self.entities.append(self.getEntity(self.text, "e1"))
        self.entities.append(self.getEntity(self.text, "e2"))
    
    def _getEntity(self, line, tag):
        before, entityText, after = re.split(r'<' + tag + '>|</' + tag + '>', line)
        begin = len(before)
        end = len(before) + len(entityText)
        return ET.Element("entity", {"text":entityText, "charOffset":str(begin)+"-"+str(end), "id":self.id + "." + tag})
        
def processLines(lines, dataSet, corpusId="SE10T8"):
    sentences = []
    sentence = None
    corpus = ET.Element("corpus", {"source":corpusId})
    xml = ET.ElementTree()
    root = xml.getroot()
    for line in lines:
        line = line.strip().strip("\"")
        if sentence == None:
            assert line[0].isdigit(), line
            origId, line = line.split("\t")
            sentence = Sentence(origId, line, corpusId)
        else:
            if line.startswith("Comment:"):
                sentence.comment = line.split(":", 1)[-1].strip()
            elif line != "":
                sentence.relation = line
            else:
                assert sentence != None
                sentences.append(sentence)
                sentence = None

def getFiles(inputPath):
    archive = zipfile.ZipFile(inputPath, 'r')
    #print archive.namelist()
    trainFile = archive.open("SemEval2010_task8_all_data/SemEval2010_task8_training/TRAIN_FILE.TXT")
    train = processLines(trainFile.readlines(), "train")
    trainFile.close()
    
    return trainFile, None

def convert(inputPath):
    train, test = getFiles(inputPath)

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None)
    optparser.add_option("-o", "--outdir", default=None, dest="outdir", help="directory for output files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    convert(options.input)