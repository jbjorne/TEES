import sys, os
sys.path.append(os.path.dirname(__file__)+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Utils.ProgressCounter import ProgressCounter

def readARFF(filename):
    featureSet = IdSet(1)
    classSet = IdSet(0)
    f = open(filename,"rt")
    inData = False
    lines = f.readlines()
    counter = ProgressCounter(len(lines),"ARFFLine")
    examples = []
    for line in lines:
        counter.update(string="Processing line " + str(counter.current + 1) + ": ")
        line = line.strip()
        if len(line) == 0 or line[0] == "%":
            continue
        elif line[0] == "@":
            #print line
            category = line.split()[0].lower()
            if category == "@attribute":
                category, name, type = line.split()
                assert(not inData)
                if name.lower() == "class":
                    name = name.lower()
                    classNames = type[1:-1].split(",")
                    assert(len(classNames)==2)
                    classSet.defineId(classNames[0].strip(),1)
                    classSet.defineId(classNames[1].strip(),-1)
                featureSet.getId(name)
            elif category.lower() == "@relation":
                assert(not inData)
            elif category == "@data":
                inData = True
        else:
            assert(inData)
            count = 1
            features = {}
            for column in line.split(","):
                if featureSet.getName(count) != "class":
                    features[count] = float(column)
                else:
                    classId = classSet.getId(column, False)
                    assert(classId != None)
                count += 1
            exampleCount = str(len(examples))
            exampleId = "BreastCancer.d" + exampleCount + ".s0.x0"
            examples.append([exampleId,classId,features,{}])
                    
    return examples

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    import os
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory, useful for debugging")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Reading input from " + options.input
    examples = readARFF(options.input)
    if options.output == None:
        if options.input.rsplit(".",1)[-1] == "arff":
            options.output = options.input.rsplit(".",1)[0] + ".examples"
        else:
            options.output = options.input + ".examples"
    print >> sys.stderr, "Writing output to " + options.output
    ExampleUtils.writeExamples(examples, options.output)
    
    
