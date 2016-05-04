import sys, os
sysPath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(sysPath)
import Utils.Settings as Settings
import Catenate

def mergeCorpora(corpusIds, outputId, inputDir, outDir):
    xml = Catenate.catenateElements(corpusIds, inputDir)
    

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-c", "--corpusIds", default="BB11,BB13T2,BB_EVENT_16", help="Datasets to process")
    optparser.add_option("-i", "--inDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-o", "--outDir", default=os.path.normpath(Settings.DATAPATH + "/corpora"), help="directory for output files")
    optparser.add_option("-t", "--tag", default="BBCAT", help="Parse with preprocessor")
    (options, args) = optparser.parse_args()
    
    mergeCorpora(options.corpusIds.split(","), options.tag, options.inDir, options.outDir)
