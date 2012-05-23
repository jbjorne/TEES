import sys, os
import shutil
import urllib
import tarfile
import tempfile
import zipfile

# Modified from http://code.activestate.com/recipes/576714-extract-a-compressed-file/
def extractPackage(path, destPath, subPath=None):
    if path.endswith('.zip'):
        opener, mode = zipfile.ZipFile, 'r'
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        opener, mode = tarfile.open, 'r:gz'
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        opener, mode = tarfile.open, 'r:bz2'
    else: 
        raise ValueError, "Could not extract `%s` as no appropriate extractor is found" % path
    
    file = opener(path, mode)
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

def downloadAndExtract(url, extractPath=None, downloadPath=None, packagePath=None, addName=True, redownload=False):
    # Download
    downloadFile = download(url, downloadPath, addName=addName, clear=redownload)
    # Unpack
    print >> sys.stderr, "Extracting", downloadFile, "to", extractPath
    extractPackage(downloadFile, extractPath, packagePath)

def download(url, destPath, addName=True, clear=False):
    redirectedUrl = urllib.urlopen(url).geturl()
    if redirectedUrl != url:
        print >> sys.stderr, "Redirected to", redirectedUrl
    if not os.path.exists(os.path.dirname(destPath)):
        os.makedirs(os.path.dirname(destPath))
    destFileName = destPath
    if addName:
        destFileName = os.path.join(destPath, os.path.basename(redirectedUrl))
    if clear or not os.path.exists(destFileName):
        if os.path.exists(destFileName): # clear existing file
            os.remove(destFileName)
        print >> sys.stderr, "Downloading file", redirectedUrl
        urllib.urlretrieve(redirectedUrl, destFileName)
    else:
        print >> sys.stderr, "Skipping already downloaded file", url
    return destFileName
