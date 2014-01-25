import sys,os
from sklearn.datasets import load_svmlight_file
from sklearn.externals import joblib
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")

def getClassifier(id, params):
    package, cls = id.rsplit('.', 1)
    prefix = "sklearn."
    if package == "elm":
        prefix = "Utils.Libraries.PythonELM."
    #print "from " + prefix + package + " import " + cls + " as " + cls
    exec "from " + prefix + package + " import " + cls + " as " + cls
    return eval(cls)

def train():
    params, files = getParameters(["examples", "model"])
    clfName = params["scikit"]
    del params["scikit"]
    useProbability = "probability" in params and params["probability"]
    useTransform = "transform" in params
    if useTransform:
        del params["transform"]
    if useProbability and clfName not in ["svm.SVC", "svm.NuSVC"]:
        del params["probability"]
    #print params, files
    clfClass = getClassifier(clfName, params)
    clf = clfClass(**params)
    X_train, y_train = load_svmlight_file(files["examples"])
    if (useTransform):
        clf = clfClass(compute_importances = useTransform, **params)
        X_train = clf.transform(X_train)
        clf.teesTransform = True
    else:
        clf.teesTransform = False
    #print X_train.shape[1]
    clf.teesFeatureCount = X_train.shape[1] # store the size with a unique name
    if useProbability:
        clf.teesProba = True
    else:
        clf.teesProba = False
    print >> sys.stderr, "Training", clfName, "with arguments", params, "and files", files
    print >> sys.stderr, clf.fit(X_train, y_train)
    print >> sys.stderr, clfName, "model saved to", joblib.dump(clf, files["model"], True)

def classify():
    params, files = getParameters(["examples", "model", "predictions"])
    clf = joblib.load(files["model"])
    #print dir(clf)
    #print clf.shape_fit_
    print >> sys.stderr, "Classifying files", files
    X_train, y_train = load_svmlight_file(files["examples"], clf.teesFeatureCount)
    if (clf.teesTransform):
        X_train = clf.transform(X_train)
    out = open(files["predictions"], "wt")
    if clf.teesProba:
        for prediction in clf.predict_proba(X_train):
            classMax = prediction.argmax() + 1
            out.write(str(classMax) + " " + str(" ".join([str(x) for x in prediction])) + "\n")
    else:
        for prediction in clf.predict(X_train):
            out.write(str(int(prediction)) + "\n")        
    out.close()

def getParameters(requireWrapperParams=None):
    params = {}
    wrapperParams = {}
    argName = None
    for arg in sys.argv[2:]:
        if arg[0] == "-": # get argument name
            argName = arg
        else: # get argument value
            if argName == None:
                raise Exception("Unnamed argument '" + arg + "'")
            # determine where to put the argument
            if argName.find("--") == 0:
                targetDict = wrapperParams
            else:
                targetDict = params
            # process argument
            try:
                targetDict[argName.lstrip("-")] = eval(arg)
            except:
                targetDict[argName.lstrip("-")] = arg
            argName = None
    for required in requireWrapperParams:
        if required not in wrapperParams:
            raise Exception("Missing scikit-learn wrapper parameter '" + required + "'")
    return params, wrapperParams

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    if ("--classify" in sys.argv and "--train" in sys.argv):
        raise Exception("Only one of --train and --classify must be defined")

    if "--classify" in sys.argv:
        classify()
    elif "--train" in sys.argv:
        train()
    else:
        raise Exception("Either --train or --classify must be defined")