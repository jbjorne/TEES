import sys, os
import types
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Libraries.combine as combine

def split(string, delimiter=":", ignoreOpen = "([{'\"", ignoreClose = ")]}'\""):
    s = ""
    ignore = ""
    for i in range(len(string)):
        c = string[i]
        if ignore != "" and c in ignoreClose:
            if c in "'\"":
                if ignore[-1] == c:
                    ignore = ignore[:-1]
                elif ignore[-1] not in "'\"":
                    ignore += c
            elif ignoreClose[ ignoreOpen.index(ignore[-1]) ] == c:
                ignore = ignore[:-1]
            else:
                raise Exception("Mismatched opening '" + ignore[-1] + "' for closing character '" + c + "' in '" + string + "' at position " + str(i) + " " + str(ignore))
        elif c in ignoreOpen:
            ignore += c

        if c == delimiter and ignore == "":
            if string[i-1:i] == "\\": # protected delimiter
                s += c
            else:
                yield s
                s = ""
        elif c == "\\" and string[i+1:i+2] == delimiter and ignore == "": # remove delimiter protector
            pass
        else: 
            s += c
    if s != "":
        yield s

def toId(parameters, valueListKey=None):
    parameters = toDict(parameters, valueListKey)
    paramKeys = sorted(parameters.keys())
    idStr = ""
    for key in paramKeys:
        if key.startswith("TEES."):
            continue
        if parameters[key] != None:
            idStr += "-" + str(key) + "_" + str(parameters[key])
        else:
            idStr += "-" + str(key)
    # sanitize id
    idStr = idStr.replace(":", ".")
    idStr = idStr.replace(" ", "_")
    idStr = "".join([c for c in idStr if c.isalnum() or c in ('.','_',"-")]).rstrip()
    return idStr


def toDict(parameters, valueListKey=None):
    if parameters == None or parameters == "":
        return {}
    if type(parameters) not in types.StringTypes:
        return parameters
    paramDict = {}
    # Check if the parameter string is a list of values without a defined parameter name
    if valueListKey != None and ":" not in parameters and "=" not in parameters:
        if parameters.strip() == "": # no values defined
            names = [] # dummy list
            paramDict = {valueListKey:None}
        else: # values are defined for the default parameter (value list key)
            names = [valueListKey + "=" + parameters]
    else:
        names = split(parameters, ":")
    # Process parameter=value1,value2,value3,... strings
    for name in names:
        if name.strip() != "":
            values = True
            if "=" in name:
                #assert name.count("=") == 1, name
                splits = [x for x in split(name, "=")]
                assert len(splits) == 2, splits
                name, values = [x for x in split(name, "=")]
                values = [x for x in split(values.strip(), ",")]
                if len(values) == 1:
                    values = values[0]
            paramDict[name.strip()] = values
    return paramDict

def toString(parameters, skipKeysWithValues=[None], skipValues=[True], skipDefaults={}):
    if parameters == None:
        return ""
    if type(parameters) in types.StringTypes:
        return parameters
    s = ""
    for key in sorted(parameters.keys()):
        if key in skipDefaults and parameters[key] == skipDefaults[key]:
            continue
        elif type(parameters[key]) in [types.ListType, types.TupleType]:
            if len(s) > 0: s += ":"
            s += key + "=" + ",".join([str(x).replace(":", "\\:") for x in parameters[key]])
        else:
            if skipKeysWithValues == None or parameters[key] not in skipKeysWithValues: # skip defaults
                if len(s) > 0: s += ":"
                if skipValues != None and parameters[key] in skipValues:
                    s += key
                else:
                    s += key + "=" + str(parameters[key]).replace(":", "\\:")
    return s

def get(parameters, defaults=None, allowNew=False, valueListKey=None, valueLimits=None, valueTypes=None):
    parameters = toDict(parameters, valueListKey) # get parameter dictionary
    # Get default values
    if defaults != None:
        if type(defaults) in [types.ListType, types.TupleType]: # convert list to dictionary
            defaults = dict( zip(defaults, len(defaults) * [None]) )
        newDict = {} # combine parameters and defaults
        for key in sorted(list(set(parameters.keys() + defaults.keys()))):
            if key not in defaults and not allowNew:
                raise Exception("Undefined parameter: " + key + " (parameters: " + str(parameters) + ", defaults: " + str(defaults) + ")")
            if key in parameters:
                newDict[key] = parameters[key]
            elif key in defaults:
                newDict[key] = defaults[key]
        parameters = newDict
    # Validate parameters
    for key in sorted(list(parameters.keys())):
        values = parameters[key]
        if type(values) not in [types.ListType, types.TupleType]:
            values = [values]
        # Check that the value is one of a defined set
        if valueLimits != None and key in valueLimits:
            for value in values:
                if value not in valueLimits[key]:
                    raise Exception("Illegal value '" + str(value) + "' for parameter " + key + " (allowed values: " + str(valueLimits[key]) + ")")
        # Check that the value has the correct type
        if valueTypes != None and key in valueTypes:
            for value in values:
                for valueType in valueTypes[key]: # a list of cast-functions
                    passed = True # value could be cast to at least one of the given types
                    try:
                        valueType(value) # will throw an exception if value is incompatible with the cast
                    except:
                        passed = False
                    if passed:
                        break
                if not passed:
                    raise Exception("Value '" + str(value) + "' for parameter " + key + " cannot be cast to an allowed type (allowed types: " + str(valueTypes[key]) + ")")

    return parameters

def getCombinations(parameters, order=None):
    parameters = get(parameters)
    parameterNames = sorted(parameters.keys())
    if order != None:
        assert sorted(order) == parameterNames
        parameterNames = order
    #parameterNames.sort()
    #parameterNames.reverse() # to put trigger parameter first (allows optimized 3-parameter grid)
    parameterValues = []
    for parameterName in parameterNames:
        parameterValues.append([])
        values = parameters[parameterName] 
        if isinstance(values, (list, tuple)):
            for value in values:
                parameterValues[-1].append( (parameterName,value) )
        else:
            parameterValues[-1].append( (parameterName,values) )
    combinationLists = combine.combine(*parameterValues)
    combinations = []
    for combinationList in combinationLists:
        combinations.append({})
        for value in combinationList:
            combinations[-1][value[0]] = value[1]
    return combinations

def cat(default, new, verboseMessage=None, verboseFor=["cat", "new", "default"]):
    if new != None and new.startswith(":") and default != None:
        if verboseMessage != None and "cat" in verboseFor:
            print >> sys.stderr, "Extended default parameters (" + verboseMessage + "): " + default + new
        return default + new
    elif new != None:
        if verboseMessage != None and "new" in verboseFor:
            print >> sys.stderr, "Using new parameters (" + verboseMessage + "): " + new
        return new
    else:
        if verboseMessage != None and "default" in verboseFor:
            print >> sys.stderr, "Using default parameters (" + verboseMessage + "): " + str(default)
        return default

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    from optparse import OptionParser
    optparser = OptionParser(description="Predict events/relations")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input")
    optparser.add_option("-n", "--name", default=None, dest="name", help="input is a python file, name is the setting variable in the file")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file stem")
    (options, args) = optparser.parse_args()
    
    if options.name != None:
        import imp
        module = imp.load_source("ParametersInput", options.input)
        exec "options.input = module." + options.name
    
    print >> sys.stderr, "input:", options.input
    params = get(options.input)
    print >> sys.stderr, "params:", params