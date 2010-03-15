#!/bin/bash

SVM=./svmmulticlass

IBOFILE=$1
MODELFILE=$2
RESULT=$3

model=$1
OUT=$2

$SVM/svm_multiclass_classify $IBOFILE $MODELFILE $RESULT--classified
python merge-prediction.py ${IBOFILE%.ibo}.log $RESULT--classified > $RESULT--allclassifications
cat ${IBOFILE%.ibo}.xml | egrep -v '<entity .* isName=\"False\"' | egrep -v '<interaction ' | python create-entities.py --classNames=classNames --predictionFile=$RESULT--allclassifications > $RESULT--noheads

python ~/cvs_checkout/JariSandbox/ComplexPPI/Source/Utils/FindHeads.py -i $RESULT--noheads -o $RESULT -p split-Charniak-Lease -t split-Charniak-Lease

python ~/cvs_checkout/JariSandbox/ComplexPPI/Source/Evaluators/EvaluateInteractionXML.py -i $RESULT -g ${IBOFILE%.ibo}.xml

