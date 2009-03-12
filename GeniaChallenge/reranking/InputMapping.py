#A graph kernel -based feature generation method
from parseGifxml import gifxmlParser
from numpy import mat
from numpy import float64
from numpy import zeros

def getTokenizationParseEntities(sentence, t_name, p_name):
    analyses = sentence.find("sentenceanalyses")
    tokenizations = analyses.find("tokenizations")
    tokenizations = tokenizations.findall("tokenization")
    tokenization = None
    for t in tokenizations:
        if t.attrib["tokenizer"] == t_name:
            tokenization = t
    assert tokenization != None
    parses = analyses.find("parses")
    parses = parses.findall("parse")
    parse = None
    for p in parses:
        if p.attrib["parser"] == p_name:
            parse = p
    assert parse != None
    entities = sentence.findall("entity")
    return tokenization, parse, entities

def getTokenFeatures(tokenization, entities):
    token_features = []
    #Simplest possible feature representation
    for token in tokenization:
        fset = set([])
        fset.add(token.attrib["text"])
        coffset = token.attrib["charOffset"]
        coffset = coffset.split("-")
        coffset = int(coffset[0]), int(coffset[1])
        for entity in entities:
            eoffset = entity.attrib["charOffset"].split("-")
            eoffset = int(eoffset[0]), int(eoffset[1])
            if (coffset[0]>=eoffset[0] and coffset[0]<=eoffset[1]) or (coffset[1]>=eoffset[0] and coffset[1]<= eoffset[1]):
                fset.add("$"+entity.attrib["type"])
        token_features.append(fset)
    return token_features

def getDependencyFeatures(dependencies, token_features):
    dep_features = []
    for dep in dependencies:
        features = []
        index1 = int(dep.attrib["t1"].split("_")[1])-1
        index2 = int(dep.attrib["t2"].split("_")[1])-1
        dtype = dep.attrib["type"]
        for f1 in token_features[index1]:
            for f2 in token_features[index2]:
                features.append(f1+"$"+dtype+"$"+f2)
        dep_features.append(features)
    return dep_features

def getFinalFeatures(token_features, dep_features):
    features = {}
    for i in range(len(token_features)):
        for fname in token_features[i]:
            if not fname in features:
                features[fname] = 1
            else:
                features[fname] += 1
            if i+1 <len(token_features):
                for fname2 in token_features[i+1]:
                    if not (fname+"$"+fname2) in features:
                        features[fname+"$"+fname2]=1
                    else:
                        features[fname+"$"+fname2] +=1
    for i in range(len(dep_features)):
        for fname in dep_features[i]:
            if not fname in dep_features:
                features[fname] = 1
            else:
                features[fname] += 1
    return features
        
def buildDictionary(iterator):
    fnames = set([])
    for document in iterator:
        for child in document:
            if child.tag == "sentence":
                tokenization, parse, entities = getTokenizationParseEntities(child, "split-Charniak-Lease", "split-Charniak-Lease")
                token_features = getTokenFeatures(tokenization, entities)
                dep_features = getDependencyFeatures(parse, token_features)
                features = getFinalFeatures(token_features, dep_features)
                keys = features.keys()
                for key in keys:
                    fnames.add(key)
    mapping = {}
    counter = 1
    for fname in fnames:
        mapping[fname] = counter
        counter += 1
    return mapping

def writeMapping(mapping, f):
    keys = mapping.keys()
    for key in keys:
        f.write(key+" "+str(mapping[key])+"\n")
    f.close()

def readDictionaryMapping(file):
    dictionary = {}
    for line in file:
        line = line.strip().split()
        assert len(line) == 2
        dictionary[line[0]] = int(line[1])
    return dictionary

def trainMapping():
    f = open("/usr/share/biotext/GeniaChallenge/xml/train.xml")
    f2 = open("featurefile",'w')
    parser = gifxmlParser(f)
    iterator = parser.documentIterator()
    mapping = buildDictionary(iterator)
    writeMapping(mapping, f2)
    f.close()
    f2.close()

if __name__=="__main__":
    f = open("/usr/share/biotext/GeniaChallenge/xml/train.xml")
    f2 = open("featurefile")
    mapping = readDictionaryMapping(f2)
    f2.close()
    f2 = open("train_inputs",'w')
    parser = gifxmlParser(f)
    iterator = parser.documentIterator()
    for document in iterator:
        for child in document:
            if child.tag == "sentence":
                tokenization, parse, entities = getTokenizationParseEntities(child, "split-Charniak-Lease", "split-Charniak-Lease")
                token_features = getTokenFeatures(tokenization, entities)
                dep_features = getDependencyFeatures(parse, token_features)
                features = getFinalFeatures(token_features, dep_features)
                fvalues = {}
                for key in features.keys():
                    if key in mapping:
                        fvalues[int(mapping[key])] = features[key]
                keys = fvalues.keys()
                keys.sort()
                line = "".join("%d:%f " %(x, fvalues[x]) for x in keys)+"\n"
                f2.write(line)
    f2.close()
                
