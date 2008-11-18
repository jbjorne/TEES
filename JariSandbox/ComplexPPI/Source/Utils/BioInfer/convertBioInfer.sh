python BioInferGraphToInteractionXML.py -i /usr/share/biotext/BinaryBioInfer/bioinfer.nestingResolved.anonymousResolved.relaxed.r205.xml -o BioInfer.xml
python ../../../../../CommonUtils/InteractionXML/MergeDuplicateEntities.py -i BioInfer.xml -o BioInfer.xml
python GroupSentencesByDocument.py -i BioInfer.xml -o BioInfer.xml
python ../../../../../CommonUtils/InteractionXML/RecalculateIds.py -i BioInfer.xml -o BioInfer.xml

# Copy parses
#python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t medpost -p stanford_medpost
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t bioinfer_gs -p bioinfer_gs
#python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t bioinfer_gs -p bioinfer_parallel
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t bioinfer_gs -p bioinfer_uncollapsed_stanford
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/ComplexPPI/BioInferCLAnalysis_split_SMBM_version.xml -o BioInfer.xml -t Charniak-Lease -p Charniak-Lease

# Create union parse
python ../../../../../CommonUtils/InteractionXML/MergeParse.py -i BioInfer.xml -p bioinfer_gs -q bioinfer_uncollapsed_stanford -n bioinfer_union -o BioInfer.xml

# Split parses
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t bioinfer_gs -p bioinfer_gs -s split_bioinfer_gs -n split_bioinfer_gs -o BioInfer.xml
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t bioinfer_gs -p bioinfer_uncollapsed_stanford -s split_bioinfer_uncollapsed_stanford -n split_bioinfer_uncollapsed_stanford -o BioInfer.xml
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t bioinfer_gs -p bioinfer_union -s split_bioinfer_union -n split_bioinfer_union -o BioInfer.xml
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t Charniak-Lease -p Charniak-Lease -s split_Charniak-Lease -n split_Charniak-Lease -o BioInfer.xml

# Detect heads
cd ..
python FindHeads.py -i BioInfer/BioInfer.xml -t split_bioinfer_gs -p split_bioinfer_gs -o BioInfer/BioInfer.xml

# Make hidden and visible subset
cd BioInfer
python ../../../../../CommonUtils/InteractionXML/Subset.py -i BioInfer.xml -o BioInferVisible.xml -d ../../../../../BioInfer/data/BioInfer_id_visible.txt
python ../../../../../CommonUtils/InteractionXML/Subset.py -i BioInfer.xml -o BioInferHidden.xml -d ../../../../../BioInfer/data/BioInfer_id_visible.txt -v
cd ..

# Visualize corpus
cd ..
python VisualizeCorpus.py -i Utils/BioInfer/BioInfer.xml -t split_bioinfer_gs -p split_bioinfer_gs -o Utils/BioInfer/Visualization
cd Utils/BioInfer