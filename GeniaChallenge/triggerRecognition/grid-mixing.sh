#!/bin/bash

. config.sh

THIS=`pwd`

for L in 0.2
  do
  for R in 0.6 0.5
  do
    ./merge-jari-filip-predictions.sh $L $R
    ./edges-full-pipeline.sh $THIS/$TESTBASE-final-split-heads-$L-$R-$R.xml /usr/share/biotext/GeniaChallenge/xml/jari-results/090303-jari-edges-from-predicted-entities $THIS/MIXTEST-$L-$R > stdout-$L-$R 2> stderr-$L-$R
  done
done

