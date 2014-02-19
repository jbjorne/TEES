from Utils.InteractionXML.GraphViz import toGraphViz

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input interaction XML file")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file stem")
    optparser.add_option("-d", "--id", default=None, dest="id", help="sentence id")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="parse name")
    optparser.add_option("-c", "--color", default="set27", dest="color", help="Event color scheme")
    optparser.add_option("-e", "--colorParse", default="set27", dest="colorParse", help="Parse color scheme")
    optparser.add_option("-n", "--colorNum", default=7, type="int", dest="colorNum", help="Number of colors in the event color scheme")
    optparser.add_option("-m", "--colorNumParse", default=7, type="int", dest="colorNumParse", help="Number of colors in the parse color scheme")
    (options, args) = optparser.parse_args()
    
    toGraphViz(options.input, options.id, options.output, options.parse, options.color, options.colorNum, options.colorParse, options.colorNumParse)