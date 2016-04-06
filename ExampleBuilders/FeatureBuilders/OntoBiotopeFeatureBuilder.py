from FeatureBuilder import FeatureBuilder

class Term():
    def __init__(self, identifier=None, name=None, parents=None, children=None):
        self.id = identifier
        self.name = name
        self.parents = parents
        #self.children = children

class OntoBiotopeFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        self.terms = {}
        self.byName = {}
        self.byKeyword = {}
    
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
            if keyword not in self.byKeyword[keyword]:
                self.byKeyword[keyword] = set()
            self.byKeyword[keyword].add(term)
    
    def prepareTerms(self):
        for term in sorted(self.terms.keys()):
            term.parents = [self.terms[x] for x in term.parents]
        for key in self.byName:
            self.byName[key] = sorted(self.byName[key], key=lambda x: x.id)
        for key in self.byKeyword:
            self.byKeyword[key] = sorted(self.byKeyword[key], key=lambda x: x.id)
    
    def loadOBO(self, oboPath):
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
                tag, content = [x.strip() for x in line.split(":", maxsplits=1)]
                if tag == "id":
                    term.id = content
                elif tag == "name":
                    term.name = content
                if tag == "is_a":
                    parentId = content.split("!")
                    parentId = parentId.strip()
                    term.parents.append(parentId)
        self.addTerm(term)
        self.prepareTerms()