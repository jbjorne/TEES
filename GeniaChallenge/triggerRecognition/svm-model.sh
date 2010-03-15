#!/bin/bash

#/usr/share/biotext/mallet-2.0-RC2/bin/simple-tagger.sh --train false --model-file triggercrf devel.feat > devel.classified
IBOFILE=$1
MODELFILE=$2
shift
shift


SVM=./svmmulticlass

OPTIONS=$*
echo "Building $MODELFILE from $IBOFILE with options $*"
$SVM/svm_multiclass_learn $OPTIONS $IBOFILE $MODELFILE

