#!/bin/sh
#PBS -N test
#PBS -j oe
#PBS -l walltime=1:00:00
#PBS -l mppwidth=256
#PBS -m e

#PBS -M jakrbj@utu.fi

aprun -n 256 $HOME/python hello.py