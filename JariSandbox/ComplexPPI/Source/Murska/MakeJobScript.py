import sys, os, shutil
import subprocess
import time
from optparse import OptionParser

def isVuori():
    return "HOSTNAME" in os.environ and "vuori" in os.environ["HOSTNAME"]

def makeJob(jobName, wallTime, outDir, args):
    if isVuori():
        return makeVuoriJob(jobName, wallTime, outDir, args)
    else:
        return makeMurskaJob(jobName, wallTime, outDir, args)

def makeMurskaJob(jobName, wallTime, outDir, args):
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
    s += "#BSUB -o " + os.path.join(outDir, jobName + ".csc-stdout") + "\n"
    s += "#BSUB -e " + os.path.join(outDir, jobName + ".csc-stderr") + "\n"
    s += "#BSUB -n 1 \n\n"
    
    if outDir != None and os.environ.has_key("METAWRK") and not os.path.exists(outDir):
        os.makedirs(outDir)
    s += "echo $PWD \n"
    if outDir != None:
        s += "mkdir -p " + outDir + "\n" # ensure output directory exists
    
    s += "module load java \n"
    s += "module load python \n" #/2.6.5-gcc \n"
    s += "export TEES_SETTINGS=/v/users/jakrbj/TEESLocalSettings.py \n"
    #s += "export PATH=$PATH:/v/users/jakrbj/cvs_checkout \n"
    #s += "export PYTHONPATH=$PYTHONPATH:/v/users/jakrbj/cvs_checkout/CommonUtils \n"
    s += "cd " + os.getcwd() + "\n\n"
    
    for i in range(len(args)):
        if " " in args[i] or ";" in args[i] or ":" in args[i]:
            args[i] = "\"" + args[i] + "\""
    s += " ".join(args)
    
    return s

def makeVuoriJob(jobName, wallTime, outDir, args):
    """
    Make a Vuori job submission script
    """
    s = "#!/bin/bash -l \n"
    s += "##execution shell environment \n\n"
    
    s += "## name of your job" + "\n"
    s += "#SBATCH -J " + jobName + "\n"
    s += "## system error message output file" + "\n"
    s += "#SBATCH -e " + os.path.join(outDir, jobName + "-" + args[1].split("/")[-1] + ".csc-stderr") + "\n"
    s += "## system message output file" + "\n"
    s += "#SBATCH -o " + os.path.join(outDir, jobName + "-" + args[1].split("/")[-1] + ".csc-stdout") + "\n"
    s += "## a per-process (soft) memory limit" + "\n"
    s += "## limit is specified in MB" + "\n"
    s += "## example: 1 GB is 1000" + "\n"
    #s += "#SBATCH --mem-per-cpu=16000" + "\n"
    s += "#SBATCH --mem-per-cpu=4000" + "\n"
    s += "## how long a job takes, wallclock time hh:mm:ss" + "\n"
    s += "#SBATCH -t 48:00:00" + "\n"
    s += "## number of processes" + "\n"
    s += "#SBATCH -n 1" + "\n"
    
    if outDir != None and os.environ.has_key("METAWRK") and not os.path.exists(outDir):
        os.makedirs(outDir)
    s += "echo $PWD \n"
    if outDir != None:
        s += "mkdir -p " + outDir + "\n" # ensure output directory exists
    
    #s += "module load java \n"
    s += "module load python \n" #/2.6.5-gcc \n"
    s += "export TEES_SETTINGS=/v/users/jakrbj/TEESLocalSettings.py \n"
    s += "cd " + os.getcwd() + "\n\n"
    
    for i in range(len(args)):
        if " " in args[i] or ";" in args[i] or ":" in args[i]:
            args[i] = "\"" + args[i] + "\""
    s += " ".join(args)
    
    return s

def getOutdir(args):
    for i in range(len(args)):
        if args[i] in ["-o", "--output"]:
            return args[i+1]
    for i in range(len(args)):
        if args[i] in ["-i", "--input"]:
            if os.path.exists(args[i+1]):
                if os.path.isfile(args[i+1]):
                    return os.path.split(args[i+1])[0]
                else:
                    return os.path.normpath(args[i+1]).rsplit("/", 1)[0]
            else:
                return args[i+1]
    assert False

if __name__=="__main__":
    #print makeJob(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
    
    print makeJob(sys.argv[1], "48:00", getOutdir(sys.argv[2:]), sys.argv[2:])