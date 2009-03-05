pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
python Core/ExampleBuilder.py -b MultiEdgeExampleBuilder -x "style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures" -i $1 -o $2
popd
