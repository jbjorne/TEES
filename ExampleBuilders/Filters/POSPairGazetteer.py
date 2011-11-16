import sys, os
import types
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Core.SentenceGraph as SentenceGraph

class POSPairGazetteer:
    def __init__(self, loadFrom=None, buildFrom=None, parse=None, tokenization=None):
        self.counts = {} # hashable -> class -> count
        self.negFractions = {} # hashable -> negative fraction
        
        assert loadFrom == None or buildFrom == None
        if buildFrom != None:
            self.build(buildFrom, parse, tokenization)
        if loadFrom != None:
            self.read(loadFrom)
    
    def build(self, corpus, parse, tokenization=None):
        assert corpus != None
        if type(corpus) == types.StringType or isinstance(corpus, ET.ElementTree): # corpus is in file
            corpus = SentenceGraph.loadCorpus(corpus, parse, tokenization)
        
        for sentence in corpus.sentences:
            sentenceGraph = sentence.sentenceGraph
            if sentenceGraph == None:
                continue
            for t1 in sentenceGraph.tokens:
                for t2 in sentenceGraph.tokens:
                    posTuple = ( t1.get("POS"), t2.get("POS") )
                    if not self.counts.has_key(posTuple):
                        self.counts[posTuple] = {}
                    if sentenceGraph.interactionGraph.has_edge(t1, t2):
                        intEdges = sentenceGraph.interactionGraph.get_edge_data(t1, t2, default={})
                        for i in range(len(intEdges)):
                            intElement = intEdges[i]["element"]
                            intType = intElement.get("type")
                            if not self.counts[posTuple].has_key(intType):
                                self.counts[posTuple][intType] = 0
                            self.counts[posTuple][intType] += 1
                    else:
                        if not self.counts[posTuple].has_key("neg"):
                            self.counts[posTuple]["neg"] = 0
                        self.counts[posTuple]["neg"] += 1
        self.update()
    
    def update(self):
        self.negFractions = {}
        for item, classes in self.counts.iteritems():
            assert sum(classes.values()) > 0, (item, classes)
            self.negFractions[item] = classes.get("neg", 0) / float(sum(classes.values()))
    
    def getNegFrac(self, item):
        if not self.negFractions.has_key(item):
            return 0.0
        return self.negFractions[item]
    
    def write(self, filename):
        f = open(filename, "wt")
        for item in sorted(self.counts.keys()):
            f.write(str(item) + " :::")
            for className in sorted(self.counts[item].keys()):
                f.write(" " + className + ":" + str(self.counts[item][className]))
            f.write("\n")
        f.close()
    
    def clear(self):
        self.counts = {}
        self.negFractions = None
    
    def read(self, filename):
        print "Loading gazetteer from", filename
        self.clear()
        f = open(filename, "rt")
        for line in f:
            itemStr, countStrings = line.split(":::")
            exec "item = " + itemStr
            self.counts[item] = {}
            for countStr in countStrings.split():
                className, numberStr = countStr.split(":")
                self.counts[item][className] = int(numberStr)
            assert len(self.counts[item]) > 0
        f.close()
        self.update()

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    import random

    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-c", "--corpus", default=None, dest="corpus", help="")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file")
    optparser.add_option("-r", "--runTests", default=False, action="store_true", dest="runTests", help="")
    (options, args) = optparser.parse_args()
    
    assert options.input == None or options.corpus == None
    g = POSPairGazetteer(options.input, options.corpus, options.parse, options.tokenization)
    
    if options.runTests:
        print "Items:", len(g.counts)
        r = random.Random(15)
        print "Accessing items:"
        items = sorted(g.counts.keys())
        for i in range(10):
            itemIndex = r.randint(0, len(g.counts)-1)
            item = items[itemIndex] 
            print itemIndex, item, ":", g.getNegFrac(item)
        #print g.getNegFrac(('JJ', 'NN'))
        print "Non-existing item:"
        itemName = "Non-existing item"
        print itemName, ":", g.getNegFrac(itemName)
    
    if options.output != None:
        g.write(options.output)
 