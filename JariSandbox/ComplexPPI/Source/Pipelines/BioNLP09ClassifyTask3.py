from Pipeline import * # All pipelines import this
from optparse import OptionParser # For using command line options

# Read command line options
optparser = OptionParser()
optparser.add_option("-i", "--input", default=Settings.DevelFileWithDuplicates, dest="input", help="interaction xml input file", metavar="FILE")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-a", "--task", default=123, type="int", dest="task", help="task number")
optparser.add_option("-m", "--speculationModel", default=Settings.TrainSpeculationModel, dest="speculationModel", help="SVM-multiclass speculation model")
optparser.add_option("-n", "--negationModel", default=Settings.TrainNegationModel, dest="negationModel", help="SVM-multiclass negation model")
optparser.add_option("-v", "--task3Ids", default=Settings.Task3Ids, dest="task3Ids", help="Speculation & negation SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [13, 123]

# Let's define some shortcuts to make things more readable
TEST_FILE = options.input
PARSE = options.parse
TOK = options.tokenization
SPECULATION_MODEL = options.speculationModel
NEGATION_MODEL = options.negationModel

# These commands will be in the beginning of most pipelines
workdir(options.output, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in the working directory

# The id-sets will be modified, so create local copies of them.
# Using always the same id numbers for machine learning classes
# and examples ensures that the model-files will be compatible
# with all of your experiments.
TASK3_IDS = copyIdSetsToWorkdir(options.task3Ids)

###############################################################################
# Speculation detection
###############################################################################
print >> sys.stderr, "====== Speculation Detection ======"
# Build an SVM example file for the test data.
Task3ExampleBuilder.run(TEST_FILE, "speculation-test-examples", PARSE, TOK, "style:typed,speculation", TASK3_IDS, None)
Cls.test("speculation-test-examples", SPECULATION_MODEL, "speculation-test-classifications")
# Evaluate the predictions
print >> sys.stderr, "Evaluating speculation example classifications:"
Ev.evaluate("speculation-test-examples", "speculation-test-classifications", TASK3_IDS+".class_names")
# The classifications are combined with the TEST_FILE xml, to produce
# an interaction-XML file with speculation predictions
speculationXML = BioTextExampleWriter.write("speculation-test-examples", "speculation-test-classifications", TEST_FILE, None)

###############################################################################
# Negation detection
###############################################################################
print >> sys.stderr, "====== Negation Detection ======"
# Build an SVM example file for the test data.
Task3ExampleBuilder.run(TEST_FILE, "negation-test-examples", PARSE, TOK, "style:typed,negation", TASK3_IDS, None)
Cls.test("negation-test-examples", NEGATION_MODEL, "negation-test-classifications")
# Evaluate the predictions
print >> sys.stderr, "Evaluating negation example classifications:"
Ev.evaluate("negation-test-examples", "negation-test-classifications", TASK3_IDS+".class_names")
# The classifications are combined with the speculation xml, to produce
# an interaction-XML file with both speculation and negation predictions
task3XML = BioTextExampleWriter.write("negation-test-examples", "negation-test-classifications", speculationXML, "task3.xml")

###############################################################################
# Shared Task Evaluation
###############################################################################
print >> sys.stderr, "====== Shared Task Evaluation ======"
gifxmlToGenia(task3XML, "geniaformat", 3)
evaluateSharedTask("geniaformat", options.task)