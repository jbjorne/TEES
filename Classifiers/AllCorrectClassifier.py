from Classifier import Classifier
import Core.ExampleUtils as Example
import sys, os, types, copy

class AllCorrectClassifier(Classifier):
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
        classifier = copy.copy(self)
        classifier.parameters = "TEES.classifier=AllCorrectClassifier"
        return classifier
        
    def classify(self, examples, output, model=None, finishBeforeReturn=False, replaceRemoteFiles=True):
        output = os.path.abspath(output)
        # Get examples
        if type(examples) == types.ListType:
            print >> sys.stderr, "Classifying", len(examples), "with All-Correct Classifier"
        else:
            print >> sys.stderr, "Classifying file", examples, "with All-Correct Classifier"
            examples = self.getExampleFile(examples, upload=False, replaceRemote=False, dummy=False)
            examples = Example.readExamples(examples, False)
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        # Classify
        f = open(output, "wt")
        for example in examples:
            f.write(str(example[1]) + "\n")
        f.close()
        classifier.predictions = output
        return classifier