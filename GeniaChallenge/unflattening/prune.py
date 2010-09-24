import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import time

class Pruner:
    """
    Class for removing invalid nodes and edges.
    """
    def __init__(self,document):
        self.document = document
        self.entities = set()
        self.events = set()

        self.origEntities = dict( [(x.attrib['id'],x) for x in
                                   self.document.getiterator('entity')] )
        self.origEvents = dict( [(x.attrib['id'],x) for x in
                                 self.document.getiterator('interaction')] )
        
        self.maxCycles = 10

    def validEvent(self,event):
        """
        Tests for the validity of the given event.

        @type event: cElementTree.Element
        @param event: event node
        @rtype: boolean
        @return: is valid?
        """
        all_entities = ['Gene_expression','Transcription',
                        'Translation','Protein_catabolism',
                        'Localization','Binding','Phosphorylation',
                        'Regulation','Positive_regulation',
                        'Negative_regulation','Protein']
        t = event.attrib['type']
        e1t = self.origEntities[event.attrib['e1']].attrib['type']
        e2t = self.origEntities[event.attrib['e2']].attrib['type']
        if e1t in ['Gene_expression','Transcription',
                   'Translation','Protein_catabolism']:
            return(t=='Theme' and e2t=='Protein')
        elif e1t=='Localization':
            # NOTE: check that all task 2 entities are of the type 'entity'
            return( ((t=='Theme' and e2t=='Protein') or
                     (t=='AtLoc' and e2t=='Entity') or
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
        elif e1t=='Protein':
            pass # these are valid leaves
        elif e1t=='Entity':
            # Sites (etc.) are successors for proteins at this point of processing
            return(t in ['ToLoc','AtLoc','Site','Csite'] and e2t=='Protein')
        else:
            sys.stderr.write("Invalid event type: %s (%s)\n"%(e1t,event.attrib['id']))
        return(False)
    
    def analyse(self):
        """
        Prepares the Pruner object for pruning by refreshing
        the cache of valid entities and events.
        """
        # from leaves to root
        tmp_entities = set( [x.attrib['id'] for x in
                             self.document.getiterator('entity')
                             if x.attrib['isName'].lower() == 'true'] )
        tmp_events = set()
        while tmp_entities or tmp_events:
            self.entities.update(tmp_entities)
            self.events.update(tmp_events)
            # pick valid events
            tmp_events = set( [x.attrib['id'] for x in
                               self.document.getiterator('interaction')
                               if (x.attrib['e2'] in tmp_entities and
                                   not x.attrib['id'] in self.events and
                                   self.validEvent(x))] )
            # pick valid entities
            tmp_entities = set( [self.origEvents[x].attrib['e1']
                                 for x in tmp_events
                                 if not self.origEvents[x].attrib['e1']
                                 in self.entities] )
        self.entities.update(tmp_entities)
        self.events.update(tmp_events)

    def analyseCycles(self):
        """
        Breaks cycles in the graph. This method requires the presence of
        prediction strengths for each edge. The weakest edge is always
        removed.

        Detection algorithm adapted from
        http://neopythonic.blogspot.com/2009/01/detecting-cycles-in-directed-graph.html

        @rtype: integer
        @return: number of cycles broken
        """
        def findCycle():
            # cycles can form between regulation events
            regs = [x.attrib['id'] for x in self.document.getiterator('entity')
                    if (x.attrib['id'] in self.entities and
                        x.attrib['type'] in ['Regulation',
                                             'Positive_regulation',
                                             'Negative_regulation'])]
            outs = dict( [(x,[y.attrib['e2']
                              for y in self.document.getiterator('interaction')
                              if (y.attrib['id'] in self.events and
                                  y.attrib['e1']==x)]) for x in regs] )
            todo = set(regs)
            while todo:
                node = todo.pop()
                stack = [node]
                while stack:
                    top = stack[-1]
                    for node in outs[top]:
                        if node in stack:
                            return stack[stack.index(node):]
                        if node in todo:
                            stack.append(node)
                            todo.remove(node)
                            break
                    else:
                        node = stack.pop()
            return None

        def pickWeakest(cycle):
            edges = [(x.attrib['id'],
                      [float(y[1]) for y in [z.split(':') for z in
                                             x.attrib['predictions'].split(',')]
                       if y[0]==x.attrib['type']][0])
                     for x in self.document.getiterator('interaction')
                     if (x.attrib['id'] in self.events and
                         x.attrib['e1'] in cycle and
                         x.attrib['e2'] in cycle)]
            weakest = edges[0]
            for x in edges:
                if x[1]<weakest[1]:
                    weakest = x
            #sys.stderr.write("Breaking cycle by removing %s\n"%weakest[0])
            self.events.remove(weakest[0])
            return(1)
        
        cycle = findCycle()
        count = 0
        self.brokenCycles = 0
        #self.sentenceIds = set()
        while cycle:
            #for id in cycle:
            #    sId = id.rsplit(".", 1)
            #    self.sentenceIds.add(sId)
            count += pickWeakest(cycle)
            self.brokenCycles = count
            cycle = findCycle()
            if count > self.maxCycles:
                break
        #sys.stderr.write("Broke %s cycle(s)\n"%count)
        return count

    def prune(self):
        """
        Prunes the graph. More specifically, removes all events and entities
        that are not present in the cache. See analyse().
        """
        self.nestingRemoveCount = 0
        if self.brokenCycles > self.maxCycles:
            # Potential error, remove all nesting events that can cause cycles
            sentence = self.document
            for event in sentence.findall('interaction'):
                toId = event.attrib['e2']
                # Remove all nesting events
                if self.origEntities[toId].attrib['isName'] == "False":
                    sentence.remove(event)
                    self.nestingRemoveCount += 1
            print >> sys.stderr, "Too many cycles error in sentence", sentence.get("id")
            print >> sys.stderr, "Removed", self.nestingRemoveCount, "nesting events"
            return  
            
        for sentence in [self.document]: #self.document.findall('sentence'):
            for entity in sentence.findall('entity'):
                uid = entity.attrib['id']
                if not uid in self.entities:
                    sentence.remove(entity)
                    #sys.stderr.write("Removed %s (%s)\n"%(entity.attrib['type'],uid))
                else:
                    pass
                    #sys.stderr.write("Preserved %s (%s)\n"%(entity.attrib['type'],uid))
            for event in sentence.findall('interaction'):
                uid = event.attrib['id']
                fromId = event.attrib['e1']
                if not self.origEntities.has_key(fromId): # intersentence interactions
                    continue
                fromType = self.origEntities[fromId].attrib['type']
                toId = event.attrib['e2']
                if not self.origEntities.has_key(toId): # intersentence interactions
                    continue
                toType = self.origEntities[toId].attrib['type']
                if not uid in self.events:
                    sentence.remove(event)
                    #sys.stderr.write("Removed %s (%s) from %s (%s) to %s (%s)\n"%(event.attrib['type'],uid,fromType,fromId,toType,toId))
                else:
                    pass
                    #sys.stderr.write("Preserved %s (%s) from %s (%s) to %s (%s)\n"%(event.attrib['type'],uid,fromType,fromId,toType,toId))



def prune(input, cycles=True, output=None):
    """
    Convenience wrapper for interface.

    @type input: string
    @param input: input file
    @type cycles: boolean
    @param cycles: break cycles?
    @type output: string
    @param output: output file
    @rtype: cElementTree.Element
    @return: corpus node
    """
    print >> sys.stderr, "Pruning"
    options = ["-i",input,"-o",output]
    if cycles:
        options.append("-c")
    return interface(options)

def interface(optionArgs=sys.argv[1:]):
    """
    The function to handle the command-line interface.
    """
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
    op.add_option("-c", "--cycles",
                  dest="cycles",
                  help="Remove cycles (requires the presence of 'predictions' attribute in 'interaction' elements)",
                  default=False,
                  action="store_true")
    (options, args) = op.parse_args(optionArgs)

    quit = False
    if not options.infile:
        print "Please specify the input file."
        quit = True
#    if not options.outfile:
#        print "Please specify the output file."
#        quit = True
    if quit:
        op.print_help()
        return(False)

    corpus = ETUtils.ETFromObj(options.infile)
    cycleBrokenCount = 0
    skipCount = 0
    for document in corpus.getroot().findall('document'):
        for sentence in document.findall("sentence"):
            #sys.stderr.write("Pruning document %s\n"%document.attrib['id'])
            pruner = Pruner(sentence)
            pruner.analyse()
            if options.cycles:
                cycleBrokenCount += pruner.analyseCycles()
            pruner.prune()
    sys.stderr.write("File pruned, broke " + str(cycleBrokenCount) + " cycles\n" )
    if skipCount > 0:
        sys.stderr.write("Pruning skipped " + str(skipCount) + " sentences\n" )
    if options.outfile:
        ETUtils.write(corpus, options.outfile)
    return corpus

if __name__=="__main__":
    interface()
