from Pipeline import *
import os, sys

# Define working directory
WORKDIR="/usr/share/biotext/GeniaChallenge/Post-processing-test-newest"
workdir(WORKDIR, False) # Select a working directory, remove existing files
log() # Start logging into a file in working directory

# Current Parse
PARSE_TOK = "split-McClosky"
# Current model
MODEL = 'train'
# File to be post-processed
PREDICTED_DEVEL_FILE="/usr/share/biotext/GeniaChallenge/extension-data/genia/test-set-split-McClosky-develDebug/test-predicted-edges.xml"

###########################################################
# Old post-processing
###########################################################
xml = unflatten(PREDICTED_DEVEL_FILE, PARSE_TOK)
#prune.interface(["-i",PREDICTED_DEVEL_FILE,"-o","pruned.xml","-c"])
#unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia(xml, "geniaformat")
#gifxmlToGenia("unflattened.xml", "geniaformat")
# Evaluate the output
evaluateSharedTask("geniaformat", 1)

sys.exit()

###########################################################
# New post-processing
###########################################################
import subprocess as SP
args = ['grep', '-v', 'type="neg"', PREDICTED_DEVEL_FILE]
f = open('tmp','w')
stdout,stderr = SP.Popen(args,
                         stderr=None,
                         stdout=f,
                         stdin=None).communicate()
import sys
sys.path.append("/usr/share/biotext/GeniaChallenge/BEG")
import BioEventGraph as BEG
sys.path.pop()
BEG.scripts.pipeline.interface(['-c', '/usr/share/biotext/GeniaChallenge/BEG/cmds/bionlp09.unmerge-predicted.cmds',
                                '--input=tmp',
                                '--output=unflattened-new-pp.xml',
                                '--parse=parse_%s'%PARSE_TOK,
                                '--weka=/usr/share/biotext/GeniaChallenge/BEG/models/delmemodels',
                                '--refweka=/usr/share/biotext/GeniaChallenge/BEG/models/bionlp09.%s'%MODEL])
gifxmlToGenia("unflattened-new-pp.xml", "new-post-process-geniaformat")
evaluateSharedTask("new-post-process-geniaformat", 1)

# Compare outputs and make sure approx span & approx recursive f-score
# is higher for the new post-processing!!!


# evaluation

# BEG.scripts.pipeline.interface(['-c', '/usr/share/biotext/GeniaChallenge/BEG/cmds/bionlp09.evaluate.cmds',
#                                 '--predicted=XXX',
#                                 '--correct=YYY',
#                                 '--root=Event]) # for shared task!
#                                 '--root=universal]) # for bioinfer!
