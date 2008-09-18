echo binary-classification for GENIA
python SplitAnalysis.py -b SingleEdgeExampleBuilder -x "style:binary,headsOnly" -y "c:1" -i /usr/share/biotext/ComplexPPI/GENIAForComplexPPIVisible.xml -t gold -p gold

echo type and direction classification for GENIA
python SplitAnalysis.py -b SingleEdgeExampleBuilder -x "style:typed,directed,headsOnly" -y "c:10000,50000,70000,85000,90000,95000" -o temp -e AveragingMultiClassEvaluator -c SVMMultiClassClassifier -i /usr/share/biotext/ComplexPPI/GENIAForComplexPPIVisible.xml -t gold -p gold

python SplitAnalysis.py -b MultiEdgeExampleBuilder -x "length:1,2,3,4,5" -y "c:85000" -c SVMMultiClassClassifier -e AveragingMultiClassEvaluator -o temp
