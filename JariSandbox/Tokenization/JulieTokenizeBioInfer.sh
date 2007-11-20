mkdir JulieInput
mkdir JulieOutput
cp BioInferSentences.txt JulieInput/BioInferSentences.txt
java -jar /home/jarib/Julie/JTBDv1.6/JTBD-1.6.jar p JulieInput JulieOutput /home/jarib/Julie/JTBDv1.6/models/JULIE_life-science-1.6.mod.gz
cp JulieOutput/BioInferSentences.txt BioInferJulieTokenization.txt
rm -R JulieInput
rm -R JulieOutput
