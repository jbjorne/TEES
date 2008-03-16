TMP=`tempfile`
cat > $TMP.svg
inkscape -A $TMP.pdf $TMP.svg
pdf2ps $TMP.pdf $TMP.ps
ps2epsi $TMP.ps $TMP.eps
epstopdf --outfile=$TMP.pdf $TMP.eps 
cat $TMP.pdf
rm -f $TMP.svg $TMP.pdf $TMP.ps $TMP.eps

