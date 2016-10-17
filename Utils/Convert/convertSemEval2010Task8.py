import sys,os
import zipfile

class Sentence():
    def __init__(self, origId, text):
        self.origId = origId
        self.text = text
        self.entities = []
        self.relation = None
        self.comment = None
    
    def process(self):
        entity = None
        for i in range(len(self.text)):
            if self.text[i] == "<":
                assert entity == None:
                entity = [None]
            
        
def processLines(lines):
    sentences = []
    sentence = None
    for line in lines:
        line = line.strip()
        if sentence == None:
            assert line[0].isdigit(), line
            origId, line = line.split("\t")
            sentence = Sentence(origId, line)
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
    train = processLines(trainFile.readlines())
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