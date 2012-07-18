import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
import Utils.ElementTreeUtils as ETUtils
import Core.Split
import shutil

def makeSubset(input, output=None, ratio=1.0, seed=0):
    if ratio == 1.0:
        if output != None:
            shutil.copy2(input, output)
            return output
        else:
            return input
    totalFolds = 100
    selectedFolds = int(ratio * 100.0)
    print >> sys.stderr, "====== Making subset ======"
    print >> sys.stderr, "Subset for ", input, "ratio", ratio, "seed", seed
    xml = ETUtils.ETFromObj(input).getroot()
    count = 0
    sentCount = 0
    for document in xml.findall("document"):
        sentCount += len(document.findall("sentence"))
        count += 1
    division = Core.Split.getFolds(count, totalFolds, seed)
    #print division, selectedFolds - 1
    index = 0
    removeCount = 0
    sentRemoveCount = 0
    for document in xml.findall("document"):
        if division[index] > selectedFolds - 1:
            xml.remove(document)
            sentRemoveCount += len(document.findall("sentence"))
            removeCount += 1
        index += 1
    print >> sys.stderr, "Subset", "doc:", count, "removed:", removeCount, "sent:", sentCount, "sentremoved:", sentRemoveCount
    xml.set("subsetRatio", str(ratio))
    xml.set("subsetSeed", str(seed))
    if output != None:
        ETUtils.write(xml, output)
    return output

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Making subset #####"
    
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input interaction XML file")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output interaction XML file")
    optparser.add_option("-f", "--fraction", default=1.0, type="float", dest="fraction", help="")
    optparser.add_option("-s", "--seed", default=1, type="int", dest="seed", help="")
    (options, args) = optparser.parse_args()
    
    makeSubset(options.input, options.output, options.fraction, options.seed)