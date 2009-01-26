#!/bin/bash

DDIR=/usr/share/biotext/GeniaChallenge/orig-data
THIS=`pwd`

echo "Total number of documents `ls *.a1 | wc -l`"
echo "Training: 600"
echo "Devel: 200"


# Division to sets, only needed once
# ls *.a1 | perl -pe 's/\.a1//' | awk '{print rand(), $1 }' | sort -n | cut -f 2 -d' ' > IDsSCRAMBLED
# cat IDsSCRAMBLED | head -n 600 > IDsTRAIN
# cat IDsSCRAMBLED | tail -n 200 > IDsDEVEL



function convert {
    SRC=$1 #source ids
    DST=$2 #destination XML
    OPTS=$3 #options given to geniaTpGifxml.py
    cd $DDIR

    TMP1=`tempfile`
    TMP2=`tempfile`
    cat $SRC | xargs python $THIS/geniaToGifxml.py $OPTS -i . -o $TMP1
    cd ../xml
    cat $TMP1 | python $THIS/readTokenization.py -d $DDIR > $TMP2
    python $HOME/cvs_checkout/CommonUtils/InteractionXML/RecalculateIds.py -i $TMP2 -o $DST
    rm -f $TMP1 $TMP2
}

convert IDsTRAIN train.xml ""
convert IDsDEVEL devel.xml ""
convert IDsTRAIN train-with-duplicates.xml -p
convert IDsDEVEL devel-with-duplicates.xml -p
