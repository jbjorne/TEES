if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the examples")
    optparser.add_option("-t", "--tokenization", default="split_gs", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split_gs", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="exampleBuilderParameters", help="Parameters for the example builder")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    (options, args) = optparser.parse_args()
    
    file.write("#!/bin/sh\n")
    file.write("#PBS -N test\n")
    file.write("#PBS -j oe\n")
    file.write("#PBS -l walltime=1:00:00\n")
    file.write("#PBS -l mppwidth=256\n")
    file.write("#PBS -m e\n")

    file.write("#PBS -M user1@univ2.fi\n")

 
    file.write("cd $PBS_O_WORKDIR\n")
    file.write("aprun -n 256 ./program\n")