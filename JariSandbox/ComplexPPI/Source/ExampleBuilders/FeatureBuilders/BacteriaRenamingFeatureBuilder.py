from FeatureBuilder import FeatureBuilder

# 1) Lowercase bacsu names, there are differences
# 2) Assert matching to bacsu
# 3) Bacsu-order seems to be the same as the former/new order
# Bacsu doesn't have everything
# 4) http://www.subtiwiki.uni-goettingen.de

def readBacsu(filename):
    f = open(filename)
    synDict = {}
    lowerCased = set()
    for line in f:
        if line[0:3] != "BSU":
            continue
        synSplits = line.split()[4:]
        synList = []
        for name in synSplits:
            name = name.replace(";", "")
            name = name.lower()
            synList.append(name)
        if not synList[0] in synDict:
            synDict[synList[0]] = synList[1:]
        else:
            print "Warning,", synList[0], "already a primary name"
            synDict[synList[0]].extend(synList[1:])
    f.close()
    return synDict

#print readBacsu("/home/jari/data/BioNLP11SharedTask/bacsu-modified.txt")

class BacteriaRenamingFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        self.bacsu = readBacsu("/home/jari/data/BioNLP11SharedTask/bacsu-modified.txt")
    
    def buildPairFeatures(self, e1, e2):
        # build in both directions
        for tag, pair in ( ("frw_", (e1, e2)), ("rev_", (e2, e1)) ):
            e1Text = pair[0].get("text").strip().lower()
            e2Text = pair[1].get("text").strip().lower()
            if self.bacsu.has_key(e1Text):
                if e2Text in self.bacsu[e1Text]:
                    self.setFeature(tag + "bacsu_synonym")
    
    def buildSubstringFeatures(self, e1, e2):
        e1Text = e1.get("text").strip().lower()
        e2Text = e2.get("text").strip().lower()
        if e1Text != "":
            e1FirstThreeLetters = e1Text[0:3]
            e1LastLetter = e1Text[-1]
        else:
            e1FirstThreeLetters = "NONE"
            e1LastLetter = "NONE"
        if e2Text != "":
            e2FirstThreeLetters = e2Text[0:3]
            e2LastLetter = e2Text[-1]
        else:
            e2FirstThreeLetters = "NONE"
            e2LastLetter = "NONE"
        self.setFeature("REN_subpair_f3_" + e1FirstThreeLetters + "_" + e2FirstThreeLetters)
        self.setFeature("REN_subpair_l1_" + e1LastLetter + "_" + e2LastLetter)
        