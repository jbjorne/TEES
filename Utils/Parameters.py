import sys, os
import types
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Libraries.combine as combine

def split(string, delimiter=":"):
    s = ""
    ignore = False
    for c in string:
        if c in "([{":
            ignore = True
        elif c in ")]}":
            ignore = False
        if c == delimiter and not ignore:
            yield s
            s = ""
        else:
            s += c
    if s != "":
        yield s

def toDict(parameters, valueListKey=None):
    if parameters == None:
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
                assert name.count("=") == 1, name
                name, values = name.split("=")
                values = values.strip().split(",")
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
            s += key + "=" + ",".join([str(x) for x in parameters[key]])
        else:
            if skipKeysWithValues == None or parameters[key] not in skipKeysWithValues: # skip defaults
                if len(s) > 0: s += ":"
                if skipValues != None and parameters[key] in skipValues:
                    s += key
                else:
                    s += key + "=" + str(parameters[key])
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
            print >> sys.stderr, "Using new parameters (" + verboseMessage + "): " + new.strip(":")
        return new.strip(":")
    else:
        if verboseMessage != None and "default" in verboseFor:
            print >> sys.stderr, "Using default parameters (" + verboseMessage + "): " + str(default)
        return default