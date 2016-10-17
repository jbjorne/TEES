import sys,os
import re
import zipfile
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import xml.etree.ElementTree as ET
import Utils.ElementTreeUtils as ETUtils

class Sentence():
    def __init__(self, origId, text, corpusId):
        self.origId = origId
        self.id = corpusId + ".d" + origId + ".s" + origId
        self.text = text
        self.entities = []
        self.relation = None
        self.comment = None
    
    def process(self, directed):
        # Build the entities
        for tag in ("e1", "e2"):
            self.entities.append(self._getEntity(self.text, tag))
            self.text = self.text.replace("<" + tag + ">", "").replace("</" + tag + ">", "")
        # Check entity offsets
        for entity in self.entities:
            begin, end = [int(x) for x in entity.get("charOffset").split("-")]
            assert entity.get("text") == self.text[begin:end], (entity.get("text"), self.text, self.text[begin:end], [begin, end])
        # Build the interactions
        # Build the sentence
        sentElem = ET.Element("sentence", {"id":self.id, "charOffset":"0-"+str(len(self.text))})
        for entity in self.entities:
            sentElem.append(entity)
        return sentElem
    
    def _getEntity(self, line, tag):
        try:
            before, entityText, after = re.split(r'<' + tag + '>|</' + tag + '>', line)
        except ValueError as e:
            print "ValueError in line '" + line + "' for tag", tag
            raise e
        begin = len(before)
        end = len(before) + len(entityText)
        return ET.Element("entity", {"text":entityText, "charOffset":str(begin)+"-"+str(end), "id":self.id + "." + tag})
        
def processLines(lines, dataSet, directed=True, tree=None, corpusId="SE10T8"):
    if tree == None:
        corpus = ET.Element("corpus", {"source":corpusId})
        tree = ET.ElementTree(corpus)
    else:
        corpus = tree.getroot()
    sentence = None
    for line in lines:
        line = line.strip()
        if sentence == None:
            assert line[0].isdigit(), line
            origId, line = line.split("\t")
            sentence = Sentence(origId, line.strip().strip("\""), corpusId)
        else:
            if line.startswith("Comment:"):
                sentence.comment = line.split(":", 1)[-1].strip()
            elif line != "":
                sentence.relation = line
            else:
                assert sentence != None
                corpus.append(sentence.process(directed=directed))
                sentence = None
    return tree

def convert(inPath, outDir):
    archive = zipfile.ZipFile(inPath, 'r')
    #print archive.namelist()
    f = archive.open("SemEval2010_task8_all_data/SemEval2010_task8_training/TRAIN_FILE.TXT")
    tree = processLines(f.readlines(), "train")
    f.close()
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    ETUtils.write(tree.getroot(), os.path.join(outDir, "SemEval201-Task8-all.xml"))

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None)
    optparser.add_option("-o", "--outdir", default=None, dest="outdir", help="directory for output files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    convert(options.input, options.outdir)