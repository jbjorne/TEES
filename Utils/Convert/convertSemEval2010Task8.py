import sys,os
import re
import zipfile
import shutil
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.MakeSets as MakeSets
from Detectors.Preprocessor import Preprocessor
import Utils.Stream as Stream
import Utils.Settings as Settings
import SemEval2010Task8Tools

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
    
    def mergeType(self, relType, e1, e2):
        return relType + "(" + e1 + "," + e2 + ")"
    
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
        for key in eMap: # Check that e1 == e1 and e2 == e2
            assert eMap[key].get("id").endswith("." + key)
        # Build the sentence
        docElem = ET.Element("document", {"id":self.corpusId + ".d" + self.origId, "set":self.setName})
        sentElem = ET.SubElement(docElem, "sentence", {"id":self.id, "charOffset":"0-"+str(len(self.text)), "text":self.text, "origId":self.origId})
        sentElem.set("relation", self.relation)
        if self.comment != None and self.comment != "":
            sentElem.set("comment", self.comment)
        for entity in self.entities:
            sentElem.append(entity)
        # Determine interaction types per direction
        relFrom, relTo = "", ""
        if self.relation == "Other":
            sentElem.append(self._getInteraction(self.relation, "e1", "e2", directed, 0, eMap, relFrom, relTo))
        else:
            relType, rest = self.relation.strip(")").split("(")
            relFrom, relTo = rest.split(",")
            reverse = (relFrom == "e2" and relTo == "e1")  
            if not reverse:
                assert relFrom == "e1" and relTo == "e2"
                forwardType = self.mergeType(relType, relFrom, relTo) if (negatives == "REVERSE_POS") else relType
                reverseType = self.mergeType(relType, relTo, relFrom) if (negatives == "REVERSE_POS") else "neg"
            else:
                forwardType = self.mergeType(relType, relFrom, relTo) if (negatives == "REVERSE_POS") else "neg"
                reverseType = self.mergeType(relType, relTo, relFrom) if (negatives == "REVERSE_POS") else relType
            # Build the interactions
            if directed:
                if forwardType != "neg" or negatives == "INCLUDE":
                    sentElem.append(self._getInteraction(forwardType, "e1", "e2", directed, 0, eMap, "e1", "e2"))
                if reverseType != "neg" or negatives == "INCLUDE":
                    sentElem.append(self._getInteraction(reverseType, "e2", "e1", directed, 1, eMap, "e2", "e1"))
            else:
                sentElem.append(self._getInteraction(self.relation, "e1", "e2", directed, 0, eMap, relFrom, relTo))
        return docElem
    
    def _getInteraction(self, relType, e1, e2, directed, count, eMap, relFrom=None, relTo=None):
        if relFrom == None: relFrom = e1
        if relTo == None: relFrom = e2
        attrs = {"id":self.id + ".i" + str(count), "type":relType, "directed":str(directed), "e1":eMap[e1].get("id"), "e2":eMap[e2].get("id")}
        if relFrom != "": attrs["from"] = relFrom
        if relTo != "": attrs["to"] = relTo
        return ET.Element("interaction", attrs)
    
    def _getEntity(self, line, tag):
        try:
            before, entityText, after = re.split(r'<' + tag + '>|</' + tag + '>', line)
        except ValueError as e:
            print "ValueError in line '" + line + "' for tag", tag
            raise e
        begin = len(before)
        end = len(before) + len(entityText)
        return ET.Element("entity", {"text":entityText, "type":"entity", "given":"True", "charOffset":str(begin)+"-"+str(end), "id":self.id + "." + tag})
        
def processLines(lines, setName, usedIds, directed=True, negatives="INCLUDE", tree=None, corpusId="SE10T8"):
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

def convert(inPath, outDir, corpusId, directed, negatives, preprocess, preprocessorParameters=None, debug=False, clear=False, constParser="BLLIP-BIO", depParser="STANFORD-CONVERT", logging=True):
    assert negatives in ("INCLUDE", "SKIP", "REVERSE_POS")
    # Download the corpus if needed
    if inPath == None:
        if not hasattr(Settings, "SE10T8_CORPUS"):
            SemEval2010Task8Tools.install()
        inPath = Settings.SE10T8_CORPUS
    assert os.path.exists(inPath)
    # Prepare the output directory
    if not os.path.exists(outDir):
        print "Making output directory", outDir
        os.makedirs(outDir)
    elif clear:
        print "Removing output directory", outDir
        shutil.rmtree(outDir)
    # Start logging
    if logging:
        Stream.openLog(os.path.join(outDir, "log.txt"), clear=clear)
    # Read and process the corpus files
    archive = zipfile.ZipFile(inPath, 'r')
    usedIds = set()
    tree = None
    for fileName, setName in [("SemEval2010_task8_all_data/SemEval2010_task8_training/TRAIN_FILE.TXT", "train"),\
                              ("SemEval2010_task8_all_data/SemEval2010_task8_testing_keys/TEST_FILE_FULL.TXT", "test")]:
        print "Processing file", fileName, "as set", setName
        f = archive.open(fileName)
        tree = processLines(f.readlines(), setName, directed=directed, negatives=negatives, usedIds=usedIds, tree=tree, corpusId=corpusId)
        f.close()
    # Divide the training set into training and development sets
    MakeSets.processCorpus(tree, None, "train", [("train", 0.7), ("devel", 1.0)], 1)
    # Write out the converted corpus
    convertedPath = os.path.join(outDir, corpusId + "-converted.xml")
    ETUtils.write(tree.getroot(), convertedPath)
    # Preprocess the converted corpus
    if preprocess:
        outPath = os.path.join(outDir, corpusId + ".xml")
        preprocessor = Preprocessor(constParser, depParser)
        preprocessor.setArgForAllSteps("debug", debug)
        preprocessor.stepArgs("CONVERT")["corpusName"] = corpusId
        preprocessor.process(convertedPath, outPath, preprocessorParameters, omitSteps=["SPLIT-SENTENCES", "NER", "SPLIT-NAMES"])
    # Stop logging
    if logging:
        Stream.closeLog(os.path.join(outDir, "log.txt"))

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nConvert the SemEval 2010 Task 8 corpus to Interaction XML")
    optparser.add_option("-i", "--corpusPath", default=None, help="Optional path to the corpus zip file (if undefined the corpus will be downloaded)")
    optparser.add_option("-o", "--outdir", default=None, help="Directory for the output files")
    optparser.add_option("-r", "--directed", default=False, action="store_true", help="Generate directed interaction elements")
    optparser.add_option("-n", "--negatives", default="REVERSE_POS", help="Generate negative interactions (used only with the --directed option")
    optparser.add_option("-c", "--corpus", default="SE10T8", help="The name for the converted corpus")
    optparser.add_option("-p", "--preprocess", default=False, action="store_true", help="Run the preprocessor after converting to the Interaction XML format")
    optparser.add_option("--parameters", default=None, help="Preprocessor parameters")
    optparser.add_option("--constParser", default=None, help="Check Preprocessor.py for the available options")
    optparser.add_option("--depParser", default=None, help="Check Preprocessor.py for the available options")
    optparser.add_option("-d", "--debug", default=False, action="store_true", help="Debug mode (preserve intermediate files)")
    optparser.add_option("--clear", default=False, action="store_true", help="Delete the contents of the output directory")
    optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="Do not save a log file")
    (options, args) = optparser.parse_args()
    
    convert(options.corpusPath, options.outdir, directed=options.directed, negatives=options.negatives, 
            preprocess=options.preprocess, preprocessorParameters=options.parameters, corpusId=options.corpus,
            constParser=options.constParser, depParser=options.depParser, 
            debug=options.debug, clear=options.clear, logging=not options.noLog)