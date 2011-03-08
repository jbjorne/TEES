"""
Trigger examples
"""
__version__ = "$Revision: 1.5 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Core.ExampleBuilder
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Core.Gazetteer import Gazetteer
import InteractionXML.MapPhrases as MapPhrases
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder

coNPPhraseFirstToken = set(["both", "each", "it", "its", "itself", "neither", "others",
                            "that", "the", "their", "them", "themselves", "these", "they",
                            "this", "those"])

def getBacteriaNames():
    f = open("/home/jari/data/BioNLP11SharedTask/resources/lpsn-bacteria-names.txt", "rt")
    names = []
    for line in f:
        if line.strip == "":
            continue
        if line.startswith("Note:"):
            continue
        namePart = line.split("18")[0].split("19")[0].split("(")[0]
        names.append(namePart)
    f.close()
    return names

def getBacteriaTokens(names):
    tokens = set()
    for name in names:
        for split in name.split():
            tokens.add(split.lower())
    return tokens

class PhraseTriggerExampleBuilder(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None):
        if classSet == None:
            classSet = IdSet(1)
        assert( classSet.getId("neg") == 1 )
        if featureSet == None:
            featureSet = IdSet()         
        ExampleBuilder.__init__(self, classSet, featureSet)
        
        self.styles = style
        self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)
        self.triggerFeatureBuilder.useNonNameEntities = False
        
        if "bb_features" in style:
            self.bacteriaTokens = getBacteriaTokens(getBacteriaNames())

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteerFileName=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = PhraseTriggerExampleBuilder(style, classSet, featureSet)
        if "names" in style:
            sentences = cls.getSentences(input, parse, tokenization, removeNameInfo=True)
        else:
            sentences = cls.getSentences(input, parse, tokenization, removeNameInfo=False)
        e.phraseTypeCounts = {}
        e.buildExamplesForSentences(sentences, output, idFileTag)
        print >> sys.stderr, "Phrase type counts:", e.phraseTypeCounts
    
    def buildLinearOrderFeatures(self,sentenceGraph,index,tag,features):
        """
        Linear features are built by marking token features with a tag
        that defines their relative position in the linear order.
        """
        tag = "linear_"+tag
        tokenFeatures, tokenFeatureWeights = self.getTokenFeatures(sentenceGraph.tokens[index], sentenceGraph)
        for tokenFeature in tokenFeatures:
            features[self.featureSet.getId(tag+tokenFeature)] = tokenFeatureWeights[tokenFeature]
    
    def buildLinearNGram(self, phraseTokens, sentenceGraph, features):
        ngram = "ngram"
        for token in phraseTokens:
            ngram += "_" + sentenceGraph.getTokenText(token).lower()
        features[self.featureSet.getId(ngram)] = 1
    
    def getPhraseHeadToken(self, phrase, phraseTokens):
        bestToken = (-9999, None)
        for token in phraseTokens:
            headScore = int(token.get("headScore"))
            if headScore >= bestToken[0]: # >= because rightmost is best
                bestToken = (headScore, token)
        return bestToken[1]
    
    def getPhraseTokens(self, phrase, sentenceGraph):
        phraseBegin = int(phrase.get("begin"))
        phraseEnd = int(phrase.get("end"))
        return sentenceGraph.tokens[phraseBegin:phraseEnd+1]
    
    def getCategoryName(self, phrase, phraseToEntity):
        if phrase not in phraseToEntity:
            return "neg"
        entityTypes = set()
        for entity in phraseToEntity[phrase]:
            entityTypes.add(entity.get("type"))
        return "---".join(sorted(list(entityTypes)))
    
    def isPotentialCOTrigger(self, phrase, phraseTokens, sentenceGraph):
        global coNPPhraseFirstToken
        
        # Check type
        if phrase.get("type") not in ["NP", "NP-IN"]: # only limit these types
            return True
        # Check named entities
        for token in phraseTokens:
            if sentenceGraph.tokenIsName[token]:
                return True
        # Check first word
        if phraseTokens[0].get("text") in coNPPhraseFirstToken:
            return True
        else:
            return False
    
    def buildExamples(self, sentenceGraph):
        """
        Build one example for each phrase in the sentence
        """
        self.triggerFeatureBuilder.initSentence(sentenceGraph)
                
        examples = []
        exampleIndex = 0
        
        # Prepare phrases, create subphrases
        #filter = set(["NP", "TOK-IN", "WHADVP", "WHNP", "TOK-WP$", "TOK-PRP$", "NP-IN"])
        filter = set(["ADJP",
                  "DT(-)-NP-IN",
                  "DT(-)-NP",
                  "NP",
                  "NP-IN",
                  "PP",
                  "S",
                  "S1",
                  "TOK-tJJ",
                  "TOK-tNN",
                  "TOK-tNNP",
                  "TOK-tNNS",
                  "VP",
                  "VP-IN"])
        phrases = MapPhrases.getPhrases(sentenceGraph.parseElement, sentenceGraph.tokens)
        phraseDict = MapPhrases.getPhraseDict(phrases)
        phrases.extend( MapPhrases.makeINSubPhrases(phrases, sentenceGraph.tokens, phraseDict) )
        phrases.extend( MapPhrases.makeTokenSubPhrases(sentenceGraph.tokens, phraseDict, None) )
        phrases, phraseDict = MapPhrases.filterPhrases(phrases, filter)
        
        phraseToEntity = MapPhrases.getPhraseEntityMapping(sentenceGraph.entities, phraseDict)
        # Make counts
        phraseTypeCounts = MapPhrases.getPhraseTypeCounts(phrases)
        for key in phraseTypeCounts.keys():
            if not self.phraseTypeCounts.has_key(key):
                self.phraseTypeCounts[key] = 0
            self.phraseTypeCounts[key] += phraseTypeCounts[key]
        
        # Build one example for each phrase
        for phrase in phrases:
            features = {}
            self.triggerFeatureBuilder.setFeatureVector(features)
            
            categoryName = self.getCategoryName(phrase, phraseToEntity)
            category = self.classSet.getId(categoryName)
            phraseTokens = self.getPhraseTokens(phrase, sentenceGraph)
            phraseHeadToken = self.getPhraseHeadToken(phrase, phraseTokens)
            self.exampleStats.beginExample(categoryName)
            
            if "co_limits" in self.styles and not self.isPotentialCOTrigger(phrase, phraseTokens, sentenceGraph):
                self.exampleStats.filter("co_limits")
                self.exampleStats.endExample()
                continue
            
            # Sentence level features
            features.update(self.triggerFeatureBuilder.bowFeatures)
            
            # Whole phrase features
            self.buildLinearNGram(phraseTokens, sentenceGraph, features)
            features[self.featureSet.getId("pType_"+phrase.get("type"))] = 1
            for split in phrase.get("type").split("-"):
                features[self.featureSet.getId("pSubType_"+split)] = 1
            # Check named entities
            nameCount = 0
            for token in phraseTokens:
                if sentenceGraph.tokenIsName[token]:
                    nameCount += 1
            features[self.featureSet.getId("phraseNames_"+str(nameCount))] = 1
            features[self.featureSet.getId("phraseNameCount")] = nameCount
            
            # Head token features
            self.triggerFeatureBuilder.setTag("head_")
            self.triggerFeatureBuilder.buildFeatures(phraseHeadToken)            
            self.triggerFeatureBuilder.buildAttachedEdgeFeatures(phraseHeadToken, sentenceGraph)
            self.triggerFeatureBuilder.setTag()
            
            # Features for all phrase tokens
            self.triggerFeatureBuilder.setTag("ptok_")
            phraseTokenPos = 0
            #print len(phraseTokens)
            for token in phraseTokens:
                self.triggerFeatureBuilder.setTag("ptok_")
                self.triggerFeatureBuilder.buildFeatures(phraseHeadToken, linear=False, chains=False)
                self.triggerFeatureBuilder.setTag("ptok_" + str(phraseTokenPos) + "_" )
                self.triggerFeatureBuilder.buildFeatures(phraseHeadToken, linear=False, chains=False)
                self.triggerFeatureBuilder.setTag("ptok_" + str(phraseTokenPos-len(phraseTokens)) + "_" )
                self.triggerFeatureBuilder.buildFeatures(phraseHeadToken, linear=False, chains=False)            
                #self.triggerFeatureBuilder.buildAttachedEdgeFeatures(phraseHeadToken)
                if "bb_features" in self.styles:
                    if token.get("text").lower() in self.bacteriaTokens:
                        features[self.featureSet.getId("lpsnBacToken")] = 1
                        features[self.featureSet.getId("lpsnBacToken_" + str(phraseTokenPos))] = 1
                        features[self.featureSet.getId("lpsnBacToken_" + str(phraseTokenPos-len(phraseTokens)))] = 1
                phraseTokenPos += 1
            self.triggerFeatureBuilder.setTag()
             
            extra = {"xtype":"phrase","t":phraseHeadToken.get("id"), "p":phrase.get("id"), "ptype":phrase.get("type")}
            extra["charOffset"] = phrase.get("charOffset")
            if phrase not in phraseToEntity:
                extra["eids"] = "neg"
            else:
                extra["eids"] = ",".join([x.get("id") for x in phraseToEntity[phrase]])
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            self.exampleStats.endExample()
            exampleIndex += 1
        
        # Mark missed entities in exampleStats
        linkedEntities = set( sum(phraseToEntity.values(), []) )
        for entity in sentenceGraph.entities:
            if entity.get("isName") != "True" and entity not in linkedEntities:
                self.exampleStats.beginExample(entity.get("type"))
                self.exampleStats.filter("no_phrase")
                self.exampleStats.endExample()
        return examples