TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,200000,500000,1000000,5000000,10000000;timeout:6000"
if [ "$1" == "mini" ]; then
	TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
	TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
	CLASSIFIER_PARAMS="c:1000,10000,100000,1000000;timeout:600"
fi
if [ -n "$2" ]; then
	CLASSIFIER_PARAMS="c:$2"
fi

pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python SplitAnalysis.py -b GeneralEntityTypeRecognizer -x "style:typed" -c SVMMultiClassClassifier -e AveragingMultiClassEvaluator -y $CLASSIFIER_PARAMS -i $TRAIN_FILE -s $TEST_FILE -o /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers -m /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers-with-merged.xml -p split-Charniak-Lease
python ../../../CommonUtils/InteractionXML/SplitMergedElements.py -i /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers-with-merged.xml -o /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers.xml
popd
cp nohup.out /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/nohup.out
