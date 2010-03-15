rm featureNames
python crf.py --buildgztr=maingztr-everything < everything.xml
python crf.py --maxsent=-1 --train --loadgztr=maingztr-everything --classNames=classNames --featureNames=featureNames < everything.xml > everything.ibo
python crf.py --declog=test.log --train --loadgztr=maingztr-everything --classNames=classNames --featureNames=featureNames --noSaveFNames < test.xml > test.ibo

### Model building

./svm-model.sh everything.ibo everything-115000-final.model -c 115000
#Reading training examples... (33525 examples) done
#Training set properties: 60574 features, 10 classes


### Prediction

./predict.sh test.ibo everything-115000-final.model test-filippredictions.xml
python expandEntities.py --buildgztr < everything.xml > allTriggers-everything
#Using Jari's final prediction & lambda=0.2 and B=0.7
./merge-jari-filip-predictions.sh 0.2 0.7 test-filippredictions.xml /usr/share/biotext/GeniaChallenge/xml/jari-results/090305-jari-test-triggers/jari-test-triggers-with-merged.xml test-triggers-final.xml

#test-triggers-final.xml is the result
