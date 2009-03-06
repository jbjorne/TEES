import sys
import re

def process(infile):
    log = re.compile(r'^(.*?) (.*)')
    spl = re.compile(r'^.*? \((.*?)\) into ([0-9]+) - .*$')
    gen = re.compile(r'^Cause-Theme combinations for .*? \((.*?)\).*$')
    gen2 = re.compile(r'^inter-group pairs for .*? \((.*?)\).*$')
    docs = 0
    skips = 0
    split = []
    causetheme = []
    intergroup = []
    for line in infile.readlines():
        m = log.match(line.strip())
        if not m:
            sys.stderr.write("Invalid log line - %s\n"%line.strip())
            continue
        if m.group(1) == 'Unflattening':
            docs += 1
        elif m.group(1) == 'Skipping':
            skips += 1
        elif m.group(1) == 'Splitting':
            if spl.match(m.group(2)):
                if int(spl.match(m.group(2)).group(2))>1:
                    split.append(spl.match(m.group(2)).group(1))
            else:
                sys.stderr.write("Invalid 'Splitting' line\n")
        elif m.group(1) == 'Generating':
            if gen.match(m.group(2)):
                causetheme.append(gen.match(m.group(2)).group(1))
            elif gen2.match(m.group(2)):
                intergroup.append(gen2.match(m.group(2)).group(1))
            else:
                sys.stderr.write("Invalid 'Generating' line\n")
    if docs==0:
        sys.stderr.write("No documents\n")
    else:
        d = float(docs)
        sys.stderr.write("Number of documents: %d\n"%(docs))
        sys.stderr.write("Number of skips per document: %d\n"%(skips/d))
        sys.stderr.write("(all events) Splitting-to-1 per document: %.3f\n"%(len(split)/d))
        sys.stderr.write("(regulations) Cause-Theme splitting per document: %.3f\n"%(len(causetheme)/d))
        sys.stderr.write("(binding) Inter-group splitting per document: %.3f\n"%(len(intergroup)/d))
        sys.stderr.write("(binding) Splitting-to-1:inter-group-pairs ratio: %.3f\n"%(len([x for x in split if x=='Binding'])/float(len(intergroup))))
        sys.stderr.write("(regulations) Splitting-to-1:cause-theme ratio: %.3f\n"%(len([x for x in split if x.endswith('egulation')])/float(len(causetheme))))

if __name__=="__main__":
    process(sys.stdin)
