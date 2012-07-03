import sys, os
from Unix import getConnection

if __name__=="__main__":
    import sys
    
    from optparse import OptionParser, OptionGroup
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-p", "--program", default=None, dest="program", help="")
    optparser.add_option("-j", "--jobFile", default=None, dest="jobFile", help="")
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
    (options, args) = optparser.parse_args()
    
    connection = getConnection(options.connection)
    connection.debug = options.debug
    connection.submit(options.program, os.path.dirname(options.jobFile), os.path.basename(options.jobFile))
        