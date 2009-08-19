try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import sys,os

try:
    import psyco
    psyco.full()
    print >> sys.stderr, "Found Psyco, using"
except ImportError:
    print >> sys.stderr, "Psyco not installed"

assert(os.path.exists(sys.argv[1]))
corpusTree = ETUtils.ETFromObj(sys.argv[1])
corpusRoot = corpusTree.getroot()

resultRoot = ET.Element("root")
specElement = ET.Element("speculation")
resultRoot.append(specElement)
negElement = ET.Element("negation")
resultRoot.append(negElement)

for sentence in corpusRoot.getiterator("sentence"):
    inSpec = False
    inNeg = False
    for entity in sentence.findall("entity"):
        if entity.get("speculation") == "True" and not inSpec:
            specElement.append(sentence)
            inSpec = True
        if entity.get("negation") == "True" and not inNeg:
            negElement.append(sentence)
            inNeg = True
        if inSpec and inNeg:
            break

ETUtils.write(resultRoot, sys.argv[2])