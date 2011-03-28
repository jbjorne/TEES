#!/bin/bash

A=/home/jari/cvs_checkout/JariSandbox/ComplexPPI/Source/Tools/GeniaEventsToSharedTask.py
GEDIR=/home/jari/biotext/BioNLP2011/data/main-tasks/GE
# nodup
python $A -i $GEDIR/GE-devel-nodup.xml -o $GEDIR/GE-devel-nodup-extratrig.xml
python $A -i $GEDIR/GE-train-nodup.xml -o $GEDIR/GE-train-nodup-extratrig.xml
python $A -i $GEDIR/GE-devel-and-train-nodup.xml -o $GEDIR/GE-devel-and-train-nodup-extratrig.xml
# with duplicates
python $A -i $GEDIR/GE-devel.xml -o $GEDIR/GE-devel-extratrig.xml
python $A -i $GEDIR/GE-train.xml -o $GEDIR/GE-train-extratrig.xml
python $A -i $GEDIR/GE-devel-and-train.xml -o $GEDIR/GE-devel-and-train-extratrig.xml
# link for a dummy extratrig-file
ln -s $GEDIR/GE-devel-nodup-empty.xml $GEDIR/GE-devel-nodup-extratrig-empty.xml

