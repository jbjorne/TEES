import sys,os
import zipfile

class Sentence():
    def __init__(self, origId, text):
        self.origId = origId
        self.text = text
        self.entities = []
        self.relation = None
        self.comment = None
        
def processLines(lines):
    inDefinition = False
    comment = None
    sentence = None
    entities = []
    relation = None
    for line in lines:
        line = line.strip()
        if not inDefinition:
            inDefinition = True
            assert line[0].isdigit(), line
            origId, line = line.split("\t")
        else:
            if line.startswith("Comment:"):
                comment = line.split(":", 1)[-1].strip()

def getFiles(inputPath):
    archive = zipfile.ZipFile(inputPath, 'r')
    #print archive.namelist()
    trainFile = archive.open("SemEval2010_task8_all_data/SemEval2010_task8_training/TRAIN_FILE.TXT")
    trainLines = trainFile.readlines()
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