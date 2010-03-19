#!/bin/bash

echo "Downloading linux binaries of SVM-Multiclass from www.joachims.org"
echo "Make sure you agree with the license conditions"

# Put SVM-Multiclass in a subdirectory in the data directory
mkdir -p data/svmmc
pushd data/svmmc
# Download and uncompress the Linux binaries
wget http://download.joachims.org/svm_multiclass/current/svm_multiclass_linux.tar.gz
tar zxf svm_multiclass_linux.tar.gz
# Configure SVM-Multiclass directory in Settings.py
cd ../../src
perl -pi -e 's/SVMMultiClassDir = None/SVMMultiClassDir = relPath("..\/data\/svmmc")/' Settings.py
popd

echo "Done"
