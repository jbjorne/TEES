if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    print "Hello world, option:", options.input