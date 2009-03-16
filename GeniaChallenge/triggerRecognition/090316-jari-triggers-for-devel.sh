# Final files for the winning submission
# jari-results/090303-jari-devel-triggers
#  -the actual run still used the 50/50 split on train for param optimization (c=200000)
#  -data was moved to Louhi for proper param optimization of train vs. devel (c=300000)
# jari-results/090304-jari-everything-triggers
#  -the actual run didn't finish 
#  -all models were built on Louhi
#  -Correct model was chosen based on 090303-jari-devel-triggers param opt on Louhi
#  -classifier/model is a link pointing to louhistuff/model-c_300000
# jari-final-triggers
#  -trigger examples for test set
# jari-results/090305-jari-test-triggers
#  -based on jari-final-triggers and 090304-jari-everything-triggers model
#  -presumably the file sent to filip
# FINALSUBMISSIONDATA/test-triggers-final.xml
#  -Filip's final mixed trigger file
# jari-final-test-edges
#  -edge examples for test set based on Filip's final merged trigger xml file
#

# This file is used to produce devel set triggers for Filip to mix

TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml:/usr/share/biotext/GeniaChallenge/xml/jari-results/090303-jari-devel-triggers-louhi/louhi/test.ibo"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
CLASSIFIER_PARAMS="predefined:/usr/share/biotext/GeniaChallenge/xml/jari-results/090303-jari-devel-triggers-louhi"
OUTDIR="/usr/share/biotext/GeniaChallenge/xml/jari-results/090316-jari-devel-triggers"

pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python TwoFileAnalysis.py -b GeneralEntityTypeRecognizer -x "style:typed" -c SVMMultiClassClassifier -e AveragingMultiClassEvaluator -y $CLASSIFIER_PARAMS -s $TEST_FILE -o $OUTDIR -m $OUTDIR/jari-devel-triggers-with-merged.xml -p split-Charniak-Lease
python ../../../CommonUtils/InteractionXML/RecalculateIds.py -i $OUTDIR/jari-devel-triggers-with-merged.xml -o $OUTDIR/jari-devel-triggers-with-merged-new-ids.xml
python ../../../CommonUtils/InteractionXML/SplitMergedElements.py -i $OUTDIR/jari-devel-triggers-with-merged-new-ids.xml -o $OUTDIR/jari-devel-triggers.xml
python Evaluators/EvaluateInteractionXML.py -i $OUTDIR/jari-devel-triggers.xml -g $GOLD_TEST_FILE
popd
cp nohup.out $OUTDIR/nohup.out
