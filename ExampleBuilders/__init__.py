"""
Turn input data into machine learning examples.

ExampleBuilders are used to convert any input data into a format that can
be classified with a Classifier. The ExampleBuilder produces a number of 
examples, each consisting of (an optional) correct class and a feature vector,
a list of feature id / feature value pairs.
"""