import sys
import re

def process(infile):
    log = re.compile(r'^(.*?) (.*)')
    node = re.compile(r'^(.*?) \(.*\)$')
    edge = re.compile(r'^(.*?) \(.*\) from .*? \(.*\) to .*? \(.*\)$')
    docs = 0
    preserved = []
    removed = []
    broken = 0
    for line in infile.readlines():
        m = log.match(line.strip())
        if not m:
            sys.stderr.write("Invalid log line - %s\n"%line.strip())
            continue
        if m.group(1) == 'Pruning':
            docs += 1
        elif m.group(1) == 'Breaking':
            broken += 1
        elif m.group(1) == 'Removed':
            if edge.match(m.group(2)):
                removed.append(('e',edge.match(m.group(2)).group(1)))
            elif node.match(m.group(2)):
                removed.append(('n',node.match(m.group(2)).group(1)))
            else:
                sys.stderr.write("Invalid 'Removed' line - %s\n"%line.strip())
        elif m.group(1) == 'Preserved':
            if edge.match(m.group(2)):
                preserved.append(('e',edge.match(m.group(2)).group(1)))
            elif node.match(m.group(2)):
                preserved.append(('n',node.match(m.group(2)).group(1)))
            else:
                sys.stderr.write("Invalid 'Preserved' line - %s\n"%line.strip())
    if docs==0:
        sys.stderr.write("No documents\n")
    else:
        d = float(docs)
        np = [x[1] for x in preserved if x[0]=='n']
        ep = [x[1] for x in preserved if x[0]=='e']
        nr = [x[1] for x in removed if x[0]=='n']
        er = [x[1] for x in removed if x[0]=='e']
        sys.stderr.write("Number of documents: %d\n"%(docs))
        sys.stderr.write("Cycles broken per document: %.3f\n"%(broken/d))
        sys.stderr.write("Nodes preserved per document: %.3f\n"%(len(np)/d))
        sys.stderr.write("Edges preserved per document: %.3f\n"%(len(ep)/d))
        sys.stderr.write("Nodes removed per document: %.3f\n"%(len(nr)/d))
        sys.stderr.write("Edges removed per document: %.3f\n"%(len(er)/d))
        sys.stderr.write("Node preserve:remove ratio: %.3f\n"%(len(np)/float(len(nr))))
        sys.stderr.write("Edge preserve:remove ratio: %.3f\n"%(len(ep)/float(len(er))))
        

if __name__=="__main__":
    process(sys.stdin)
