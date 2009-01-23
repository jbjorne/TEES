import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class Pruner:
    def __init__(self,document):
        self.document = document
        self.entities = {}
        self.events = {}

        self.entityTypes = dict( [(x.attrib['id'],x.attrib['type']) for x in
                                  self.document.getiterator('entity')] )

    def findNames(self):
        result = dict( [(x.attrib['id'],x) for x in
                        self.document.getiterator('entity')
                        if x.attrib['isName'].lower() == 'true'] )
        return(result)

    def findEntities(self,events):
        uids = [x.attrib['e1'] for x in events]
        result = dict( [(x.attrib['id'],x) for x in
                        self.document.getiterator('entity')
                        if (x.attrib['id'] in uids and
                            not self.entities.has_key(x.attrib['id']))] )
        return(result)
    
    def validEvent(self,event):
        all_entities = ['Gene_expression','Transcription',
                        'Translation','Protein_catabolism',
                        'Localization','Binding','Phosphorylation',
                        'Regulation','Positive_regulation',
                        'Negative_regulation','Protein']
        t = event.attrib['type']
        e1t = self.entityTypes[event.attrib['e1']]
        e2t = self.entityTypes[event.attrib['e2']]
        if e1t in ['Gene_expression','Transcription',
                   'Translation','Protein_catabolism']:
            return(t=='Theme' and e2t=='Protein')
        elif e1t=='Localization':
            # NOTE: check that all task 2 entities are of the type 'entity'
            return( ((t=='Theme' and e2t=='Protein') or
                     (t=='ToLoc' and e2t=='Entity')) )
        elif e1t=='Binding':
            # they say that e2t could also be DNA
            # but there was no such entities in the data
            return( ((t.startswith('Theme') and e2t in ['Protein']) or
                     (t.startswith('Site') and e2t in ['Entity'])) )
        elif e1t=='Phosphorylation':
            return( ((t=='Theme' and e2t=='Protein') or
                     (t=='Site' and e2t=='Entity')) )
        elif e1t in ['Regulation','Positive_regulation','Negative_regulation']:
            return( ((t=='Theme' and e2t in all_entities) or
                     (t=='Cause' and e2t in all_entities) or
                     (t in ['Site','Csite'] and e2t=='Entity')) )
        else:
            sys.stderr.write("Invalid event type: %s"%e1t)
        return(False)
    
    def analyse(self):
        tmp_entities = self.findNames()
        tmp_events = {}
        while tmp_entities or tmp_events:
            self.entities.update(tmp_entities)
            self.events.update(tmp_events)
            tmp_events = dict( [(x.attrib['id'],x) for x in
                                self.document.getiterator('interaction')
                                if (tmp_entities.has_key(x.attrib['e2']) and
                                    not self.events.has_key(x.attrib['id']) and
                                    self.validEvent(event))] )
            tmp_entities = self.findEntities(tmp_events)

    def prune(self):
        for sentence in self.document.findall('sentence'):
            for entity in sentence.findall('entity'):
                uid = entity.attrib['id']
                if not self.entities.has_key(uid):
                    sentence.remove(self.entities[uid])
            for event in sentence.findall('interaction'):
                uid = event.attrib['id']
                if not self.event.has_key(uid):
                    sentence.remove(self.events[uid])



def interface(optionArgs=sys.argv[1:]):
    from optparse import OptionParser

    op = OptionParser(usage="%prog [options]\nGenia shared task specific pruning of invalid nodes and edges.")
    op.add_option("-i", "--infile",
                  dest="infile",
                  help="Input file (gifxml)",
                  metavar="FILE")
    op.add_option("-o", "--outfile",
                  dest="outfile",
                  help="Output file (gifxml)",
                  metavar="FILE")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.infile:
        print "Please specify the input file."
        quit = True
    if not options.outfile:
        print "Please specify the output file."
        quit = True
    if quit:
        op.print_help()
        return(False)

    corpus = ET.parse(options.infile)
    for document in corpus.getroot().findall('document'):
        pruner = Pruner(document)
        pruner.analyse()
        pruner.prune()
    corpus.write(options.outfile)

if __name__=="__main__":
    interface()
