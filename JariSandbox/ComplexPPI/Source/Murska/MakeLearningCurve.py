import sys, os, shutil
import subprocess
import time
from optparse import OptionParser

from MakeJobScript import *

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-t", "--task", default=None, dest="task", help="")
    optparser.add_option("-o", "--output", default="/wrk/jakrbj/BioNLP11Tests/curves", dest="output", help="output directory")
    optparser.add_option("-s", "--seed", default="1", dest="seed", help="")
    optparser.add_option("-p", "--points", default="0.02,0.04,0.08,0.16,0.32,0.64,1.00", dest="points", help="")
    optparser.add_option("-d", "--dummy", default=False, action="store_true", dest="dummy", help="")
    (options, args) = optparser.parse_args()
    
    options.points = options.points.split(",")
    for point in options.points:
        jobName = "LC-" + options.task + "-" + options.seed + "-" + point 
        outDir = options.output + "/seed" + options.seed + "/" + options.task + "-" + point
        command = ["python", "BioNLP11Full.py", 
                   "-o", outDir, 
                   "--downSampleTrain", point,
                   "--downSampleSeed", options.seed, 
                   "--noTestSet",
                   "--clearAll"]
        if options.task in ["OLD", "OLD.1", "OLD.2", "GE", "GE.1", "GE.2", "EPI", "ID", "BB", "REL", "REN", "CO"]:
            command.append("-a")
            command.append(options.task)
        command.append("-p")
        if options.task in ["OLD", "OLD.1", "OLD.2", "REL", "REN", "CO"]:
            command.append("split-McClosky")
        else:
            command.append("split-mccc-preparsed")
        if options.task in ["OLD", "OLD.1", "OLD.2", "GE", "GE.1", "GE.2", "EPI", "ID"]:
            command.append("-u")
        if options.task in ["BI", "REN"]:
            command[1] = "BIFull.py"
        if options.task == "EPI":
            command.append("--triggerStyle")
            command.append("typed,epi_merge_negated")
        sub = makeJob(jobName, "48:00", outDir, command)
        if options.dummy:
            print sub
        else:
            p = subprocess.Popen("bsub", stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
            print p.communicate(sub)[0]
            #print "BSUB stderr", p.stderr.readlines()
            #print "BSUB stdout", p.stdout.readlines()

