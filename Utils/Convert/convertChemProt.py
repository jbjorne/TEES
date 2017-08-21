import os

def convertChemProt(inDir):
    filenames = os.listdir(inDir)
    filetypes = ["_abstracts.tsv", "_entities.tsv", "_relations.tsv"]
    for filename in filenames:
        if not filename.endswith(".tsv"):
            continue
        if not any([filename.endswith(x) for x in filetypes]):
            continue