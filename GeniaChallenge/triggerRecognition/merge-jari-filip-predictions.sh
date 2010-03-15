#!/bin/bash

. config.sh

L=$1
B1=$2
B2=$2

FILE1=$3
FILE2=$4
RES=$5

echo "merging"
python merge-triggers.py --l=$L --b1=$B1 --b2=$B2 $FILE1 $FILE2 > $RES--merged
echo "expanding entities"
echo "Using train gazzetteer!"
python expandEntities.py --gztr allTriggers-train < $RES--merged > $RES--merged--expanded

echo "recalculating ids"
python ~/cvs_checkout/CommonUtils/InteractionXML/RecalculateIds.py -i $RES--merged--expanded -o $RES--merged--expanded--recalculated

echo "splitting elements"
python ~/cvs_checkout/CommonUtils/InteractionXML/SplitMergedElements.py -i $RES--merged--expanded--recalculated  -o $RES--merged--expanded--recalculated--split

echo "finding heads"
python ~/cvs_checkout/JariSandbox/ComplexPPI/Source/Utils/FindHeads.py -i $RES--merged--expanded--recalculated--split -o $RES -p split-Charniak-Lease -t split-Charniak-Lease

#python ~/cvs_checkout/JariSandbox/ComplexPPI/Source/Evaluators/EvaluateInteractionXML.py -i $RES -g $TEST > eval-$TESTBASE-final-split-heads-$L-$B1-$B2.xml

echo "The final mixed file is in $RES"

