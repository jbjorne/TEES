import sys, os
from FeatureBuilder import FeatureBuilder
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
import Utils.Settings as Settings
import Utils.Download

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
            print >> sys.stderr, "Warning,", synList[0], "already a primary name"
            synDict[synList[0]].extend(synList[1:])
    f.close()
    return synDict

#print readBacsu("/home/jari/data/BioNLP11SharedTask/bacsu-modified.txt")

def readSubtiwiki(filename):
    f = open(filename)
    synDict = {}
    lowerCased = set()
    for line in f:
        line = line.strip()
        synList = line.split(",")
        for i in range(len(synList)):
            synList[i] = synList[i].lower()
        if not synList[0] in synDict:
            synDict[synList[0]] = synList[1:]
        else:
            print >> sys.stderr, "Warning,", synList[0], "already a primary name"
            synDict[synList[0]].extend(synList[1:])
    f.close()
    return synDict

def installRENData(destPath=None, downloadPath=None, redownload=False, updateLocalSettings=False):
    print >> sys.stderr, "---------------", "Downloading TEES data files for REN", "---------------"
    print >> sys.stderr, "These files are derived from UniProt bacsu and SubtiWiki"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "resources")
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "resources/download")
    Utils.Download.downloadAndExtract(Settings.URL["TEES_RESOURCES"], destPath, downloadPath, redownload=redownload)
    Settings.setLocal("TEES_RESOURCES", destPath, updateLocalSettings)


class BacteriaRenamingFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        #self.bacsu = readBacsu(os.path.expanduser("~/data/BioNLP11SharedTask/supporting-tasks/bacsu-modified.txt"))
        #self.subti = readSubtiwiki(os.path.expanduser("~/data/BioNLP11SharedTask/supporting-tasks/Subtiwiki-Synonyms.csv"))
        #self.subti = readSubtiwiki(os.path.expanduser("~/cvs_checkout/JariSandbox/Wiki/subtiwiki/Subtiwiki-Synonyms.csv"))
        if not hasattr(Settings, "TEES_RESOURCES"):
            print >> sys.stderr, "TEES example builder data files not installed, installing now"
            installRENData(updateLocalSettings=True)
        self.bacsu = readBacsu(os.path.join(Settings.TEES_RESOURCES, "bacsu-modified.txt"))
        self.subti = readSubtiwiki(os.path.join(Settings.TEES_RESOURCES, "Subtiwiki-Synonyms.csv"))
        # OR the dictionaries
        self.any = {}
        for key in sorted(list(set(self.bacsu.keys() + self.subti.keys()))):
            self.any[key] = set()
            if self.bacsu.has_key(key):
                for value in self.bacsu[key]: 
                    self.any[key].add(value)
            if self.subti.has_key(key):
                for value in self.subti[key]: 
                    self.any[key].add(value)
            self.any[key] = list(self.any[key])
            self.any[key].sort()
        # AND the dictionaries
        self.all = {}
        for key in sorted(list(set(self.bacsu.keys() + self.subti.keys()))):
            self.all[key] = set()  
            allSynonyms = set()
            bacsuSet = set()
            if self.bacsu.has_key(key):
                bacsuSet = self.bacsu[key]
                for x in bacsuSet: allSynonyms.add(x)
            subtiSet = set()
            if self.subti.has_key(key):
                subtiSet = self.subti[key]
                for x in subtiSet: allSynonyms.add(x)
            for synonym in allSynonyms:
                if synonym in bacsuSet and synonym in subtiSet:
                    self.all[key].add(synonym)
            self.all[key] = list(self.all[key])
            self.all[key].sort()
    
    def buildPairFeatures(self, e1, e2):
        self.buildPairFeaturesDict(e1, e2, self.bacsu, "bacsu")
        self.buildPairFeaturesDict(e1, e2, self.subti, "subti")
        self.buildPairFeaturesDict(e1, e2, self.any, "any")
        self.buildPairFeaturesDict(e1, e2, self.all, "all")
        
    def buildPairFeaturesDict(self, e1, e2, synDict, synTag):
        # build in both directions
        for tag, pair in ( ("frw_", (e1, e2)), ("rev_", (e2, e1)) ):
            e1Text = pair[0].get("text").strip().lower()
            e2Text = pair[1].get("text").strip().lower()
            if synDict.has_key(e1Text):
                if e2Text in synDict[e1Text]:
                    self.setFeature(tag + synTag + "_synonym")
    
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
        