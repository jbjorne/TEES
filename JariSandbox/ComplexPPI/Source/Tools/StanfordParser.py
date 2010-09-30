import sys, os
import shutil
import subprocess
import tempfile
import codecs

stanfordParserDir = "/home/jari/biotext/tools/stanford-parser-2008-10-26"

def convert(input, output=None):
    global stanfordParserDir

    workdir = tempfile.mkdtemp()
    if output == None:
        output = os.path.join(workdir, "stanford-output.txt")
    
    input = os.path.abspath(input)
    cwd = os.getcwd()
    os.chdir(stanfordParserDir)
    args = ["java", "-mx150m", "-cp", "stanford-parser.jar", "edu.stanford.nlp.trees.EnglishGrammaticalStructure", "-CCprocessed", "-treeFile", input] 
    subprocess.call(args, 
        stdout=codecs.open(output, "wt", "utf-8"))
    os.chdir(cwd)

    lines = None    
    if output == None:
        outFile = codecs.open(output, "rt", "utf-8")
        lines = outFile.readlines()
        outFile.close()
    
    shutil.rmtree(workdir)
    return lines