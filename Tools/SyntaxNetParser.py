import sys, os
import shutil
import subprocess
import tempfile
import codecs
import ProcessUtils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")))
import Utils.ElementTreeUtils as ETUtils
from Parser import Parser
import Utils.Settings as Settings

class SyntaxNetParser(Parser):    
    ###########################################################################
    # Main Interface
    ###########################################################################
    
#     @classmethod
#     def parseCls(cls, parserName, input, output=None, debug=False, reparse=False, syntaxNetDir=None, modelDir=None):
#         parserObj = cls()
#         parserObj.parse(parserName, input, output, debug, reparse, syntaxNetDir, modelDir)
    
    def parse(self, parserName, input, output=None, debug=False, reparse=False, syntaxNetDir=None, modelDir=None):
        # Run the parser process
        if syntaxNetDir == None:
            syntaxNetDir = Settings.SYNTAXNET_DIR
        corpusTree, corpusRoot = self.getCorpus(input)
        workdir = tempfile.mkdtemp()
        inPath = self.makeInputFile(corpusRoot, workdir)
        outPath = ProcessUtils.runSentenceProcess(self.run, syntaxNetDir, inPath, workdir, True, "SyntaxNetParser", "Parsing", processArgs={"modelDir":modelDir})
        self.insertCoNLLParses(outPath, corpusRoot, parserName, unescaping=True, conllFormat="conllx")
        # Remove work directory
        if not debug:
            shutil.rmtree(workdir)
        else:
            print >> sys.stderr, "Parser IO files at", workdir
        # Write the output XML file
        if output != None:
            print >> sys.stderr, "Writing output to", output
            ETUtils.write(corpusRoot, output)
        return corpusTree
    
    ###########################################################################
    # Parser Process Control
    ###########################################################################

    def run(self, input, output, modelDir=None):
        parserEval = "bazel-bin/syntaxnet/parser_eval"
        if modelDir == None:
            modelDir = "syntaxnet/models/parsey_mcparseface"
        universal = modelDir.endswith("universal")
        
        morpherArgs = [parserEval,
                      "--input", "stdin",
                      "--output", "stdout-conll",
                      "--hidden_layer_sizes", "64",
                      "--arg_prefix", "brain_morpher",
                      "--graph_builder", "structured",
                      "--task_context", os.path.join(modelDir, "context.pbtxt"),
                      "--resource_dir", modelDir,
                      "--model_path", os.path.join(modelDir, "morpher-params"),
                      "--slim_model",
                      "--batch_size", "1024",
                      "--alsologtostderr"]
        
        taggerArgs = [parserEval,
                      "--input", "stdin-conll" if universal else "stdin",
                      "--output", "stdout-conll",
                      "--hidden_layer_sizes", "64",
                      "--arg_prefix", "brain_tagger",
                      "--graph_builder", "structured",
                      "--task_context", os.path.join(modelDir, "context.pbtxt"),
                      "--model_path", os.path.join(modelDir, "tagger-params"),
                      "--slim_model",
                      "--batch_size", "1024",
                      "--alsologtostderr"]
        if universal:
            taggerArgs += ["--resource_dir", modelDir]
        

        parserArgs = [parserEval,
                      "--input", "stdin-conll",
                      "--output", "stdout-conll",
                      "--hidden_layer_sizes", "512,512",
                      "--arg_prefix", "brain_parser",
                      "--graph_builder", "structured",
                      "--task_context", os.path.join(modelDir, "context.pbtxt"),
                      "--model_path", os.path.join(modelDir, "parser-params"),
                      "--slim_model",
                      "--batch_size", "1024",
                      "--alsologtostderr"]
        if universal:
            parserArgs += ["--resource_dir", modelDir]
        
        print >> sys.stderr, "SyntaxNet model:", modelDir
        if universal:
            print >> sys.stderr, "Morpher arguments:", taggerArgs
        print >> sys.stderr, "Tagger arguments:", taggerArgs
        print >> sys.stderr, "Parser arguments:", parserArgs
        if universal:
            morpher = subprocess.Popen(morpherArgs,
                                  stdin=codecs.open(input, "rt", "utf-8"),
                                  stdout=subprocess.PIPE)
        tagger = subprocess.Popen(taggerArgs,
                                  stdin=morpher.stdout if universal else codecs.open(input, "rt", "utf-8"),
                                  stdout=subprocess.PIPE)
        parser = subprocess.Popen(parserArgs,
                                  stdin=tagger.stdout,
                                  stdout=codecs.open(output, "wt", "utf-8"))
        return ProcessUtils.ProcessWrapper([morpher, tagger, parser] if universal else [tagger, parser])

    ###########################################################################
    # Parsing Process File IO
    ###########################################################################
    
    def makeInputFile(self, corpusRoot, workdir):
        inputPath = os.path.join(workdir, "input")
        with codecs.open(inputPath, "wt", "utf-8") as f:
            for sentence in corpusRoot.getiterator("sentence"):
                f.write(sentence.get("text").replace("\n", " ").replace("\r", " ").replace("\t", " ").strip() + "\n")
        return inputPath

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="SyntaxNet Parser Wrapper")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="Name of the parse element")
    optparser.add_option("-d", "--syntaxNetDir", default=None, dest="syntaxNetDir", help="SyntaxNet program directory")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    SyntaxNetParser().parse(options.parse, options.input, options.output, options.debug, False, options.syntaxNetDir)        