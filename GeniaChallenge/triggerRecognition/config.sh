TRAIN=/usr/share/biotext/GeniaChallenge/xml/train.xml
TEST=/usr/share/biotext/GeniaChallenge/xml/devel.xml

JARIPREDICTIONS=/usr/share/biotext/GeniaChallenge/xml/jari-results/090303-jari-devel-triggers/jari-devel-triggers-with-merged.xml

TRAINBASENAME=`basename $TRAIN`
TESTBASENAME=`basename $TEST`

TRAINBASE=${TRAINBASENAME%.xml}
TESTBASE=${TESTBASENAME%.xml}

C=100000

