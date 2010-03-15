#!/bin/bash

. config.sh

echo "Train file: $TRAIN   Test file: $TEST"

#rm -f maingztr featureNames
echo "Building the main gztr"
rm featureNames
python crf.py --buildgztr=maingztr-everything < everything.xml

echo "Using maingztr-everything"
#python crf.py --maxsent=-1 --train --loadgztr=maingztr --classNames=classNames --featureNames=featureNames < $TRAIN > $TRAINBASE.ibo

python crf.py --maxsent=-1 --train --loadgztr=maingztr-everything --classNames=classNames --featureNames=featureNames < everything.xml > everything.ibo

#python crf.py --declog=devel.log --train --loadgztr=maingztr --classNames=classNames --featureNames=featureNames --noSaveFNames < $TEST > $TESTBASE.ibo

python crf.py --declog=test.log --train --loadgztr=maingztr-everything --classNames=classNames --featureNames=featureNames --noSaveFNames < test.xml > test.ibo

#echo "Feature files written to $TRAINBASE.ibo and $TESTBASE.ibo in `pwd`"
