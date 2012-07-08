import sys, os
import types
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Libraries.combine as combine

def toDict(parameters, valueListKey=None):
    if parameters == None:
        return {}
    if type(parameters) not in types.StringTypes:
        return parameters
    paramDict = {}
    if valueListKey != None and ":" not in parameters and "=" not in parameters:
        names = [valueListKey + "=" + parameters]
    else:
        names = parameters.split(":")
    for name in names:
        if name.strip() != "":
            values = True
            if "=" in name:
                name, values = name.split("=")
                values = values.split(",")
                if len(values) == 1:
                    values = values[0]
            paramDict[name] = values
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

def get(parameters, defaults=None, allowNew=False, valueListKey=None, valueLimits=None):
    parameters = toDict(parameters, valueListKey) # get parameter dictionary
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
            if valueLimits != None and key in valueLimits:
                values = newDict[key]
                if type(values) not in [types.ListType, types.TupleType]:
                    values = [values]
                for value in values:
                    if value not in valueLimits[key]:
                        raise Exception("Illegal value " + str(value) + " for parameter " + key + " (allowed values: " + str(valueLimits[key]) + ")")
        parameters = newDict
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