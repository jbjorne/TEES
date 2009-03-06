pushd ~/cvs_checkout/JariSandbox/ComplexPPI/Source
if [ -n "$3" ]; then
	python Core/ExampleBuilder.py -b MultiEdgeExampleBuilder -x "style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures" -i $1 -o $2 -d $3
else
	python Core/ExampleBuilder.py -b MultiEdgeExampleBuilder -x "style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures" -i $1 -o $2
fi
popd
