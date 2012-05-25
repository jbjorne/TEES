import sys, os
import shutil
import urllib
import tarfile
import tempfile
import zipfile
from Libraries.progressbar import *

pbar = None

def checkReturnCode(code):
    if code != 0:
        print >> sys.stderr, "Non-zero return code", str(code) + ", program may not be working."
        return False
    else:
        print >> sys.stderr, "Return code", str(code) + ", program appears to be working."
        return True

# Modified from http://code.activestate.com/recipes/576714-extract-a-compressed-file/
def extractPackage(path, destPath, subPath=None):
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
    
    file = opener(path, mode)
    names = namelister(file)
    if subPath == None:
        file.extractall(destPath)
    else:
        tempdir = tempfile.mkdtemp()
        file.extractall(tempdir)
        if os.path.exists(destPath):
            shutil.rmtree(destPath)
        shutil.move(os.path.join(tempdir, subPath), destPath)
        shutil.rmtree(tempdir)
    file.close()
    return names

def downloadAndExtract(url, extractPath=None, downloadPath=None, packagePath=None, addName=True, redownload=False):
    # Download
    downloadFile = download(url, downloadPath, addName=addName, clear=redownload)
    # Unpack
    print >> sys.stderr, "Extracting", downloadFile, "to", extractPath
    return extractPackage(downloadFile, extractPath, packagePath)

def downloadProgress(count, blockSize, totalSize):
    percent = int(count*blockSize*100/totalSize)
    percent = min(0, max(percent, 100)) # clamp
    pbar.update(percent)

def download(url, destPath, addName=True, clear=False):
    global pbar
    
    redirectedUrl = urllib.urlopen(url).geturl()
    if redirectedUrl != url:
        print >> sys.stderr, "Redirected to", redirectedUrl
    destFileName = destPath
    if addName:
        destFileName = os.path.join(destPath, os.path.basename(redirectedUrl))
    if not os.path.exists(os.path.dirname(destFileName)):
        os.makedirs(os.path.dirname(destFileName))
    if clear or not os.path.exists(destFileName):
        if os.path.exists(destFileName): # clear existing file
            os.remove(destFileName)
        print >> sys.stderr, "Downloading file", redirectedUrl, "to", destFileName
        widgets = [FileTransferSpeed(),' <<<', Bar(), '>>> ', Percentage(),' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=100)
        pbar.start()
        urllib.urlretrieve(redirectedUrl, destFileName, reporthook=downloadProgress)
        pbar.finish()
        pbar = None
    else:
        print >> sys.stderr, "Skipping already downloaded file", url
    return destFileName
