import cElementTreeUtils as ETUtils
from collections import defaultdict

def getNestedItems(parent, term, data, preTag):
    items = parent.find(preTag+term+"s").findall(preTag+term)
    for item in items:
        data[term] += item.text
        print "  " + term + ": " + item.text

def loadDrugBank(filename, preTag="{http://drugbank.ca}"):
    data = defaultdict(lambda : defaultdict(list))
    print "Loading XML"
    xml = ETUtils.ETFromObj(filename)
    print "Processing XML"
    root = xml.getroot()
    assert root.tag == preTag+"drugs", root.tag
    for drug in root.findall(preTag+"drug"):
        name = drug.find(preTag+"name").text  
        print name
        assert name not in data
        getNestedItems(drug, "synonym", data[name], preTag)
#        synonyms = drug.find(preTag+"synonyms").findall(preTag+"synonym")
#        for synonym in synonyms:
#            data[name]["synonyms"] += synonym.text
#            print "  S:", synonym.text
        brands = drug.find(preTag+"brands").findall(preTag+"brand")
        for brand in brands:
            data[name]["brands"] += brand.text
            print "  B:", brand.text
        groups = drug.find(preTag+"groups").findall(preTag+"group")
        for group in groups:
            data[name]["groups"] += group.text
            print "  G:", group.text

if __name__=="__main__":
    drugBankFile = "/home/jari/data/DDIExtraction2011/resources/drugbank.xml"
    loadDrugBank(drugBankFile)