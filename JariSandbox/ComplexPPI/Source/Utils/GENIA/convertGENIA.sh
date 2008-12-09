python GENIAToInteractionXML.py -i /usr/share/biotext/genia/treebank/Stanford-GTB/GTB_BI-xml-collapsed-realigned.xml -e /usr/share/biotext/genia/GENIA_101108/GENIA_event_sentence_removed -o GENIA.xml
perl -pi -e 's/parser="gold"/parser="gold_collapsed"/g' GENIA.xml

python GENIAToInteractionXML.py -i /usr/share/biotext/genia/treebank/Stanford-GTB/GTB_BI-xml-uncollapsed-realigned.xml -e /usr/share/biotext/genia/GENIA_101108/GENIA_event_sentence_removed -o GENIA_uncollapsed.xml
perl -pi -e 's/parser="gold"/parser="gold_uncollapsed"/g' GENIA_uncollapsed.xml

# Copy parses
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i GENIA.xml -s GENIA_uncollapsed.xml -o GENIA.xml -t gold -p gold_uncollapsed
#python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i GENIA.xml -s /usr/share/biotext/ComplexPPI/Genia_CL.xml -o GENIA.xml -t Charniak-Lease -p Charniak-Lease
# CopyParse won't work because the origIds in Genia_CL do not match those in GENIA.xml
# So let's use the more primitive method: 
python ../../../../../CommonUtils/InteractionXML/Tools/CopyElements.py -s /usr/share/biotext/ComplexPPI/Genia_CL.xml -t GENIA.xml -o GENIA.xml -p "document/sentence" -m "id,text" -e "sentenceanalyses/parses/parse" -i "{'parser':'Charniak-Lease'}"
python ../../../../../CommonUtils/InteractionXML/Tools/CopyElements.py -s /usr/share/biotext/ComplexPPI/Genia_CL.xml -t GENIA.xml -o GENIA.xml -p "document/sentence" -m "id,text" -e "sentenceanalyses/tokenizations/tokenization" -i "{'tokenizer':'Charniak-Lease'}"

# Remove duplicates
python ../../../../../CommonUtils/InteractionXML/MergeDuplicateEntities.py -i GENIA.xml -o GENIA.xml
python ../../../../../CommonUtils/InteractionXML/RecalculateIds.py -i GENIA.xml -o GENIA.xml

# Create union parse
python ../../../../../CommonUtils/InteractionXML/MergeParse.py -i GENIA.xml -p gold_collapsed -q gold_uncollapsed -n gold_union -o GENIA.xml

# Remove duplicate dependencies
python ../../../../../CommonUtils/InteractionXML/RemoveDuplicateDependencies.py -i GENIA.xml -o GENIA.xml

if [ "$1" == "no_split" ]; then
	# Detect heads
	cd ..
	python FindHeads.py -i GENIA/GENIA.xml -t gold -p gold_collapsed -o GENIA/GENIA.xml
	
	# Make hidden and visible subset
	cd GENIA
	python ../../../../../CommonUtils/InteractionXML/Subset.py -i GENIA.xml -o GENIAVisible.xml -f 0.5
	python ../../../../../CommonUtils/InteractionXML/Subset.py -i GENIA.xml -o GENIAHidden.xml -f 0.5 -v
	
	# Visualize
	cd ../..
	python VisualizeCorpus.py -i Utils/GENIA/GENIA.xml -t gold -p gold_collapsed -o Utils/GENIA/Visualization
	cd Utils/GENIA
else
	# Split parses
	python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f GENIA.xml -t gold -p gold_collapsed -s split_gold_collapsed -n split_gold_collapsed -o GENIA.xml
	python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f GENIA.xml -t gold -p gold_uncollapsed -s split_gold_uncollapsed -n split_gold_uncollapsed -o GENIA.xml
	python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f GENIA.xml -t gold -p gold_union -s split_gold_union -n split_gold_union -o GENIA.xml
	python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f GENIA.xml -t Charniak-Lease -p Charniak-Lease -s split_Charniak-Lease -n split_Charniak-Lease -o GENIA.xml
	
	# Detect heads
	cd ..
	python FindHeads.py -i GENIA/GENIA.xml -t split_gold_collapsed -p split_gold_collapsed -o GENIA/GENIA.xml
	
	# Make hidden and visible subset
	cd GENIA
	python ../../../../../CommonUtils/InteractionXML/Subset.py -i GENIA.xml -o GENIAVisible.xml -f 0.5
	python ../../../../../CommonUtils/InteractionXML/Subset.py -i GENIA.xml -o GENIAHidden.xml -f 0.5 -v
	
	# Visualize
	cd ../..
	python VisualizeCorpus.py -i Utils/GENIA/GENIA.xml -t split_gold_union -p split_gold_union -o Utils/GENIA/Visualization
	cd Utils/GENIA
fi