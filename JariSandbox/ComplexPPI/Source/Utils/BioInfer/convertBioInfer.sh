python BioInferGraphToInteractionXML.py -o BioInfer.xml
python ../../../../../CommonUtils/InteractionXML/MergeDuplicateEntities.py -i BioInfer.xml -o BioInfer.xml
