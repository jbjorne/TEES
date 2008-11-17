python BioInferGraphToInteractionXML.py -o BioInfer.xml
python ../../../../../CommonUtils/InteractionXML/MergeDuplicateEntities.py -i BioInfer.xml -o BioInfer.xml
python GroupSentencesByDocument.py -i BioInfer.xml -o BioInfer.xml
python ../../../../../CommonUtils/InteractionXML/RecalculateIds.py -i BioInfer.xml -o BioInfer.xml

# Copy parses
#python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t medpost -p stanford_medpost
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t bioinfer_gs -p bioinfer_gs
#python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t bioinfer_gs -p bioinfer_parallel
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallel.xml -o BioInfer.xml -t bioinfer_gs -p bioinfer_uncollapsed_stanford
python ../../../../../CommonUtils/InteractionXML/CopyParse.py -i BioInfer.xml -s /usr/share/biotext/ComplexPPI/BioInferCLAnalysis_split_SMBM_version.xml -o BioInfer.xml -t Charniak-Lease -p Charniak-Lease

# Split parses
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t bioinfer_gs -p bioinfer_gs -s split_bioinfer_gs -n split_bioinfer_gs -o BioInfer.xml
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t bioinfer_gs -p bioinfer_uncollapsed_stanford -s split_bioinfer_uncollapsed_stanford -n split_bioinfer_uncollapsed_stanford -o BioInfer.xml
python ../../../../../PPI_Learning/Analysers/ProteinNameSplitter.py -f BioInfer.xml -t Charniak-Lease -p Charniak-Lease -s split_Charniak-Lease -n split_Charniak-Lease -o BioInfer.xml

# Detect heads
python FindHeads.py -i BioInfer/BioInfer.xml -t split_bioinfer_gs -p split_bioinfer_gs -o BioInfer/BioInferWithHeads.xml
