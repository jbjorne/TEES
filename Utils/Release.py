import sys,os
print __file__
mainTEESDir = os.path.abspath(os.path.join(__file__, "../.."))
print mainTEESDir

def listExecutables(filter=["Core", "FeatureBuilders", "InteractionXML"]):
    print "| Program | Location | Description |"
    print "|:-----------|:-----------|:-----------|"
    for triple in os.walk(mainTEESDir):
        for filename in sorted(triple[2]):
            skip = False
            for filterRule in filter:
                if filterRule in os.path.join(triple[0], filename):
                    skip = True
                    break
            if skip:
                continue
            if filename.endswith(".py"):
                f = open(os.path.join(triple[0], filename), "rt")
                lines = f.readlines()
                f.close()
                isExecutable = False
                description = ""
                for line in lines:
                    if "optparser = OptionParser(" in line:
                        assert line.count("\"") in [0, 2], line
                        if line.count("\"") == 2:
                            description = line.split("\"")[1]
                            description = description.split("\\n", 1)[-1]
                            description = description.split(".")[0]
                            description = description.strip()
                        isExecutable = True
                if isExecutable:
                    subDir = triple[0][len(mainTEESDir)+1:]
                    print "|", subDir, "|", filename, "|", description, "|"

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(description="Make TEES release files.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("-a", "--action", default=None, dest="action", help="")
    (options, args) = optparser.parse_args()
    assert options.action in ["CONVERT_CORPORA", "BUILD_MODELS", "PACKAGE_MODELS", "BUILD_APIDOC", "LIST_EXECUTABLES"]
    
    if options.action == "LIST_EXECUTABLES":
        listExecutables()