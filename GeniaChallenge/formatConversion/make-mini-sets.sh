# Mini sets for faster development and testing
echo "Making mini-sets"
pushd ~/cvs_checkout/CommonUtils/InteractionXML
# mini files for flattened
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/train.xml -o /usr/share/biotext/GeniaChallenge/xml/train-mini.xml -s 1 -f 0.025
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/devel.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-mini.xml -s 1 -f 0.05
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/train12.xml -o /usr/share/biotext/GeniaChallenge/xml/train12-mini.xml -s 1 -f 0.125
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/devel12.xml -o /usr/share/biotext/GeniaChallenge/xml/devel12-mini.xml -s 1 -f 0.25

python DeleteElements.py -i /usr/share/biotext/GeniaChallenge/xml/devel-mini.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-mini-empty.xml -r "{\"pair\":{},\"interaction\":{},\"entity\":{\"isName\":\"False\"}}"
python DeleteElements.py -i /usr/share/biotext/GeniaChallenge/xml/devel12-mini.xml -o /usr/share/biotext/GeniaChallenge/xml/devel12-mini-empty.xml -r "{\"pair\":{},\"interaction\":{},\"entity\":{\"isName\":\"False\"}}"

# mini files for nonflattened
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/train-with-duplicates.xml -o /usr/share/biotext/GeniaChallenge/xml/train-with-duplicates-mini.xml -s 1 -f 0.025
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini.xml -s 1 -f 0.05
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/train-with-duplicates12.xml -o /usr/share/biotext/GeniaChallenge/xml/train-with-duplicates12-mini.xml -s 1 -f 0.125
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates12.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates12-mini.xml -s 1 -f 0.25

python DeleteElements.py -i /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini-empty.xml -r "{\"pair\":{},\"interaction\":{},\"entity\":{\"isName\":\"False\"}}"

# other empty sets
python DeleteElements.py -i /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-empty.xml -r "{\"pair\":{},\"interaction\":{},\"entity\":{\"isName\":\"False\"}}"

popd