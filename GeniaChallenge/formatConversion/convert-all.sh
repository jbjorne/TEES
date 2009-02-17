#!/bin/bash

DDIR=/usr/share/biotext/GeniaChallenge/orig-data
THIS=`pwd`

echo "Total number of documents `ls $DDIR/*.a1 | wc -l`"
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
    
    # Split tokenization
    echo "Running protein name splitter"
    python $HOME/cvs_checkout/PPI_Learning/Analysers/ProteinNameSplitter.py -f $DST -o $DST -p Charniak-Lease -t Charniak-Lease -s split-Charniak-Lease -n split-Charniak-Lease
    
    # Find head token offsets
    python $HOME/cvs_checkout/JariSandbox/ComplexPPI/Source/Utils/FindHeads.py -i $DST -o $DST -p split-Charniak-Lease -t split-Charniak-Lease
    
    # Remove unneeded ThemeX and CauseX
    echo "Removing ThemeX and CauseX"
    perl -pi -e 's/Theme2/Theme/g' $DST
    perl -pi -e 's/Theme3/Theme/g' $DST
    perl -pi -e 's/Theme4/Theme/g' $DST
    perl -pi -e 's/Cause2/Cause/g' $DST
    
    rm -f $TMP1 $TMP2
}

convert IDsTRAIN train.xml ""
#convert IDsDEVEL devel.xml ""
#convert IDsEVERYTHING everything.xml ""
#convert IDsTRAIN train-with-duplicates.xml -p
#convert IDsDEVEL devel-with-duplicates.xml -p
#convert IDsEVERYTHING everything-with-duplicates.xml -p

# Update the mini-sets
cd $THIS
./make-mini-sets.sh
