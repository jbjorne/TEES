from distutils.core import setup
setup (name='TEES',
    version='2.0',
    py_modules=['__init__', 'configure'],
    packages=['Classifiers', 'Detectors', 'Evaluators', 'ExampleBuilders', 'ExampleWriters', 'Tools', 'Utils'],
    description='Turku Event Extraction System',
    maintainer='Jari Bjorne',
    maintainer_email='jari.bjorne@utu.fi',
    url='http://temp/',
    license='GPL3',
    platforms='UNIX',
)



