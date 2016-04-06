from FeatureBuilder import FeatureBuilder
import sys, os

class Term():
    def __init__(self, identifier=None, name=None):
        self.id = identifier
        self.name = name
        self.fullId = None
        self.parents = []
        #self.children = children

class OntoBiotopeFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        self.terms = {}
        self.byName = {}
        self.byKeyword = {}
        self.loadOBO(os.path.join(os.path.dirname(os.path.abspath(__file__)), "OntoBiotope_BioNLP-ST-2016.obo"))
    
    def getParents(self, name):
        terms = []
        if name:
            terms += self.byName.get(name, [])
        for keyword in name.split():
            terms += self.byKeyword.get(keyword, [])
        terms = sorted(set(terms), key=lambda x: x.id)
        visited = set()
        while terms:
            for term in terms:
                visited.add(term)
            parents = []
            for term in terms:
                parents.extend(term.parents)
            parents = sorted(set(parents), key=lambda x: x.id)
            terms = [x for x in parents if x not in visited]
        return sorted(visited, key=lambda x: x.id)
    
    def getOBOFeaturesForEntity(self, entity, tag):
        names = []
        if entity.get("type") in ("Geographical", "Habitat"):
            terms = self.getParents(entity.get("text").lower())
            for term in terms:
                names.append("OBO-" + tag + term.fullId)
                #print term.id, term.name
                #self.features[self.featureSet.getId(tag + term.fullId)] = 1
        return names
    
    def buildOBOFeaturesForEntityPair(self, e1, e2):
        e1Names = self.getOBOFeaturesForEntity(e1, "e1_")
        e2Names = self.getOBOFeaturesForEntity(e2, "e2_")
        for name in e1Names + e2Names:
            self.features[self.featureSet.getId(name)] = 1
        for e1Name in e1Names:
            for e2Name in e2Names:
                self.features[self.featureSet.getId(e1Name + "__" + e2Name)] = 1
    
    def buildOBOFeaturesForToken(self, token, tag=""):
        terms = self.getParents(token.get("text").lower())
        if len(terms) > 0:
            self.features[self.featureSet.getId("OntoBiotope_match")] = 1
        for term in terms:
            self.features[self.featureSet.getId(tag + term.fullId)] = 1
    
    ###########################################################################
    # OBO Loading
    ###########################################################################    
    
    def addTerm(self, term):
        assert term.id not in self.terms
        self.terms[term.id] = term
        if term.name not in self.byName:
            self.byName[term.name] = set()
        self.byName[term.name].add(term)
        for keyword in term.name.split():
            if keyword not in self.byKeyword:
                self.byKeyword[keyword] = set()
            self.byKeyword[keyword].add(term)
    
    def prepareTerms(self):
        for key in sorted(self.terms.keys()):
            term = self.terms[key]
            term.fullId = term.id + "_" + "_".join(term.name.split())
            term.parents = [self.terms[x] for x in term.parents]
        for key in self.byName:
            self.byName[key] = sorted(self.byName[key], key=lambda x: x.id)
        for key in self.byKeyword:
            self.byKeyword[key] = sorted(self.byKeyword[key], key=lambda x: x.id)
    
    def loadOBO(self, oboPath):
        print >> sys.stderr, "Loading OBO from", oboPath
        f = open(oboPath, "rt")
        lines = f.readlines()
        f.close()
        term = None
        for line in lines:
            line = line.strip()
            if line == "[Term]":
                if term:
                    self.addTerm(term)
                term = Term()
            elif ":" in line:
                tag, content = [x.strip() for x in line.split(":", 1)]
                if tag == "id":
                    term.id = content
                elif tag == "name":
                    term.name = content.lower()
                if tag == "is_a":
                    term.parents.append(content.split("!")[0].strip())
        self.addTerm(term)
        self.prepareTerms()