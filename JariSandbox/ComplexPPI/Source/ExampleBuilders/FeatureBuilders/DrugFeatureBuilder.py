import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
from Core.IdSet import IdSet
import Core.ExampleBuilder
import Core.ExampleUtils as ExampleUtils
from FeatureBuilder import FeatureBuilder

import cElementTreeUtils as ETUtils
from collections import defaultdict

class DrugFeatureBuilder(FeatureBuilder):
    data = None
    
    def __init__(self, featureSet=None):
        FeatureBuilder.__init__(self, featureSet)
        drugBankFile = "/home/jari/data/DDIExtraction2011/resources/drugbank.xml"
        # Load drug data into memory on first call to constructor
        if DrugFeatureBuilder.data == None:
            DrugFeatureBuilder.data, DrugFeatureBuilder.nameToId = prepareDrugBank(drugBankFile)
            DrugFeatureBuilder.interactionPairs = buildInteractionPairs(DrugFeatureBuilder.data)
    
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
            partnerDBId = "DB" + (5 - len(partnerDBId)) * "0" + partnerDBId
            interaction[0] = partnerDBId
            if partnerDBId in data:
                interaction[1] = data[partnerDBId]["name"]
                counts["found-partner-ids"] += 1
            else:
                counts["missing-partner-ids"] += 1
            if verbose: print "  ", interaction
    if verbose: print "Interaction resolution counts:", counts

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
    print "Loading DrugBank XML"
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
        # TODO: Enzymes & targets
        getNestedItems(drug, "synonym", data[id], preTag)
        getNestedItems(drug, "brand", data[id], preTag)
        getNestedItems(drug, "group", data[id], preTag)
        getNestedItems(drug, "category", data[id], preTag, "categories")
        interactions = drug.find(preTag+"drug-interactions").findall(preTag+"drug-interaction")
        for interaction in interactions:
            data[id]["interaction"].append( [interaction.find(preTag+"drug").text, None, interaction.find(preTag+"description").text,] )
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
    #print f.interactionPairs
    print "1:", f.getInteraction("Refludan", "Treprostinil")
    print "2:", f.getInteraction("Refludan", "TreprostinilBlahBlah")
    print "3:", f.getInteraction("Refludan", "[4-({5-(AMINOCARBONYL)-4-[(3-METHYLPHENYL)AMINO]PYRIMIDIN-2-YL}AMINO)PHENYL]ACETIC ACID")
    
    