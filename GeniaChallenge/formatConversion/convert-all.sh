#!/bin/bash

DIRTRAIN=/usr/share/biotext/GeniaChallenge/orig-data
DIRTEST=/usr/share/biotext/GeniaChallenge/test-data
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
    DDIR=$4 
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
    perl -pi -e 's/\"(Theme|Cause|Site|CSite|AtLoc|ToLoc)[0-9]+\"/\"$1\"/g' $DST
    
    rm -f $TMP1 $TMP2
}

### Converts the TRAIN/DEVEL data for task 1
# convert IDsTRAIN train.xml "" $DIRTRAIN
# convert IDsDEVEL devel.xml "" $DIRTRAIN
# convert IDsEVERYTHING everything.xml "" $DIRTRAIN
# convert IDsTRAIN train-with-duplicates.xml -p $DIRTRAIN
# convert IDsDEVEL devel-with-duplicates.xml -p $DIRTRAIN
# convert IDsEVERYTHING everything-with-duplicates.xml -p $DIRTRAIN

### Converts the TEST data
#convert IDsTEST test.xml "" $DIRTEST


### Converts the TRAIN/DEVEL data for task 2
convert IDsTRAIN train12.xml "-t 12" $DIRTRAIN
convert IDsDEVEL devel12.xml "-t 12" $DIRTRAIN
convert IDsEVERYTHING everything12.xml "-t 12" $DIRTRAIN
convert IDsTRAIN train-with-duplicates12.xml "-t 12 -p" $DIRTRAIN
convert IDsDEVEL devel-with-duplicates12.xml "-p -t 12" $DIRTRAIN
convert IDsEVERYTHING everything-with-duplicates12.xml "-t 12 -p" $DIRTRAIN

#### I don't know what this is:
# # Update the mini-sets
# cd $THIS
# ./make-mini-sets.sh
