import sys,os
from sklearn.datasets import load_svmlight_file
from sklearn.externals import joblib

def getClassifier(id):
    #id = id.rstrip("scikit.")
    if id == "svc":
        from sklearn import svm
        return svm.SVC
    elif id == "randomforest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier

def train():
    params, files = getParameters(["examples", "model"])
    print params, files
    clfClass = getClassifier(params["scikit"])
    clf = clfClass(probability=True, **params)
    X_train, y_train = load_svmlight_file(files["examples"])
    #print X_train.shape[1]
    print >> sys.stderr, "Training", params["scikit"], "with", params, files
    print >> sys.stderr, clf.fit(X_train, y_train)
    print >> sys.stderr, params["scikit"], "model saved to", joblib.dump(clf, files["model"], True)

def classify():
    params, files = getParameters(["examples", "model", "predictions"])
    clf = joblib.load(files["model"])
    #print dir(clf)
    #print clf.shape_fit_
    X_train, y_train = load_svmlight_file(files["examples"])#, clf.shape_fit_[1])
    out = open(files["predictions"], "wt")
    for prediction in clf.predict_proba(X_train): #clf.predict(X_train):
        classMax = prediction.argmax() + 1
        out.write(str(classMax) + " " + str(" ".join([str(x) for x in prediction])) + "\n")
    out.close()

def getParameters(unnamedNames=None):
    params = {}
    unnamed = {}
    if unnamedNames != None:
        unnamed = dict.fromkeys(unnamedNames)
    unnamedIndex = 0
    for arg in sys.argv[2:]:
        # get argument name
        if arg.find("--") == 0:
            continue
        elif arg[0] == "-":
            argName = arg
        else:
            argName = None
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
                    try:
                        params[argName] = bool(arg)
                    except ValueError:
                        params[argName] = arg
        else:
            if unnamedNames == None or unnamedIndex >= len(unnamedNames):
                raise Exception("Unknown argument", arg)
            unnamed[unnamedNames[unnamedIndex]] = arg
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