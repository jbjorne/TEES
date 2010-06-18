import sys, os
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Settings
if os.environ.has_key("METAWRK"): # CSC
    Settings.SVMMultiClassDir = "/v/users/jakrbj/svm-multiclass"
    Settings.EverythingTriggerModel = "/v/users/jakrbj/release-files-review-version-models/everything-trigger-model-c_200000"
    Settings.EverythingEdgeModel = "/v/users/jakrbj/release-files-review-version-models/everything-edge-model-c_28000"
    Settings.EverythingSpeculationModel = "/v/users/jakrbj/release-files-review-version-models/everything-speculation-model-c_13000"
    Settings.EverythingNegationModel = "/v/users/jakrbj/release-files-review-version-models/everything-negation-model-c_10000"
    Settings.TriggerIds="/v/users/jakrbj/release-files-review-version-models/genia-trigger-ids"
    Settings.EdgeIds="/v/users/jakrbj/release-files-review-version-models/genia-edge-ids"
    Settings.Task3Ids="/v/users/jakrbj/release-files-review-version-models/genia-task3-ids"

from Pipeline import *
from optparse import OptionParser

optparser = OptionParser()
optparser.add_option("-i", "--input", default=None, dest="input", help="interaction xml input file", metavar="FILE")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory (for final files)")
optparser.add_option("-w", "--workdir", default="/wrk/jakrbj/shared-task-test", dest="workdir", help="working directory")
(options, args) = optparser.parse_args()
assert options.input != None
options.input = os.path.abspath(options.input)
assert options.output != None
options.output = os.path.abspath(options.output)
if not os.path.exists(options.output):
    os.makedirs(options.output)
options.workdir = os.path.abspath(options.workdir)
if not os.path.exists(options.workdir):
    os.makedirs(options.workdir)

# define shortcuts for commonly used files
TEST_FILE = options.input
OUTFILE_STEM = os.path.join(options.output, os.path.basename(options.input))
if OUTFILE_STEM[-7:] == ".xml.gz":
    OUTFILE_STEM = OUTFILE_STEM[:-7]
elif OUTFILE_STEM[-4:] == ".xml":
    OUTFILE_STEM = OUTFILE_STEM[:-4]

WORKDIR=options.workdir
PARSE_TOK="split-McClosky"

logFileName = OUTFILE_STEM+"-log.txt"
count = 2
while os.path.exists(logFileName):
    print >> sys.stderr, "Log file", logFileName, "exists, trying", OUTFILE_STEM + "-log-" + str(count) + ".txt"
    logFileName = OUTFILE_STEM + "-log-" + str(count) + ".txt"
    count += 1

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, True) # Select a working directory, don't remove existing files
log(clear=True, logFile=OUTFILE_STEM+"-log.txt") # Start logging into a file in output (not work) directory
    
###############################################################################
# Task 3 
###############################################################################
# Task 3
SPECULATION_MODEL = Settings.EverythingSpeculationModel
NEGATION_MODEL = Settings.EverythingNegationModel

# The id-sets will be modified, so create local copies of them.
# Using always the same id numbers for machine learning classes
# and examples ensures that the model-files will be compatible
# with all of your experiments.
TASK3_IDS = copyIdSetsToWorkdir(Settings.Task3Ids)

# Speculation detection
print >> sys.stderr, "====== Speculation Detection ======"
Task3ExampleBuilder.run(TEST_FILE, "speculation-test-examples", PARSE_TOK, PARSE_TOK, "style:typed,speculation", TASK3_IDS, None)
Cls.test("speculation-test-examples", SPECULATION_MODEL, "speculation-test-classifications")
xml = BioTextExampleWriter.write("speculation-test-examples", "speculation-test-classifications", TEST_FILE, None, TASK3_IDS+".class_names")

# Negation detection
print >> sys.stderr, "====== Negation Detection ======"
Task3ExampleBuilder.run(xml, "negation-test-examples", PARSE_TOK, PARSE_TOK, "style:typed,negation", TASK3_IDS, None)
Cls.test("negation-test-examples", NEGATION_MODEL, "negation-test-classifications")
xml = BioTextExampleWriter.write("negation-test-examples", "negation-test-classifications", xml, OUTFILE_STEM + "-events_unflattened_task3.xml.gz", TASK3_IDS+".class_names")

# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia(xml, OUTFILE_STEM + "-events_geniaformat.tar.gz", 3, strengths=True)
#evaluateSharedTask("geniaformat", 1)

# Touch a "complete" file
open(OUTFILE_STEM + "-finished", "wt").close()
    
# Remove workdir
if os.environ.has_key("METAWRK"): # CSC
    shutil.rmtree(options.workdir)