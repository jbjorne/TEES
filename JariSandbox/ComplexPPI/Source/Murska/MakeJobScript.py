import sys, os, shutil
import subprocess
import time
from optparse import OptionParser

def makeJob(jobName, wallTime, outDir, args):
    """
    Make a Murska job submission script
    """
    s = "#!/bin/sh \n"
    s += "##execution shell environment \n\n"
    s += "##OUTDIR: " + outDir + " \n\n"
    s += "##Memory limit \n"
    s += "#BSUB -M 4200000 \n"
    s += "##Max runtime \n"
    s += "#BSUB -W " + wallTime + "\n" #48:00 \n"
    s += "#BSUB -J " + jobName + "\n"
    s += "#BSUB -o " + os.path.join(outDir, jobName + "csc.stdout") + "\n"
    s += "#BSUB -e " + os.path.join(outDir, jobName + "csc.stderr") + "\n"
    s += "#BSUB -n 1 \n\n"
    
    if os.environ.has_key("METAWRK") and not os.path.exists(outDir):
        os.makedirs(outDir)
    s += "echo $PWD \n"
    s += "mkdir -p " + outDir + "\n" # ensure output directory exists
    
    s += "module load java \n"
    s += "module load python/2.6.5-gcc \n"
    s += "export PATH=$PATH:/v/users/jakrbj/cvs_checkout \n"
    s += "export PYTHONPATH=$PYTHONPATH:/v/users/jakrbj/cvs_checkout/CommonUtils \n"
    s += "cd " + os.getcwd() + "\n\n"
    
    for i in range(len(args)):
        if " " in args[i] or ";" in args[i]:
            args[i] = "\"" + args[i] + "\""
    s += " ".join(args)
    
    return s

if __name__=="__main__":
    print makeJob(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])