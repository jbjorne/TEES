pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python Core/ExampleBuilder.py -b GeneralEntityTypeRecognizer -x "style:typed" -i $1 -o $2-with-merged
python ../../../CommonUtils/InteractionXML/SplitMergedElements.py -i $2-with-merged -o $2
popd
