import sys, os
import shutil
import urllib
import tarfile
import tempfile
import zipfile
import codecs
from Libraries.progressbar import *

pbar = None

def checkReturnCode(code):
    if code != 0:
        print >> sys.stderr, "Non-zero return code", str(code) + ", program may not be working."
        return False
    else:
        print >> sys.stderr, "Return code", str(code) + ", program appears to be working."
        return True

def getTopDir(path, names, include=None):
    topDirs = [] 
    for item in names:
        if "/" not in item or (item.endswith("/") and item.count("/") == 1):
            potential = os.path.join(path, item)
            if os.path.exists(potential) and os.path.isdir(potential):
                if include == None or item.strip("/") in include:                  
                    topDirs.append(item)
    if len(topDirs) == 0:
        topDirs = [os.path.join(path, x) for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
    assert len(topDirs) == 1, (path, topDirs, names)
    return os.path.join(path, topDirs[0])

class SizeReportingFile(file):
    def __init__(self, filename):
        self.totalSize = os.path.getsize(filename)
        #self.readSize = 0
        super(SizeReportingFile, self).__init__(filename)
    
    def read(self, size):
        global pbar
        #self.readSize += size
        if pbar != None:
            percent = int(self.tell() * 100 / self.totalSize)
            percent = max(0, min(percent, 100)) # clamp
            pbar.update(percent)
        return file.read(self, size)

def extractWithProgress(package, names, destPath):
    global pbar
    
    count = 0
    for name in names:
        package.extract(name, destPath)
        count += 1
        if pbar != None:
            percent = int(count * 100 / len(names))
            percent = max(0, min(percent, 100)) # clamp
            pbar.update(percent)

# Modified from http://code.activestate.com/recipes/576714-extract-a-compressed-file/
def extractPackage(path, destPath, subPath=None):
    global pbar
    
    if path.endswith('.zip'):
        opener, mode = zipfile.ZipFile, 'r'
        namelister = zipfile.ZipFile.namelist
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        opener, mode = tarfile.open, 'r:gz'
        namelister = tarfile.TarFile.getnames
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        opener, mode = tarfile.open, 'r:bz2'
        namelister = tarfile.TarFile.getnames
    else: 
        raise ValueError, "Could not extract `%s` as no appropriate extractor is found" % path
    
    widgets = [' [', Bar(), '] ', Percentage(), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=100)
    pbar.start()
    
    #package = opener(fileobj=SizeReportingFile(path), mode=mode)
    package = opener(path, mode)
    names = namelister(package)
    if subPath == None:
        extractWithProgress(package, names, destPath)
    else:
        tempdir = tempfile.mkdtemp()
        extractWithProgress(package, names, tempdir)
        if os.path.exists(destPath):
            shutil.rmtree(destPath)
        shutil.move(os.path.join(tempdir, subPath), destPath)
        shutil.rmtree(tempdir)
    package.close()
    
    pbar.finish()
    pbar = None
    
    return names

def downloadAndExtract(url, extractPath=None, downloadPath=None, packagePath=None, addName=True, redownload=False):
    # Download
    downloadFile = download(url, downloadPath, addName=addName, clear=redownload)
    if downloadFile == None:
        return None
    # Unpack
    print >> sys.stderr, "Extracting", downloadFile, "to", extractPath
    return extractPackage(downloadFile, extractPath, packagePath)

def downloadProgress(count, blockSize, totalSize):
    percent = int(count*blockSize*100/totalSize)
    percent = max(0, min(percent, 100)) # clamp
    pbar.update(percent)
    
def downloadWget(url, filename):
    import subprocess
    subprocess.call(["wget", "--output-document=" + filename, url])

def download(url, destPath=None, addName=True, clear=False):
    global pbar
    
    origUrl = url
    redirectedUrl = urllib.urlopen(url).geturl()
    if redirectedUrl != url:
        print >> sys.stderr, "Redirected to", redirectedUrl
    if destPath == None:
        destPath = "/tmp"
    destFileName = destPath
    if addName:
        destFileName = destPath + "/" + os.path.basename(origUrl)
    if not os.path.exists(os.path.dirname(destFileName)):
        os.makedirs(os.path.dirname(destFileName))
    if clear or not os.path.exists(destFileName):
        if os.path.exists(destFileName): # clear existing file
            os.remove(destFileName)
        print >> sys.stderr, "Downloading file", redirectedUrl, "to", destFileName
        widgets = [FileTransferSpeed(),' <<<', Bar(), '>>> ', Percentage(),' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=100)
        pbar.start()
        try:
            urllib.FancyURLopener().retrieve(redirectedUrl, destFileName, reporthook=downloadProgress)
        except IOError, e:
            print >> sys.stderr, e.errno
            print >> sys.stderr, "Error downloading file", redirectedUrl
            pbar.finish()
            pbar = None
            print >> sys.stderr, "Attempting download with wget"
            downloadWget(origUrl, destFileName)
            if os.path.exists(destFileName):
                return destFileName
            else:
                print >> sys.stderr, "Error downloading file", origUrl, "with wget"
                return None
        pbar.finish()
        pbar = None
    else:
        print >> sys.stderr, "Skipping already downloaded file", url
    return destFileName

def getPubMed(pmid):
    print >> sys.stderr, "*************************** NOTE ***************************"
    print >> sys.stderr, "Do not attempt to do large-scale classification of PubMed"
    print >> sys.stderr, "abstracts with this feature. For that, use the downloadable"
    print >> sys.stderr, "PubMed release. This is a demonstration feature only, and"
    print >> sys.stderr, "abusing it will cause you to be banned from PubMed!"
    print >> sys.stderr, "************************************************************"
    print >> sys.stderr, "Downloading PubMed abstract", pmid
    tempDir = tempfile.gettempdir()
    url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=" + str(pmid) + "&retmode=xml"
    downloaded = os.path.join(tempDir, "pmid-" + str(pmid))
    download(url, downloaded + ".xml", False)
    # Read the text from the XML
    f = codecs.open(downloaded + ".xml", "rt", "utf-8")
    textElements = []
    for line in f:
        line = line.strip()
        for tag in ["<ArticleTitle>", "<AbstractText>"]:
            if line.startswith(tag):
                textElements.append(line.split(">", 1)[1].split("<")[0])
    f.close()
    # Save the text file
    f = codecs.open(downloaded + ".txt", "wt", "utf-8")
    f.write("\n".join(textElements))
    f.close()
    # Return text file name
    return downloaded + ".txt"