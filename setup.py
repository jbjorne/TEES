from distutils.core import setup
setup (name='TEES',
    version='2.1.1',
    py_modules=['__init__', 'configure', 'train', 'classify', 'batch'],
    packages=['Core', 'Classifiers', 'Detectors', 'Evaluators', 'ExampleBuilders', 'ExampleBuilders.FeatureBuilders',
              'ExampleWriters', 'Tools', 'Utils', 'Utils.Connection', 'Utils.Convert', 'Utils.InteractionXML', 
              'Utils.InteractionXML.Tools', 'Utils.Libraries', 'Utils.STFormat'],
    description='Turku Event Extraction System',
    maintainer='Jari Bjorne',
    maintainer_email='jari.bjorne@utu.fi',
    url='http://jbjorne.github.com/TEES/',
    license='GPL3',
    platforms='UNIX',
)



