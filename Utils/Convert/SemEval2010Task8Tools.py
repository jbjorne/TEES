import sys, os
import shutil
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../../")))
import Utils.Settings as Settings
import Utils.Download
import tempfile
import zipfile

def install(destPath=None, redownload=False, updateLocalSettings=True):
    if hasattr(Settings, "SE10T8_CORPUS"): # Already installed
        return
    print >> sys.stderr, "---------------", "Downloading the SemEval 2010 Task 8 corpus", "---------------"
    if destPath == None:
        destPath = os.path.join(Settings.DATAPATH, "resources/SemEval2010_task8_all_data.zip")
    Utils.Download.download(Settings.URL["SE10T8_CORPUS"], destPath, addName=False, clear=redownload)
    Settings.setLocal("SE10T8_CORPUS", destPath, updateLocalSettings)

def evaluate(inputXML, goldXML):
    install()
    tempDir = os.path.join(tempfile.gettempdir(), "SE10T8_evaluator")
    archive = zipfile.ZipFile(Settings.SE10T8_CORPUS, 'r')
    basePath = "SemEval2010_task8_all_data/SemEval2010_task8_scorer-v1.2/semeval2010_task8_"
    for filename in ("format_checker.pl", "scorer-v1.2.pl"):
        archive.extract(basePath + filename, tempDir)
        source = archive.open(basePath + filename)
        target = file(os.path.join(tempDir, filename), "wb")
        with source, target:
            shutil.copyfileobj(source, target)

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None)
    optparser.add_option("-o", "--output", default=None)
    optparser.add_option("-a", "--action", default=None)
    (options, args) = optparser.parse_args()
    
    if options.action == "install":
        install()
    elif options.action == "evaluate":
        evaluate(None, None)
    else:
        print "Unknown action", options.action