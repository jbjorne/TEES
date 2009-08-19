from Pipeline import *
import os

# Define working directory
WORKDIR="/usr/share/biotext/GeniaChallenge/Post-processing-test"
workdir(WORKDIR, True) # Select a working directory, remove existing files
log() # Start logging into a file in working directory

# Current Parse
PARSE_TOK = "split-McClosky"
# File to be post-processed
PREDICTED_DEVEL_FILE="/usr/share/biotext/GeniaChallenge/extension-data/genia/test-set-split-McClosky-develDebug/test-predicted-edges.xml"

###########################################################
# Old post-processing
###########################################################
prune.interface(["-i",PREDICTED_DEVEL_FILE,"-o","pruned.xml","-c"])
unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("unflattened.xml", "geniaformat")
# Evaluate the output
evaluateSharedTask("geniaformat", 1)

###########################################################
# New post-processing
###########################################################
# NewPostProcessing.interface(PREDICTED_DEVEL_FILE, new-post-process-output.xml)
# gifxmlToGenia("new-post-process-output.xml", "new-post-process-geniaformat")
# evaluateSharedTask("new-post-process-geniaformat", 1)

# Compare outputs and make sure approx span & approx recursive f-score
# is higher for the new post-processing!!!