"""
Trigger examples
"""
__version__ = "$Revision: 1.2 $"

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
    
    def buildExamples(self, sentenceGraph):
        """
        Build one example for each phrase in the sentence
        """
        self.triggerFeatureBuilder.initSentence(sentenceGraph)
                
        examples = []
        exampleIndex = 0
        
        # Prepare phrases, create subphrases
        #filter = set(["NP", "TOK-IN", "WHADVP", "WHNP", "TOK-WP$", "TOK-PRP$", "NP-IN"])
        phrases = MapPhrases.getPhrases(sentenceGraph.parseElement, set(["NP", "WHADVP", "WHNP"]))
        phraseDict = MapPhrases.getPhraseDict(phrases)
        phrases.extend( MapPhrases.makeINSubPhrases(phrases, sentenceGraph.tokens, phraseDict, ["NP"]) )
        phrases.extend( MapPhrases.makeTokenSubPhrases(sentenceGraph.tokens, phraseDict) )
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
            
            # Sentence level features
            features.update(self.triggerFeatureBuilder.bowFeatures)
            
            # Whole phrase features
            self.buildLinearNGram(phraseTokens, sentenceGraph, features)
            features[self.featureSet.getId("pType_"+phrase.get("type"))] = 1
            for split in phrase.get("type").split("-"):
                features[self.featureSet.getId("pSubType_"+split)] = 1
            
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
                self.triggerFeatureBuilder.buildFeatures(phraseHeadToken, linear=False)
                self.triggerFeatureBuilder.setTag("ptok_" + str(phraseTokenPos) + "_" )
                self.triggerFeatureBuilder.buildFeatures(phraseHeadToken, linear=False)
                self.triggerFeatureBuilder.setTag("ptok_" + str(len(phraseTokens)-phraseTokenPos-1) + "_" )
                self.triggerFeatureBuilder.buildFeatures(phraseHeadToken, linear=False)            
                #self.triggerFeatureBuilder.buildAttachedEdgeFeatures(phraseHeadToken)
                phraseTokenPos += 1
            self.triggerFeatureBuilder.setTag()
             
            extra = {"xtype":"phrase","t":phraseHeadToken.get("id"), "p":phrase.get("id"), "ptype":phrase.get("type")}
            extra["charOffset"] = phrase.get("charOffset")
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            self.exampleStats.beginExample(categoryName)
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