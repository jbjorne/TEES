import sys,os
import re
import zipfile
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import xml.etree.ElementTree as ET
import Utils.ElementTreeUtils as ETUtils

class Sentence():
    def __init__(self, origId, text, corpusId, usedIds, setName):
        self.origId = origId
        self.corpusId = corpusId
        self.id = corpusId + ".d" + origId + ".s" + origId
        assert self.id not in usedIds
        usedIds.add(self.id)
        self.text = text
        self.entities = []
        self.relation = None
        self.comment = None
        self.setName = setName
    
    def process(self, directed, negatives):
        # Build the entities
        for tag in ("e1", "e2"):
            self.entities.append(self._getEntity(self.text, tag))
            self.text = self.text.replace("<" + tag + ">", "").replace("</" + tag + ">", "")
        # Check entity offsets
        for entity in self.entities:
            begin, end = [int(x) for x in entity.get("charOffset").split("-")]
            assert entity.get("text") == self.text[begin:end], (entity.get("text"), self.text, self.text[begin:end], [begin, end])
        assert len(self.entities) == 2
        eMap = {"e1":self.entities[0], "e2":self.entities[1]}
        for key in eMap:
            assert eMap[key].get("id").endswith("." + key)
        # Build the sentence
        docElem = ET.Element("document", {"id":self.corpusId + ".d" + self.origId, "set":self.setName})
        sentElem = ET.SubElement(docElem, "sentence", {"id":self.id, "charOffset":"0-"+str(len(self.text)), "text":self.text})
        if self.comment != None and self.comment != "":
            sentElem.set("comment", self.comment)
        for entity in self.entities:
            sentElem.append(entity)
        # Build the interactions
        relFrom = None
        relTo = None
        if self.relation == "Other":
            relType = "Other"
        else:
            relType, rest = self.relation.strip(")").split("(")
            relFrom, relTo = rest.split(",")
        if directed:
            if relType == "Other":
                ET.SubElement(sentElem, "interaction", {"id":self.id + ".i0", "type":relType, "directed":"True", "e1":eMap["e1"].get("id"), "e2":eMap["e2"].get("id")})
                ET.SubElement(sentElem, "interaction", {"id":self.id + ".i0", "type":relType, "directed":"True", "e1":eMap["e2"].get("id"), "e2":eMap["e1"].get("id")})
            else:
                ET.SubElement(sentElem, "interaction", {"id":self.id + ".i0", "type":relType, "directed":"True", "e1":eMap[relFrom].get("id"), "e2":eMap[relTo].get("id")})
                if negatives:
                    ET.SubElement(sentElem, "interaction", {"id":self.id + ".i0", "type":"neg", "directed":"True", "e1":eMap[relTo].get("id"), "e2":eMap[relFrom].get("id")})                
        else:
            if relType == "Other":
                ET.SubElement(sentElem, "interaction", {"id":self.id + ".i0", "type":relType, "directed":"False", "e1":eMap["e1"].get("id"), "e2":eMap["e2"].get("id")})
            else:
                ET.SubElement(sentElem, "interaction", {"id":self.id + ".i0", "type":relType + "(" + relFrom + "," + relTo + ")", "directed":"False", "e1":eMap["e1"].get("id"), "e2":eMap["e2"].get("id"), "from":relFrom, "to":relTo})
        return docElem
    
    def _getEntity(self, line, tag):
        try:
            before, entityText, after = re.split(r'<' + tag + '>|</' + tag + '>', line)
        except ValueError as e:
            print "ValueError in line '" + line + "' for tag", tag
            raise e
        begin = len(before)
        end = len(before) + len(entityText)
        return ET.Element("entity", {"text":entityText, "type":"entity", "charOffset":str(begin)+"-"+str(end), "id":self.id + "." + tag})
        
def processLines(lines, setName, usedIds, directed=True, negatives=False, tree=None, corpusId="SE10T8"):
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
            sentence = Sentence(origId, line.strip().strip("\""), corpusId, usedIds, setName)
        else:
            if line.startswith("Comment:"):
                sentence.comment = line.split(":", 1)[-1].strip()
            elif line != "":
                sentence.relation = line
            else:
                assert sentence != None
                corpus.append(sentence.process(directed=directed, negatives=negatives))
                sentence = None
    return tree

def convert(inPath, outDir, directed, negatives):
    archive = zipfile.ZipFile(inPath, 'r')
    #print archive.namelist()
    usedIds = set()
    tree = None
    for fileName, setName in [("SemEval2010_task8_all_data/SemEval2010_task8_training/TRAIN_FILE.TXT", "train"),\
                              ("SemEval2010_task8_all_data/SemEval2010_task8_testing_keys/TEST_FILE_FULL.TXT", "test")]:
        print "Processing file", fileName, "as set", setName
        f = archive.open(fileName)
        tree = processLines(f.readlines(), setName, directed=directed, negatives=negatives, usedIds=usedIds, tree=tree)
        f.close()
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    ETUtils.write(tree.getroot(), os.path.join(outDir, "SemEval201-Task8-all.xml"))

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None)
    optparser.add_option("-o", "--outdir", default=None, dest="outdir", help="directory for output files")
    optparser.add_option("--debug", default=False, action="store_true", help="")
    optparser.add_option("--directed", default=False, action="store_true", help="")
    optparser.add_option("--negatives", default=False, action="store_true", help="")
    (options, args) = optparser.parse_args()
    
    convert(options.input, options.outdir, options.directed, options.negatives)