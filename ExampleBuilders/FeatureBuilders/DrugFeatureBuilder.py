import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilder import FeatureBuilder
import Utils.Settings as Settings
import Utils.Download
import Utils.ElementTreeUtils as ETUtils
from collections import defaultdict

def installDrugBank(destPath=None, downloadPath=None, redownload=False, updateLocalSettings=False):
    print >> sys.stderr, "---------------", "Downloading Drug Bank XML", "---------------"
    print >> sys.stderr, "See http://www.drugbank.ca/downloads for conditions of use"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "resources")
    if downloadPath == None:
        downloadPath = os.path.join(Settings.DATAPATH, "resources/download")
    filenames = Utils.Download.downloadAndExtract(Settings.URL["DRUG_BANK_XML"], destPath, downloadPath, redownload=redownload)
    assert len(filenames) == 1
    Settings.setLocal("DRUG_BANK_XML", os.path.join(destPath, filenames[0]), updateLocalSettings)

class DrugFeatureBuilder(FeatureBuilder):
    data = None
    
    def __init__(self, featureSet=None):
        FeatureBuilder.__init__(self, featureSet)
        if not hasattr(Settings, "DRUG_BANK_XML"):
            print >> sys.stderr, "Drug Bank XML not installed, installing now"
            installDrugBank(updateLocalSettings=True)
        drugBankFile = Settings.DRUG_BANK_XML
        #drugBankFile = "/home/jari/data/DDIExtraction2011/resources/drugbank.xml"
        # Load drug data into memory on first call to constructor
        if DrugFeatureBuilder.data == None:
            DrugFeatureBuilder.data, DrugFeatureBuilder.nameToId = prepareDrugBank(drugBankFile)
            
            DrugFeatureBuilder.tokenToId = {}
            for name in DrugFeatureBuilder.nameToId:
                splits = name.split()
                if len(splits) < 2:
                    continue
                for split in splits:
                    if split not in DrugFeatureBuilder.tokenToId:
                        DrugFeatureBuilder.tokenToId[split] = []
                    DrugFeatureBuilder.tokenToId[split].extend(DrugFeatureBuilder.nameToId[name])
            for token in DrugFeatureBuilder.tokenToId:
                DrugFeatureBuilder.tokenToId[token] = sorted(list(set(DrugFeatureBuilder.tokenToId[token])))
            
            DrugFeatureBuilder.interactionPairs = buildInteractionPairs(DrugFeatureBuilder.data)
    
    def buildDrugFeatures(self, token):
        norText = normalizeDrugName(token.get("text"))
        drugs = self.getDrugs(token.get("text"))
        tokenDrugs = self.getDrugs(token.get("text"), True)
        
        for drugList, tag in [(drugs, ""), (tokenDrugs, "_token")]:
            if len(drugList) > 0:
                self.setFeature("DrugBank_match" + tag)
            else:
                self.setFeature("DrugBank_noMatch" + tag)
            for drug in drugList:
                for category in drug:
                    if category == "interaction":
                        continue
                    values = drug[category]
                    if isinstance(values, basestring):
                        values = [values]
                    for value in values:
                        value = value.replace(" ", "-").replace("\n", "-")
                        self.setFeature("DrugBank_" + category + "_" + value + tag)
                        norValue = normalizeDrugName(value)
                        self.setFeature("DrugBank_nor_" + category + "_" + value + tag)
                        if norText == norValue:
                            self.setFeature("DrugBank_equalsValueInCategory_" + category + tag)
                            self.setFeature("DrugBank_equalsValue_" + norValue  + "_InCategory_" + category + tag)
    
    def buildPairFeatures(self, e1, e2):
        e1Name = normalizeDrugName(e1.get("text"))
        e2Name = normalizeDrugName(e2.get("text"))
        interactionType = self.getInteraction(e1Name, e2Name)
        if self.getInteraction(e1Name, e2Name) == True:
            self.setFeature("DrugBankPairTrueInt")
        else:
            self.setFeature("NotDrugInteraction")
            if interactionType == "UNKNOWN_NAME":
                self.setFeature("PairNotInDrugBank")
            else:
                self.setFeature("DrugBankPairFalseInt")
    
    def getMTMXAttrs(self, e1, e2, attr):
        rv = [str(e1.get(attr)).lower().replace(" ", ""), str(e2.get(attr)).lower().replace(" ", "")]
        if rv[0] == "": rv[0] = "none"
        if rv[1] == "": rv[1] = "none"
        rv.sort()
        return rv
        
    def buildMTMXFeatures(self, e1, e2):
        names = self.getMTMXAttrs(e1, e2, "mtmxName")
        self.setFeature("mtmxNames-" + "-".join(names))
        if names[0] == names[1]:
            if names[0] in ["", "none"]:
                self.setFeature("mtmxNames-both_unknown")
            else:
                self.setFeature("mtmxNames-both_identical")
        self.setFeature("mtmxShortNames-" + "-".join(self.getMTMXAttrs(e1, e2, "mtmxNameShort")))
        mtmxCuis = self.getMTMXAttrs(e1, e2, "mtmxCui")
        for mtmxCui in mtmxCuis:
            self.setFeature("mtmxCui_" + mtmxCui)
        self.setFeature("mtmxCuis-" + "-".join(mtmxCuis))
        # Probabilities
        rv = self.getMTMXAttrs(e1, e2, "mtmxProb")
        if rv[0] in ["", "none"]: rv[0] = "0"
        if rv[1] in ["", "none"]: rv[1] = "0"
        rv[0] = int(rv[0])
        rv[1] = int(rv[1])
        assert rv[0] <= 1000 and rv[1] <= 1000, (rv[0], rv[1])
        rv.sort()
        self.setFeature("mtmxProbMin", float(rv[0]) / 1000.0)
        self.setFeature("mtmxProbMax", float(rv[1]) / 1000.0)
        # Semtypes
        sem = self.getMTMXAttrs(e1, e2, "mtmxSemTypes")
        #print sem
        for i in sem[0].split(","):
            for j in sem[1].split(","):
                semPair = [i, j]
                semPair.sort()
                #print "semPair", semPair
                self.setFeature("semPair-" + "-".join(semPair))
                self.setFeature("semType-" + i)
                self.setFeature("semType-" + j)
    
    def getInteraction(self, e1Name, e2Name):
        e1Name = normalizeDrugName(e1Name)
        e2Name = normalizeDrugName(e2Name)
        e1Ids = DrugFeatureBuilder.nameToId[e1Name]
        e2Ids = DrugFeatureBuilder.nameToId[e2Name]
        #print e1Ids, e2Ids
        if len(e1Ids) == 0 or len(e2Ids) == 0:
            return "UNKNOWN_NAME" # unknown drug name
        for id1 in e1Ids:
            for id2 in e2Ids:
                if DrugFeatureBuilder.interactionPairs[id1][id2]:
                    return True
        return False
    
    def getDrugs(self, name, isToken=False):
        name = normalizeDrugName(name)
        if isToken:
            nameToId = DrugFeatureBuilder.nameToId
        else:
            nameToId = DrugFeatureBuilder.tokenToId
            
        if name not in nameToId:
            return []
        
        datas = []
        for id in nameToId[name]:
            datas.append(DrugFeatureBuilder.data[id])
        return datas

def normalizeDrugName(text):
    return text.replace("-","").replace("/","").replace(",","").replace("\\","").replace(" ","").lower()

def getNestedItems(parent, term, data, preTag, termPlural=None, verbose=False):
    if termPlural != None:
        items = parent.find(preTag+termPlural).findall(preTag+term)
    else:
        items = parent.find(preTag+term+"s").findall(preTag+term)
    for item in items:
        data[term].append(item.text)
        if verbose: print "  " + term + ": " + item.text
        
def resolveInteractions(data, verbose=False):
    counts = defaultdict(int)
    if verbose: print "Resolving Interactions"
    for id in data:
        if verbose: print id, data[id]["name"]
        for interaction in data[id]["interaction"]:
            partnerDBId = str(interaction[0])
            #partnerDBId = "DB" + (5 - len(partnerDBId)) * "0" + partnerDBId
            interaction[0] = partnerDBId
            if partnerDBId in data:
                interaction[1] = data[partnerDBId]["name"]
                counts["found-partner-ids"] += 1
            else:
                counts["missing-partner-ids"] += 1
            if verbose: print "  ", interaction
    #if verbose: 
    print >> sys.stderr, "Interaction resolution counts:", counts

def buildInteractionPairs(data):
    intPairs = defaultdict(lambda : defaultdict(lambda: False))
    for id in data:
        for interaction in data[id]["interaction"]:
            if interaction[1] != None:
                intPairs[id][interaction[0]] = True
                intPairs[interaction[0]][id] = True
    return intPairs
    
def mapNamesToIds(data, normalize=True, verbose=False):
    counts = defaultdict(int)
    nameToId = defaultdict(list)
    for id in sorted(data.keys()):
        for name in [data[id]["name"]] + data[id]["synonym"] + data[id]["brand"]:
            #assert name not in nameToId, name
            if normalize:
                name = normalizeDrugName(name)
            if id not in nameToId[name]:
                nameToId[name].append(id)
    # count
    for name in nameToId:
        counts[len(nameToId[name])] += 1
        if len(nameToId[name]) > 2:
            if verbose: print "Multiple ids:", len(nameToId[name]), name, nameToId[name]
    if verbose: print "Name to id:", counts
    return nameToId

def loadDrugBank(filename, preTag="{http://drugbank.ca}", verbose=False):
    data = defaultdict(lambda : defaultdict(list))
    print "Loading DrugBank XML from", filename
    xml = ETUtils.ETFromObj(filename)
    print "Processing DrugBank XML"
    root = xml.getroot()
    assert root.tag == preTag+"drugs", root.tag
    for drug in root.findall(preTag+"drug"):
        id = drug.find(preTag+"drugbank-id").text
        name = drug.find(preTag+"name").text
        if verbose: print id, name
        assert id not in data
        data[id]["name"] = name
        data[id]["id"] = id
        # TODO: Enzymes & targets
        # TODO: hydrophobicity
        getNestedItems(drug, "synonym", data[id], preTag)
        getNestedItems(drug, "brand", data[id], preTag)
        getNestedItems(drug, "group", data[id], preTag)
        getNestedItems(drug, "category", data[id], preTag, "categories")
        interactions = drug.find(preTag+"drug-interactions").findall(preTag+"drug-interaction")
        for interaction in interactions:
            data[id]["interaction"].append( [interaction.find(preTag+"drug").text, interaction.find(preTag+"name").text, interaction.find(preTag+"description").text,] )
    return data

def prepareDrugBank(drugBankFile):
    data = loadDrugBank(drugBankFile)
    resolveInteractions(data)
    nameToId = mapNamesToIds(data)
    return data, nameToId

if __name__=="__main__":
#    drugBankFile = "/home/jari/data/DDIExtraction2011/resources/drugbank.xml"
#    data = loadDrugBank(drugBankFile, verbose=True)
#    nameToId = mapNamesToIds(data, verbose=True)
#    #print nameToId
#    #resolveInteractions(data)
    f = DrugFeatureBuilder()
    print "A:", f.getDrug("Lepirudin")
    print "B:", f.getDrug("Refludan")
    print "C:", f.getDrug("Treprostinil")
    #print f.interactionPairs
    print "1:", f.getInteraction("Refludan", "Treprostinil")
    print "2:", f.getInteraction("Refludan", "TreprostinilBlahBlah")
    print "3:", f.getInteraction("Refludan", "[4-({5-(AMINOCARBONYL)-4-[(3-METHYLPHENYL)AMINO]PYRIMIDIN-2-YL}AMINO)PHENYL]ACETIC ACID")
    
    