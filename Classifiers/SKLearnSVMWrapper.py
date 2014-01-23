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
    if useProbability and clfName.find("svm.") != 0:
        del params["probability"]
    #print params, files
    clfClass = getClassifier(clfName, params)
    clf = clfClass(**params)
    X_train, y_train = load_svmlight_file(files["examples"])
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
    out = open(files["predictions"], "wt")
    if clf.teesProba:
        X_train, y_train = load_svmlight_file(files["examples"])
        for prediction in clf.predict_proba(X_train): #clf.predict(X_train):
            classMax = prediction.argmax() + 1
            out.write(str(classMax) + " " + str(" ".join([str(x) for x in prediction])) + "\n")
    else:
        X_train, y_train = load_svmlight_file(files["examples"], clf.teesFeatureCount)
        for prediction in clf.predict(X_train): #clf.predict(X_train):
            out.write(str(int(prediction)) + "\n")        
    out.close()

def getParameters(unnamedNames=None):
    params = {}
    unnamed = {}
    if unnamedNames != None:
        unnamed = dict.fromkeys(unnamedNames)
    unnamedIndex = 0
    argName = None
    for arg in sys.argv[2:]:
        # get argument name
        if arg.find("--") == 0:
            continue
        elif arg[0] == "-":
            argName = arg[1:]
        else:
            # get argument value
            if argName != None:
                params[argName] = arg
                # process argument
                try:
                    params[argName] = float(arg)
                except ValueError:
                    try:
                        params[argName] = float(arg)
                    except ValueError:
                        if arg in ["True", "False"]:
                            params[argName] = bool(arg) 
                        else:
                            params[argName] = arg
                argName = None
            else:
                if unnamedNames == None or unnamedIndex >= len(unnamedNames):
                    raise Exception("Unknown argument", arg)
                unnamed[unnamedNames[unnamedIndex]] = arg
                unnamedIndex += 1
    return params, unnamed

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    #from optparse import OptionParser
    #optparser = OptionParser(description="Interface to scikit-learn SVM")
    #optparser.add_option("--train", default=False, action="store_true", dest="train")
    #optparser.add_option("--classify", default=False, action="store_true", dest="classify")
    #(options, args) = optparser.parse_args()
    
    action = sys.argv[1]
    
    assert action in ["train", "classify"]
    if action == "train":
        train()
    else:
        classify()