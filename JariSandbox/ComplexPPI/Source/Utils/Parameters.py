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