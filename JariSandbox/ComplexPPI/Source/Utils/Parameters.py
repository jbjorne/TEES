import types

def getArgs(func, args):
    '''Return dictionary without invalid function arguments.'''
    if type(args) == types.DictType:
        argsDict = args
    else:
        argsDict = splitParameters(args)
    validArgs = func.func_code.co_varnames[:func.func_code.co_argcount]
    return dict((key, value) for key, value in argsDict.iteritems() 
                if key in validArgs)

def splitParameters(string):
    if string == None:
        return {}
    paramDict = {}
    paramSets = string.split(";")
    for paramSet in paramSets:
        paramName, paramValueString = paramSet.split(":")
        paramValues = paramValueString.split(",")
        paramDict[paramName] = []
        count = 0
        for value in paramValues:
            try:
               floatValue = float(value)
               intValue = int(value)
               if floatValue != float(intValue):
                   paramDict[paramName].append(floatValue)
               else:
                   paramDict[paramName].append(intValue)
            except:
               paramDict[paramName].append(value) 
    return paramDict