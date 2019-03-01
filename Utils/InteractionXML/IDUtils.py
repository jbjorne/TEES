import sys

def getNextFreeId(elements):
    highest = -1
    for element in elements:
        id = element.get("id")
        assert id.find(".") != -1, id
        lastPart = id.rsplit(".",1)[-1]
        assert len(lastPart) > 1, id
        number = int(lastPart[1:])
        if number > highest:
            highest = number
    if len(elements) - 1 > highest:
        highest = len(elements) - 1
    return highest + 1

def getIdNumberType(idNumber):
    if idNumber[0] == "d":
        return "document"
    elif idNumber[0] == "s":
        return "sentence"
    elif idNumber[0] == "i":
        return "interaction"
    elif idNumber[0] == "p":
        return "pair"
    elif idNumber[0] == "e":
        return "entity"
    elif idNumber[0] == "a":
        return "path"
    else:
        sys.exit("Unknown type")

def splitInteractionId(id):
    dict = {}
    splits = id.split(".")
    dict["corpus"] = splits[0]
    for i in splits[1:]:
        dict[getIdNumberType(i)] = int(i[1:])
    return dict

def buildInteractionId(id):
    idString = id["corpus"]
    if id.has_key("document"):
        idString += ".d" + str(id["document"])
    if id.has_key("sentence"):
        idString += ".s" + str(id["sentence"])
    
    if id.has_key("entity"):
        idString += ".e" + str(id["e"])
    if id.has_key("interaction"):
        idString += ".i" + str(id["interaction"])
    if id.has_key("pair"):
        idString += ".p" + str(id["pair"])
    if id.has_key("path"):
        idString += ".a" + str(id["path"])
    return idString
    
def sortInteractionIds(id1, id2):
    splits1 = id1.split(".")
    splits2 = id2.split(".")
    # start from split 1 since token 0 is the name of the dataset
    for i in range(1,len(splits1)):
        # each level's index starts with a letter (s for sentence etc.)
        number1 = int(splits1[i][1:]) 
        number2 = int(splits2[i][1:])
    
        if number1 > number2:
           return 1
        elif number1 < number2:
           return -1
    return 0 # last number1 == number 2

def checkUnique(element, ids):
    tag = element.tag
    id = element.get("id")
    if id == None:
        raise Exception("No identity defined for element of type " + str(tag))
    if tag not in ids:
        ids[tag] = set()
    if id in ids[tag]:
        raise Exception("Duplicate id '" + str(id) + "' for element of type " + str(tag))
    ids[tag].add(id)