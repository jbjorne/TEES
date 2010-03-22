TMP=`tempfile`
CU=$HOME/cvs_checkout/CommonUtils

cat $1 | python $CU/draw_dg.py > $TMP.svg
inkscape -A $2 $TMP.svg
rm -f $TMP.svg

