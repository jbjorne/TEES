# Parameters
# 1) Input file in interaction xml format
# 2) Gold file, i.e. an interaction xml file that will be used as a gold standard 
#    (devel.xml default)
# 3) Output directory. Will be deleted if exists! (default "visualization")

GOLD_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
if [ -n "$2" ]; then
	GOLD_FILE="$2"
fi

OUTDIR="visualization"
if [ -n "$3" ]; then
	OUTDIR="$3"
fi

python ~/cvs_checkout/JariSandbox/ComplexPPI/Source/VisualizeCorpus.py -i $1 -g $GOLD_FILE -o $OUTDIR
