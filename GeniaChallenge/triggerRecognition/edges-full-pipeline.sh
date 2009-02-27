TEST_FILE="$1"
CLASSIFIER_PARAMS="predefined:$2"
OUTDIR="$3"
GOLD_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"

pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python SplitAnalysis.py -b MultiEdgeExampleBuilder -x "style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures" -c SVMMultiClassClassifier -e AveragingMultiClassEvaluator -y $CLASSIFIER_PARAMS -s $TEST_FILE -o $OUTDIR -m $OUTDIR/edges.xml -p split-Charniak-Lease
python Evaluators/EvaluateInteractionXML.py -i $OUTDIR/edges.xml -g $GOLD_FILE
popd
pushd ~/cvs_checkout/GeniaChallenge/unflattening
python prune.py -c -i $OUTDIR/edges.xml -o $OUTDIR/pruned.xml
python unflatten.py -i $OUTDIR/pruned.xml -o $OUTDIR/unflattened.xml
python ../formatConversion/gifxmlToGenia.py -i $OUTDIR/unflattened.xml -o $OUTDIR/final
popd
