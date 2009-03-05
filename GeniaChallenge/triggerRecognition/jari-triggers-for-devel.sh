TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/everything.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/test.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/test.xml"
CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,200000,500000,1000000,5000000,10000000;timeout:6000"
if [[ "$1" =~ "mini" ]]; then
	TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
	TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
	GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
	CLASSIFIER_PARAMS="c:1000,10000,100000,1000000;timeout:600"
fi
if [[ "$1" =~ "empty" ]]; then
	TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini-empty.xml"
fi

if [ -n "$3" ]; then
	CLASSIFIER_PARAMS="$3"
fi

PIPELINE="SplitAnalysis.py"
if [ "$2" == "twofile" ]; then
	PIPELINE="TwoFileAnalysis.py"
fi

pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python $PIPELINE -b GeneralEntityTypeRecognizer -x "style:typed" -c SVMMultiClassClassifier -e AveragingMultiClassEvaluator -y $CLASSIFIER_PARAMS -i $TRAIN_FILE -s $TEST_FILE -o /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers -m /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers-with-merged.xml -p split-Charniak-Lease
python ../../../CommonUtils/InteractionXML/RecalculateIds.py -i /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers-with-merged.xml -o /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers-with-merged-new-ids.xml
python ../../../CommonUtils/InteractionXML/SplitMergedElements.py -i /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers-with-merged-new-ids.xml -o /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers.xml
python Evaluators/EvaluateInteractionXML.py -i /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers.xml -g $GOLD_TEST_FILE
popd
cp nohup.out /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/nohup.out
