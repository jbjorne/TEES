import sys, os

input = "/home/jari/cvs_checkout"
ignoreStrings = ["CVS", 
"PPIDependencies", 
"BIGraph", 
"Murska", 
"EACL09", 
"networkx_v099",
"paperExtension",
".cvsignore",
"ComplexPPI/Source/Tests",
"ComplexPPI/Source/Release",
"ComplexPPI/Data",
"JariSandbox/Tokenization",
"paperBioNLP09",
".metadata",
".pyc"]

def listFiles(path, subPath):
    os.path.walk(path, printVisit, subPath)

def printVisit(subPath, dirname, names):
    global ignoreStrings
    
    for name in sorted(names):
        if name == "":
            continue
        if os.path.isdir(os.path.join(dirname, name)):
            continue
        pathName = os.path.join(dirname, name)[len(subPath):]
        
        foundIStr = False
        for iStr in ignoreStrings:
            if pathName.find(iStr) != -1:
                foundIStr = True
                break
        if foundIStr: continue
        print pathName
        

#listFiles(os.path.join(input, "cvs_checkout"))
#listFiles(os.path.join(input, "cvs_release/GeniaChallenge"))
listFiles(input + "/CommonUtils", "/home/jari/cvs_checkout/")
