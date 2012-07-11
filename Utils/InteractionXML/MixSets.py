import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import RecalculateIds

def mixSets(input, output, docOrigIds, sourceSet, targetSet):
    print >> sys.stderr, "Mixing Sets", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    if docOrigIds != None:
        for document in corpusRoot.getiterator("document"):
            docId = document.get("pmid")
            if docId == None:
                docId = document.get("origId")
            if docId in docOrigIds:
                assert document.get("set") == sourceSet
                document.set("set", targetSet)
                docOrigIds.remove(docId)
        assert len(docOrigIds) == 0, docOrigIds
    
    sentenceIds = None
    if sentenceIds != None:
        for document in corpusRoot.getiterator("document"):
            removed = []
            for sentence in document.findall("sentence"):
                assert document.get("set") == sourceSet
                sentenceId = sentence.get("id")
                if sentenceId in sentenceIds:
                    removed.append(document.remove(sentence))
                    sentenceIds.remove(sentenceId)
            if len(removed) > 0:
                newDoc = ET.Element("document")
                for attr in document.attrib:
                    newDoc.set(attr, document.get(attr))
                newDoc.set("id", None)
                newDoc.set("set", targetSet)
                for sentence in removed:
                    newDoc.append(sentence)
                corpusRoot.append(newDoc)
        assert len(sentenceIds) == None
    
        RecalculateIds.recalculateIds(corpusTree, onlyWithinSentence=False)
             
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree