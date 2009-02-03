# Mini sets for faster development and testing
echo "Making mini-sets"
pushd ~/cvs_checkout/CommonUtils/InteractionXML
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/train.xml -o /usr/share/biotext/GeniaChallenge/xml/train-mini.xml -f 0.05
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/devel.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-mini.xml -f 0.1
popd