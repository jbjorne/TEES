TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,200000,500000,1000000,5000000,10000000;timeout:6000"
if [[ "$1" =~ "mini" ]]; then
	TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
	TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers-mini.xml"
	GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
	#CLASSIFIER_PARAMS="c:10,100,1000,10000,100000,1000000;timeout:600"
	CLASSIFIER_PARAMS="c:10,100,1000,10000;timeout:600"
fi
if [[ "$1" =~ "empty" ]]; then
	TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini-empty.xml"
fi
if [[ "$1" =~ "final" ]]; then
	TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/everything.xml"
	TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers.xml"
	GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
fi

if [ -n "$3" ]; then
	CLASSIFIER_PARAMS="$3"
fi

PIPELINE="SplitAnalysis.py"
if [ "$2" == "twofile" ]; then
	PIPELINE="TwoFileAnalysis.py"
fi

pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python $PIPELINE -b MultiEdgeExampleBuilder -x "style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures" -c SVMMultiClassClassifier -e AveragingMultiClassEvaluator -y $CLASSIFIER_PARAMS -i $TRAIN_FILE -g $GOLD_TEST_FILE -s $TEST_FILE -o /usr/share/biotext/GeniaChallenge/xml/jari-edges-from-predicted-entities -m /usr/share/biotext/GeniaChallenge/xml/jari-edges-from-predicted-entities/jari-edges-from-predicted-entities.xml -p split-Charniak-Lease
python Evaluators/EvaluateInteractionXML.py -i /usr/share/biotext/GeniaChallenge/xml/jari-edges-from-predicted-entities/jari-edges-from-predicted-entities.xml -g $GOLD_TEST_FILE
popd