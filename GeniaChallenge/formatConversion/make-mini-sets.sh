# Mini sets for faster development and testing
echo "Making mini-sets"
pushd ~/cvs_checkout/CommonUtils/InteractionXML
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/train.xml -o /usr/share/biotext/GeniaChallenge/xml/train-mini.xml -s 1 -f 0.025
python Subset.py -i /usr/share/biotext/GeniaChallenge/xml/devel.xml -o /usr/share/biotext/GeniaChallenge/xml/devel-mini.xml -s 1 -f 0.05
popd