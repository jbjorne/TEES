import sys, os
import shutil
mainTEESDir = os.path.abspath(os.path.join(__file__, ".."))
sys.path.append(mainTEESDir)
from Detectors.Preprocessor import Preprocessor

def combineParses(inPath, outPath, pattern):

def run(inPath, outPath, pattern, connection, numJobs, clear, debug):
    model = "GE11"
    # Remove existing work directory, if requested to do so
    if os.path.exists(outPath) and clear:
        print >> sys.stderr, "Output directory exists, removing", outPath
        shutil.rmtree(outPath)
    # Create work directory if needed
    if not os.path.exists(outPath):
        print >> sys.stderr, "Making output directory", outPath
        os.makedirs(outPath)
        
    combineParses(inPath, os.path.join(outPath, "parses"), pattern)
        
    preprocessor = Preprocessor(["MERGE-SETS", "IMPORT-PARSE", "DIVIDE-SETS"])
    preprocessor.stepArgs("IMPORT-PARSE")["parseDir"] = options.parseDir
    preprocessor.process(inPath, os.path.join(outPath, "corpus/" + model))

if __name__== "__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="Predict events/relations")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-p", "--output", default=None, dest="output", help="output file stem")
    optparser.add_option("-p", "--parallel", default=1, type=int, dest="parallel", help="")
    optparser.add_option("-c", "--connection", default="connection=Unix:jobLimit=$JOBS", dest="connection", help="")
    # Debugging and process control
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    (options, args) = optparser.parse_args()