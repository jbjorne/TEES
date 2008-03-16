TMP=`tempfile`
cat > $TMP.svg
inkscape -E $TMP.eps $TMP.svg
epstopdf --outfile=$TMP.pdf $TMP.eps 
cat $TMP.pdf
rm -f $TMP.svg $TMP.pdf $TMP.eps

