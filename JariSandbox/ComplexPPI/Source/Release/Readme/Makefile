ALL: readme.pdf

readme.bbl: readme.bib readme.tex
	pdflatex readme.tex
	bibtex readme

readme.pdf: readme.tex readme.bbl
	pdflatex readme.tex && pdflatex readme.tex && pdflatex readme.tex

clean:
	rm -f readme.log readme.pdf readme.aux readme.bbl readme.blg *~
