python GENIAToInteractionXML.py -o GENIA.xml
cd ../..
python VisualizeCorpus.py -i Utils/GENIA/GENIA.xml -t gold -p gold -o Utils/GENIA/Visualization
cd Utils/GENIA