#A simple script for getting
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import sys

class gifxmlParser(object):
    #A very simplified gifxml-parser, which simply returns document
    #elements for further processing.

    def __init__(self, source):
        """Source is an iterable object consisting of lines of
        gifxml, such as an open file-like object, a list/iterator
        of lines etc."""
        self.source = source

    def documentIterator(self):
        """Iterative parsing of gifxml one document at a time"""
        #For very large files we might want to implement a mechanism
        #that clears from memory parts of the xml tree already processed
        context = iter(ET.iterparse(self.source, events = ("start","end")))
        event, root = context.next()

        for event, elem in context:
            if event == "end" and elem.tag == "document":
                yield elem

if __name__=="__main__":
    #A simple test routine for illustrating how this works
    #Prints out all the sentences and their ids
    parser = gifxmlParser(sys.stdin)
    iterator = parser.documentIterator()
    for document in iterator:
        for child in document:
            if child.tag == "sentence":
                print child.get("id")+" "+child.get("text")
                
