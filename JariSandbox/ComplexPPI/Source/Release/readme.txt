###############################################################################
University of Turku BioNLP'09 Event Detection Software

Preliminary Release

December 2009
###############################################################################

Index
1. Introduction
2. Related Publications
3. Overview of the Software
4. How to Use It

# 1. Introduction #############################################################

This software package contains the system designed to detect biomedical events as defined in the BioNLP'09 Shared Task. It combines machine learning and rule based systems, using Joachmis SVM-Multiclass for the machine learning components.

This preliminary release contains software required for detecting events as defined in the tasks 1 & 2 of the shared task, starting from textual data in the interaction XML (see section 5) format. Software for task 3 will be included in the final release.

This preliminary release is both badly documented, potentially buggy and quite possibly extremely annoying to use. Please bear with us, the final release will be made ASAP in January 2010 :-)

# 2. Related Publications #####################################################

This software release covers the following publications:

Björne, Jari and Ginter, Filip and Heimonen, Juho and Pyysalo, Sampo and Salakoski, Tapio: Learning to Extract Biological Event and Relation Graphs. Proceedings of NODALIDA'09. 2009

Björne, Jari and Heimonen, Juho and Ginter, Filip and Airola, Antti and Pahikkala, Tapio and Salakoski, Tapio: Extracting Complex Biological Events with Rich Graph-Based Feature Sets. Proceedings of the BioNLP'09 Shared Task on Event Extraction. 2009, pp. 10-18

Björne, Jari and Heimonen, Juho and Ginter, Filip and Airola, Antti and Pahikkala, Tapio and Salakoski, Tapio: Extracting Contextualized Complex Biological Events with Rich Graph-Based Feature Sets. Journal of Computational Intelligence. (To appear)

# 3. Overview of the Software #################################################

The main idea behind the software architecture of this system is to separate and abstract the machine learning away from the actual textual data. In this, the system follows traditional machine learning approaches where all kinds of data are handled through a generic feature vector representation. The learning component is a thin wrapper around the SVM-multiclass, and can be replaced with other learning systems. All the components should be independent, so different components can be mixed to perform different experiments.

The overall structure of the system goes like this (<>=process, []=data, V=arrow. Hooray for ASCII art!).

Fig 1: Classifying with the system

	[Interaction-XML with parses and named entities]
	       V
	<Trigger example generation>
	       V
	<Trigger example classification (SVM-multiclass)>
	       V
	<Insertion of predicted triggers into Interaction XML>
	       V
	[Interaction-XML with parses, named entities and triggers]
	       V
	<Edge (Event argument) example generation>
	       V
	<Edge example classification (SVM-multiclass)>
	       V
	<Insertion of predicted edges into Interaction XML>
	       V
	[Interaction-XML with parses, named entities, triggers and edges]
	       V
	<Post-processing (trigger node duplication etc.)>
	       V
        <Conversion to BioNLP'09 Shared Task format (a2 files)>
	       V
	[Predicted events in shared task format]
	       V
	<Evaluation with BioNLP'09 Shared Task tools>

Figure 1 shows how to get classifications with the pre-trained models. If anything in the input files changes, you will need to retrain the system. There are programs for this and the basic idea is to use known training data to generate training examples and then train the SVM-multiclass on these.

You will probably want to change the input files, e.g. use your own parses. The process for making the Interaction XML from the Shared task data is like this:

Fig 2: Preparing the data

	[Shared Task Data]
	       V
	<Charniak-McClosky Parser>
	       V
	<Johnson Reranker>
	       V
	<Stanford Conversion>
	       V
	<Interaction XML generation (including head token detection)>
	       V
	[Parsed Shared task data in interaction XML format]

This is quite an involved process, so to make things easier we have provided the Shared Task data already in the interaction XML format. It should be quite simple to insert e.g. your own parses into this format. The original data preparation tools will be released in the official software release.

# 4. How to Use It ############################################################

4.1 Required Software

The main requirement of the software is Python, at least versions 2.4 and 2.5 are known to work. Additionally, if you want to use the BioNLP'09 official evaluation tools, you will need to have perl installed, and have it in the PATH and callable with the command "perl".

For additional settings, there is a settings file located in src/Settings.py. You probably only need to modify it if you want to retrain the system, in which case you need Joachims SVM-multiclass. Download it from, compile with C. You will now have two binaries, "svm_multiclass_learn" and "svm_multiclass_classify". In src/Settings.py set the variable SVMMultiClassDir to point to this directory.

All the included xml-files contain information for all three subtasks of the BioNLP'09 Shared Task. All the model files are trained for joint prediction of tasks 1 & 2. Results for the primary task 1 can be obtained by giving the correct task parameter for the relevant pipeline.

4.2 Running the System

The system is controlled by writing "pipeline files", which are simply Python scripts that call functions defined in the public interface of the event detection system. These functions usually pass the same data forward, each performing some step in the experiment. There are multiple pre-made pipelines in the package, and these should cover the most common use cases of the software. These are located in src/Classifiers/. To run a pipeline, simply call it with python "python name.py". For some pipelines, you can also pass command line parameters.

4.3 Classifying with Pre-trained Models

4.4 Writing Your Own Pipelines

# 5. Interaction XML ##########################################################
