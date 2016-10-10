import os
import codecs

def openFile(path, tarFile=None):
    if tarFile != None:
        try:
            return tarFile.extractfile(tarFile.getmember(path))
        except KeyError:
            pass
    else:
        if os.path.exists(path):
            return codecs.open(path, "rt", "utf-8") #open(path, "rt")
    return None

def openWithExt(path, extensions, tarFile=None):
    f = None
    for ext in extensions:
        f = openFile(path + "." + ext, tarFile)
        if f != None:
            break
    return f

def getTarFilePath(path):
    if path.find(".tar.gz") != -1:
        tarFilePath, filePath = path.split(".tar.gz")
        tarFilePath += ".tar.gz"
        filePath.rstrip("/")
        return tarFilePath, filePath
    else:
        return None, path