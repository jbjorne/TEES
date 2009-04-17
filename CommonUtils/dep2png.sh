CU=$HOME/cvs_checkout/CommonUtils
TMP=`tempfile`
(cat | python $CU/draw_dg.py > $TMP.svg ) || exit
inkscape -b '#FFFFFF' -d 50 -e $TMP.png $TMP.svg > /dev/null
cat $TMP.png
rm -f $TMP.svg $TMP.png
