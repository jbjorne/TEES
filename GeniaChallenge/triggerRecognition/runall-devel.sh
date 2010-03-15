### Data preparation

rm featureNames
python crf.py --buildgztr=maingztr-train < train.xml
python crf.py --maxsent=-1 --train --loadgztr=maingztr-train --classNames=classNames --featureNames=featureNames < train.xml > train.ibo
python crf.py --declog=devel.log --train --loadgztr=maingztr-train --classNames=classNames --featureNames=featureNames --noSaveFNames < devel.xml > devel.ibo

### Model building

./svm-model.sh train.ibo train-100000-final.model -c 100000
#Reading training examples... (33525 examples) done
#Training set properties: 60574 features, 10 classes


### Prediction

./predict.sh devel.ibo train-100000-final.model devel-filippredictions.xml
python expandEntities.py --buildgztr < train.xml > allTriggers-train
#Using Jari's final prediction & lambda=0.2 and B=0.7
./merge-jari-filip-predictions.sh 0.2 0.7 devel-filippredictions.xml /usr/share/biotext/GeniaChallenge/xml/jari-results/090316-jari-devel-triggers/jari-devel-triggers-with-merged.xml devel-triggers-final.xml

./edges-full-pipeline.sh /home/ginter/cvs_checkout/GeniaChallenge/triggerRecognition/devel-triggers-final.xml /usr/share/biotext/GeniaChallenge/xml/jari-results/090306-jari-train-vs-devel-edges `pwd`/SYSTRIGGERSONDEVEL
