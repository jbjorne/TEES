from Pipeline import * # All pipelines import this
from optparse import OptionParser # For using command line options
import traceback
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Tools.GeniaSentenceSplitter
import Tools.BANNER
import Tools.CharniakJohnsonParser
#import InteractionXML.ConvertPMC as ConvertPMC
import STFormat.STTools
import STFormat.ConvertXML

# Read command line options
optparser = OptionParser()
p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
optparser.add_option("-i", "--input", default=p, dest="input", help="interaction xml input file", metavar="FILE")
optparser.add_option("-o", "--output", default="/home/jari/data/temp/testSTConversion.xml", dest="output", help="output directory")
optparser.add_option("-w", "--workdir", default=None, dest="workdir", help="work directory")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
#assert options.workdir != None

# These commands will be in the beginning of most pipelines
#workdir(options.output, False) # Select a working directory, don't remove existing files
#log() # Start logging into a file in the working directory

documents = STFormat.STTools.loadSet(options.input)
xml = STFormat.ConvertXML.toInteractionXML(documents)
xml = Tools.GeniaSentenceSplitter.makeSentences(xml)#, options.output)
#xml = Tools.BANNER.run(xml, "before-parsing.xml")
xml = Tools.CharniakJohnsonParser.parse(xml, options.output, requireEntities=True)
