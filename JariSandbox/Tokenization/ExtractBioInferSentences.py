import cElementTree as ElementTree
import cElementTreeUtils as ETUtils

sentenceFile = None
tokenizationFile = None

def processDocument(documentElement):
    global sentenceFile, tokenizationFile
    sentenceElement = documentElement.find("sentence")
    sentenceFile.write(sentenceElement.get("text")+"\n")
    
    tokenElements = sentenceElement.getiterator("token")
    isFirst = True
    for tokenElement in tokenElements:
        if not isFirst:
            tokenizationFile.write(" ")
        tokenizationFile.write( tokenElement.get("text") )
        isFirst = False
    tokenizationFile.write("\n")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print "Found Psyco, using"
    except ImportError:
        print "Psyco not installed"
    
    sentenceFile = open("BioInferSentences.txt", "wt")
    tokenizationFile = open("BioInferMedpostTokenization.txt", "wt")
    
    filename = "/usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInferAnalysis.xml/BioInferAnalysis.xml"
    print "Processing documents"
    ETUtils.iterparse(filename, "document", processDocument)
    
    sentenceFile.close()
    tokenizationFile.close()