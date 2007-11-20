"""
  Program:    Compare Tokenization
  Date:       Nov. 20, 2007
  Author:     Jari Bjorne

  Description: This program compares two tokenizations, which could be f.e.
               created with two different tokenizators.
                
  Status: Working

  Dependencies: None
"""

def compareSentences(sentence1, sentence2):
    """Compares two sentences.

    Sentence2 is compared two sentence1. The return value is a tuple containing
    statistics and a list of the differing areas.

    Keyword arguments:
    sentence1 -- string
    sentence2 -- string
    """ 
               
    truePositives = 0
    falsePositives = 0
    falseNegatives = 0
    
    index2 = 0
    begin1 = 0 # Begin position for possible difference area
    begin2 = 0 # Begin position for possible difference area
    differences = []
    difference = False
    for i in range(len(sentence1)):
        if sentence1[i].isspace():
            if sentence2[index2].isspace():
                truePositives += 1
                
                if difference == True:
                    differences.append( (sentence1[begin1:i],sentence2[begin2:index2]) )
                    difference = False
                begin1 = i
                begin2 = index2
            else:
                falseNegatives += 1
                index2 -= 1
                difference = True
        elif sentence2[index2].isspace():
            falsePositives += 1
            index2 += 1
            difference = True
        index2 += 1
    
    return (truePositives, falsePositives, falseNegatives, differences)

if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print "Found Psyco, using"
    except ImportError:
        print "Psyco not installed"
    
    progDescription = "Compare two tokenizations. The input files must have the tokenizations in the following format: One sentence per line, and tokens separated by a single whitespace. The program will print to stdout statistics and the differences in the tokenization."    
    optparser = OptionParser(usage="%prog [options]\n" + progDescription)
    optparser.add_option("-m", "--model", dest="model", default="BioInferMedpostTokenization.txt", help="The model tokenization", metavar="FILE")
    optparser.add_option("-t", "--test", dest="test", default="BioInferJulieTokenization.txt", help="The tokenization that will be compared to the model tokenization", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    modelFile = open(options.model)
    testFile = open(options.test)
    modelLines = modelFile.readlines()
    modelFile.close()
    testLines = testFile.readlines()
    testFile.close()
    
    print
    print "Comparing: " + options.model + " / " + options.test
    print "Line: Precision, Recall, True Positives, False Positives, False Negatives"
    print
    precisionSum = 0.0
    recallSum = 0.0
    for i in range(len(modelLines)):
        comparison = compareSentences(modelLines[i], testLines[i])
        precision = float(comparison[0]) / float(comparison[0] + comparison[1])
        recall = float(comparison[0]) / float(comparison[0] + comparison[2])
        print str(i) + ": P=" + str(precision)[0:4] + " R=" + str(recall)[0:4] + " tp=" + str(comparison[0]) + " fp=" + str(comparison[1]) + " fn=" + str(comparison[2]) + "  ",
        for difference in comparison[3]:
            print "[" + difference[0] + " / " + difference[1] + "] ",
        print
        precisionSum += precision
        recallSum += recall
    print
    print "Total: P=" + str(precisionSum/float(len(modelLines)))[0:4] + " R=" + str(recallSum/float(len(modelLines)))[0:4]