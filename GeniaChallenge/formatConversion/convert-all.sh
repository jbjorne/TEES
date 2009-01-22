#!/bin/bash

DDIR=/usr/share/biotext/GeniaChallenge/orig-data
THIS=`pwd`

cd $DDIR

echo "Total number of documents `ls *.a1 | wc -l`"
echo "Training: 600"
echo "Devel: 200"


# Division to sets, only needed once
# ls *.a1 | perl -pe 's/\.a1//' | awk '{print rand(), $1 }' | sort -n | cut -f 2 -d' ' > IDsSCRAMBLED
# cat IDsSCRAMBLED | head -n 600 > IDsTRAIN
# cat IDsSCRAMBLED | tail -n 200 > IDsDEVEL

cat IDsTRAIN | xargs python $THIS/geniaToGifxml.py -i . -o ../xml/train.xml 

