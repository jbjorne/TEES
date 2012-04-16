from FeatureBuilder import FeatureBuilder

# Amino acids from http://www.bio.davidson.edu/courses/genomics/jmol/aatable.html
#amino acid     three letter code     single letter code

subcomponent = set(["region", "promoter", "upstream", "fragment", "site",
              "sequence", "segment", "repeat", "repeat", "element",
              "duplication", "exon", "downstream", "terminus", "motif",
              "frame", "carboxy-terminus", "domain", "subunit", "codon",
              "promoter", "enhancer", "locus", "ltr", "helix-loop-helix",
              "zinc-finger", "portion", "residue", "box", "intron"])

supergroup = set(["complex", "family", "octamer", "microtubule"])

aminoAcids = [
    #nonpolar (hydrophobic)
    ("glycine", "gly", "g", "nonpolar", "neutral"), 
    ("alanine", "ala", "a", "nonpolar", "neutral"),
    ("valine", "val", "v", "nonpolar", "neutral"),
    ("leucine", "leu", "l", "nonpolar", "neutral"),
    ("isoleucine", "ile", "i", "nonpolar", "neutral"),
    ("methionine", "met", "m", "nonpolar", "neutral"),
    ("phenylalanine", "phe", "f", "nonpolar", "neutral"),
    ("tryptophan", "trp", "w", "nonpolar", "neutral"),
    ("proline", "pro", "p", "nonpolar", "neutral"), 
    #polar (hydrophilic)
    ("serine", "ser", "s", "hydrophilic", "neutral"),
    ("threonine", "thr", "t", "hydrophilic", "neutral"),
    ("cysteine", "cys", "c", "hydrophilic", "neutral"),
    ("tyrosine", "tyr", "y", "hydrophilic", "neutral"),
    ("asparagine", "asn", "n", "hydrophilic", "neutral"),
    ("glutamine", "gln", "q", "hydrophilic", "neutral"),
    #electrically charged (negative and hydrophilic)
    ("aspartic acid", "asp", "d", "hydrophilic", "negative"),
    ("glutamic acid", "glu", "e", "hydrophilic", "negative"),
    #electrically charged (positive and hydrophilic)
    ("lysine", "lys", "k", "hydrophilic", "positive"),
    ("arginine", "arg", "r", "hydrophilic", "positive"),
    ("histidine", "his", "h", "hydrophilic", "positive")]

class RELFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        #self.noAnnType = False
        #self.edgeTypesForFeatures = []
        #self.useNonNameEntities = False

    def findAminoAcid(self, string):
        global aminoAcids
    
        string = string.lower()
        for aa in aminoAcids:
            word = string.find(aa[0])
            if word != -1:
                return word, aa
            else:
                tlc = string.find(aa[1]) # three letter code
                if tlc != -1:
                    # Three letter code must not be a part of a word (where it could be just a substring)
                    if (tlc == 0 or not string[tlc-1].isalpha()) and (tlc + 3 >= len(string) or not string[tlc + 3].isalpha()):
                        return tlc, aa
        return -1, None
    
    def buildAllFeatures(self, tokens, tokenIndex):
        token = tokens[tokenIndex]
        tokText = token.get("text").lower()
        
        self.buildAminoAcidFeatures(tokText)
        self.buildDNAFeatures(tokText)
        self.buildSubstringFeatures(tokens, tokenIndex)
        self.buildRangeFeatures(tokens, tokenIndex)
        self.buildKnownWordFeatures(tokText)
    
    def buildAminoAcidFeatures(self, string):
        index, aa = self.findAminoAcid(string)
        if aa != None:
            self.setFeature("RELaminoacid_string")
            self.setFeature("RELaminoacid_" + aa[1])
    
    def findSubstring(self, string, substring, tag=None):
        if tag == None:
            tag = substring
        index = string.find(substring)
        if index != -1:
            self.setFeature("RELsubstring_"+tag)
            if index + len(substring) == len(string):
                self.setFeature("RELsubstring_terminal_"+tag)
            else:
                self.setFeature("RELsubstring_nonterminal_"+tag)
            
    def buildSubstringFeatures(self, tokens, tokenIndex):
        string = ""
        for t in tokens[tokenIndex-6:tokenIndex]:
            # TODO the actual token does not seem to be included
            string += t.get("text")
        string = string.lower().replace("-", "").replace(" ", "")
        # nfkb
        self.findSubstring(string, "nfkappab", "nfkb")
        self.findSubstring(string, "nfkb")
        self.findSubstring(string, "nfkappab", "complex")
        self.findSubstring(string, "nfkb", "complex")
        # kappa-b
        self.findSubstring(string, "kappab")
        # ap-1
        self.findSubstring(string, "ap1")
        self.findSubstring(string, "activatingprotein1", "ap1")
        self.findSubstring(string, "ap1", "complex")
        self.findSubstring(string, "activatingprotein1", "complex")
        # proteasome
        self.findSubstring(string, "proteasome")
        self.findSubstring(string, "proteasome", "complex")
        # base pairs
        self.findSubstring(string, "bp", "bp")
        self.findSubstring(string, "basepair", "bp")
        # primes
        self.findSubstring(string, "5&apos;", "5prime")
        self.findSubstring(string, "3&apos;", "3prime")
    
    def buildDNAFeatures(self, string):
        for letter in string:
            if letter not in ["a", "g", "t", "c"]:
                return
        self.setFeature("RELDNA_sequence")
    
    def buildRangeFeatures(self, tokens, tokenIndex):
        if tokenIndex > 1:
            if tokens[tokenIndex-1].get("text").lower() in ["to", "and", "-"]:
                t1Text = tokens[tokenIndex-2].get("text")
                if t1Text[0] == "-" or t1Text[0] == "+":
                    t1Text = t1Text[1:]
                t2Text = tokens[tokenIndex].get("text")
                if t2Text[0] == "-" or t2Text[0] == "+":
                    t2Text = t2Text[1:]
                if t1Text.isdigit() and t2Text.isdigit():
                    self.setFeature("RELnumeric_range")
    
    def buildKnownWordFeatures(self, string):
        global subcomponent, supergroup
        
        string = string.lower()
        
        if string[-1] == "s":
            singular = string[:-1]
        else:
            singular = None
        if string in subcomponent or singular in subcomponent:
            self.setFeature("RELknown_subcomponent")
        if string in supergroup or singular in supergroup:
            self.setFeature("RELknown_supergroup")