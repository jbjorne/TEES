try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import sys,os
from optparse import OptionParser

def getCorpus(filename):
    corpusTree = ETUtils.ETFromObj(filename)
    corpusRoot = corpusTree.getroot()
    return corpusRoot

def insertTask2(inputfile, task2file, outputfile):
    print >> sys.stderr, "Adding task2 information from", task2file, "to", inputfile, "and saving to", outputfile
    t2Root = getCorpus(task2file)
    noT2Root = getCorpus(inputfile)
    
    sentMap = {}
    for sentence in t2Root.getiterator("sentence"):
        sentMap[sentence.get("id")] = sentence
    
    for sentence in noT2Root.getiterator("sentence"):
        for entity in sentMap[sentence.get("id")].findall("entity"):
            sentence.append(entity)
        for interaction in sentMap[sentence.get("id")].findall("interaction"):
            sentence.append(interaction)
    
    ETUtils.write(noT2Root, outputfile)

def extractTask2(inputfile, outputfile, inverse):
    if inverse:
        print >> sys.stderr, "Extracting task2 information from", inputfile, "to", outputfile
    else:
        print >> sys.stderr, "Removing task2 information from", inputfile, "and saving to", outputfile
    corpusRoot = getCorpus(inputfile)
    for sentence in corpusRoot.getiterator("sentence"):
        task2EntityIds = set()
        if not inverse:
            for entity in sentence.findall("entity"):
                if entity.get("type") == "Entity":
                    task2EntityIds.add(entity.get("id"))
                if entity.get("type") in ["Entity", "neg"]:
                    sentence.remove(entity)
            for interaction in sentence.findall("interaction"):
                if interaction.get("type") in ["Site","CSite","AtLoc","ToLoc","neg"]:
                    sentence.remove(interaction)
                elif interaction.get("e1") in task2EntityIds or interaction.get("e2") in task2EntityIds:
                    sentence.remove(interaction) # remove Theme/Cause interactions referring to t2 entities
        else:
            for entity in sentence.findall("entity"):
                if entity.get("type") == "Entity":
                    task2EntityIds.add(entity.get("id"))
                if entity.get("type") != "Entity":
                    sentence.remove(entity)
            for interaction in sentence.findall("interaction"):
                if interaction.get("type") not in ["Site","CSite","AtLoc","ToLoc"]:
                    sentence.remove(interaction)
            analysesElement = sentence.find("sentenceanalyses")
            if analysesElement != None:
                sentence.remove(analysesElement)

    ETUtils.write(corpusRoot, outputfile)

def run(input, output, task2, mode):
    if mode == "extract":
        extractTask2(input, task2, False)
        extractTask2(input, output, True)
    elif mode == "insert":
        insertTask2(input, task2, output)
    else:
        assert False

if __name__=="__main__":
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-t", "--task2", default=None, dest="task2", help="task2 elements", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output xml", metavar="FILE")
    optparser.add_option("-m", "--mode", default=None, dest="mode", help="extract or insert")
    (options, args) = optparser.parse_args()
    
    run( options.input, options.output, options.task2, options.mode )