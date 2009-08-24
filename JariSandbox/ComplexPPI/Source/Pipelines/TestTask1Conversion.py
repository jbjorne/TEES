from Pipeline import *
import os

WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/recall-boost-split-McClosky"

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log()

print "Old:"
evaluateSharedTask("geniaformat", 1)
print "New:"
gifxmlToGenia("unflattened.xml", "geniaformat-new", 1)
evaluateSharedTask("geniaformat-new", 1)