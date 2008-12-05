class FeatureBuilder:
    def __init__(self, featureSet):
        self.featureSet = featureSet
        self.features = None
        self.entity1 = None
        self.entity2 = None
        self.noAnnType = False
        self.ontologyFeatureBuilder = None
        self.maximum = False # produce maximum number of features
    
    def setFeatureVector(self, features, entity1=None, entity2=None):
        self.features = features
        self.entity1 = entity1
        self.entity2 = entity2
        
    def normalizeFeatureVector(self):
        # Normalize features
        total = 0.0
        for v in self.features.values(): total += abs(v)
        if total == 0.0: 
            total = 1.0
        for k,v in self.features.iteritems():
            self.features[k] = float(v) / total

    def getTokenFeatures(self, token, sentenceGraph, text=True, POS=True, annotatedType=True, stem=False, ontology=True):
        featureList = []
        if text:
            featureList.append("txt_"+sentenceGraph.getTokenText(token))
        if POS:
            pos = token.attrib["POS"]
            if pos.find("_") != None and self.maximum:
                for split in pos.split("_"):
                    featureList.append("POS_"+split)
            featureList.append("POS_"+pos)
        if annotatedType and not self.noAnnType:
            annTypes = self.getTokenAnnotatedType(token, sentenceGraph)
            if "noAnnType" in annTypes and not self.maximum:
                annTypes.remove("noAnnType")
            for annType in annTypes:
                featureList.append("annType_"+annType)
            if ontology and (self.ontologyFeatureBuilder != None):
                for annType in annTypes:
                    featureList.extend(self.ontologyFeatureBuilder.getParents(annType))
        if stem:
            featureList.append("stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(token)))
                    
        return featureList
    
    def getTokenAnnotatedType(self, token, sentenceGraph):
        if len(sentenceGraph.tokenIsEntityHead[token]) > 0 and not self.noAnnType:
            annTypes = set()
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.attrib.has_key("type") and not entity.attrib["type"] in annTypes:
                    if self.entity1 == None and self.entity2 == None:
                        annTypes.add(entity.attrib["type"])
                    else:
						if self.maximum:
                        	annTypes.add(entity.attrib["type"])
                        if self.entity1 == entity:
							if not self.maximum:
                            	return [entity.attrib["type"]]
							else:
                            	annTypes.add("e1_"+entity.attrib["type"])
                        elif self.entity2 == entity:
							if not self.maximum:
                            	return [entity.attrib["type"]]
                            else:
								annTypes.add("e2_"+entity.attrib["type"])
                        else:
                            annTypes.add(entity.attrib["type"])
            annTypes = list(annTypes)
            annTypes.sort()
			if self.maximum:
				return annTypes[0:2]
			else:
            	return annTypes[0:1] #annTypes[0:2]
        else:
            return ["noAnnType"]