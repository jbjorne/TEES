import sys, os
import shutil

TEAM_NAME = "TEES"
MODEL_DIR = "/home/jari/Dropbox/data/BioNLP16/models"
OUTPUT_DIR = "/home/jari/Dropbox/data/BioNLP16/submission"

results = {
"BB_EVENT_16-160331":"BB3-event",
"BB_EVENT_NER_16-160406":"BB3-event+ner"
}

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
assert not os.path.exists(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)

SOURCE_FILES = {"DEVEL":"classification-empty/devel-empty-events.zip", "TEST":"classification-test/test-events.zip"}
SUBMIT_FILES = {"DEVEL":"develset", "TEST":"testset"}

for model in sorted(results.keys()):
    for dataSet in ("DEVEL", "TEST"):
        src = os.path.join(MODEL_DIR, model, SOURCE_FILES[dataSet])
        dst = os.path.join(OUTPUT_DIR, TEAM_NAME + "_" + results[model] + "_" + SUBMIT_FILES[dataSet] + ".zip")
        print "Copying", (src, dst)
        shutil.copy2(src, dst)

