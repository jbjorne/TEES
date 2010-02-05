__version__ = "$Revision: 1.11 $"

class FeatureBuilder:
    """
    Multiple example builders might make use of the same features. A feature builder object can be used in
    different example builders that require the same feature set.
    """
    def __init__(self, featureSet):
        """
        @type featureSet: IdSet
        @param featureSet: feature ids
        """
        self.featureSet = featureSet # feature ids
        self.features = None # current feature vector
        self.entity1 = None # an entity node for which features are built
        self.entity2 = None # another entity node for pairwise examples such as edges
        self.noAnnType = False # do not use annotated entity types for building features
        self.ontologyFeatureBuilder = None
        self.maximum = False # produce maximum number of features
        
        self.maskNamedEntities = True # named entity text strings are replaced with NAMED_ENT
        self.tag = "" # a prefix that is added to each feature name
    
    def setFeatureVector(self, features, entity1=None, entity2=None):
        """
        When the feature builder builds features, they are put to this feature vector.
        
        @type features: dictionary
        @param features: a reference to the feature vector
        @type entity1: cElementTree.Element
        @param entity1: an entity used by trigger or edge feature builders   
        @type entity2: cElementTree.Element
        @param entity2: an entity used by trigger or edge feature builders   
        """
        self.features = features
        self.entity1 = entity1
        self.entity2 = entity2
        self.tokenFeatures = {}
        
    def setFeature(self, name, value):
        """
        Add a feature to the feature vector. If the feature already exists, its current
        value is replaced with the new value. All features are prefixed with FeatureBuilder.tag.
        
        @type name: str
        @type value: float
        """
        self.features[self.featureSet.getId(self.tag+name)] = value
        
    def normalizeFeatureVector(self):
        """
        Some machine learning tasks require feature values to be normalized to range [0,1]. The range is
        defined as the difference of the largest and smallest feature value in the current feature vector.
        If this method is used, it should be called as the last step after generating all features.
        """
        # Normalize features
        total = 0.0
        for v in self.features.values(): total += abs(v)
        if total == 0.0: 
            total = 1.0
        for k,v in self.features.iteritems():
            self.features[k] = float(v) / total

    def getTokenFeatures(self, token, sentenceGraph, text=True, POS=True, annotatedType=True, stem=False, ontology=True):
        """
        Token features are features describing an isolated word token. These subfeatures are often merged into
        such features like n-grams. This method produces and caches a set of feature names for a token in
        the sentenceGraph sentence. The various flags can be used to choose which attributes will be included in the
        feature name list.
        
        @type token: cElementTree.Element
        @param token: a word token 
        @type sentenceGraph: SentenceGraph
        @param sentenceGraph: the sentence to which the token belongs
        @type text: boolean
        @type POS: boolean
        @type annotatedType: boolean
        @type stem: boolean
        @type ontology: boolean         
        """
        callId = token.get("id") + str(text) + str(POS) + str(annotatedType) + str(stem) + str(ontology)
        if self.tokenFeatures.has_key(callId):
            return self.tokenFeatures[callId]
        
        featureList = []
        if text:
            featureList.append("txt_"+sentenceGraph.getTokenText(token))
            if (not self.maskNamedEntities) and sentenceGraph.tokenIsName[token]:
                featureList.append("txt_"+token.get("text"))
        if POS:
            pos = token.get("POS")
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
        
        self.tokenFeatures[callId] = featureList            
        return featureList
    
    def getTokenAnnotatedType(self, token, sentenceGraph):
        """
        Multiple entities may have the same head token. This returns a list of the types of all entities whose
        head token this token is. If the FeatureBuilder.maximum flag is set, the list is truncated to a length of
        two, otherwise to a length of one. This is done because when token features (to which the annotated type
        belongs to) are combined into other features, a large number of annotated type features can lead to an
        exponential increase in the number of features.
        """
        if len(sentenceGraph.tokenIsEntityHead[token]) > 0 and not self.noAnnType:
            annTypes = set()
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.get("type") != None and not entity.get("type") in annTypes:
                    if self.entity1 == None and self.entity2 == None:
                        annTypes.add(entity.get("type"))
                    else:
                        if self.maximum:
                            annTypes.add(entity.get("type"))
                        if self.entity1 == entity:
                            if not self.maximum:
                            	return [entity.get("type")]
                            else:
                            	annTypes.add("e1_"+entity.get("type"))
                        elif self.entity2 == entity:
                            if not self.maximum:
                            	return [entity.get("type")]
                            else:
								annTypes.add("e2_"+entity.get("type"))
                        else:
                            annTypes.add(entity.get("type"))
            annTypes = list(annTypes)
            annTypes.sort()
            if self.maximum:
				return annTypes[0:2]
            else:
            	return annTypes[0:1] #annTypes[0:2]
        else:
            return ["noAnnType"]