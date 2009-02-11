#Generates most probable candidates for sentences
import parseGifxml
import sys
import nbest

def compare(x,y):
    if x[0] > y[0]:
        return 1
    elif x[0] == y[0]:
        return 0
    else:
        return -1


def getSimplePredictions(sentence):
    """Returns the prediction lists with no normalizations,
    preprocessing etc."""
    entities = []
    pairs = []
    for child in sentence:
        if child.tag == "entity":
            entities.append(child)
        elif child.tag == "pair":
            pairs.append(child)
    predictions = {}
    for pair in pairs:
        e1 = pair.attrib["e1"]
        e2 = pair.attrib["e2"]
        key = e1+"_"+e2
        values = pair.attrib["predictions"].split(",")
        values = [(float((x.split(":")[1])),x.split(":")[0]) for x in values]
        values.sort(compare)
        predictions[key] =values
    return predictions

def toTable(predictions):
    rows = []
    keys = []
    for key in predictions.keys():
        keys.append(key)
        column = []
        for pair in predictions[key]:
            column.append(pair[0])
        rows.append(column)
    normalizeTable(rows)
    rows_transpose = [[] for i in range(len(rows[0]))]
    #Transpose
    for i in range(len(rows)):
        for j in range(len(rows[0])):
            rows_transpose[j].append(rows[i][j])
    return rows, rows_transpose, keys

def normalizeTable(table):
    minimum = None
    #No need for maximum actually, but maybe I'll change this later
    #to normalize to probabilities or something...
    maximum = None
    for i in range(len(table)):
        for j in range(len(table[i])):
            value = table[i][j]
            if not minimum:
                minimum = value
            if not maximum:
                maximum = value
            if value > maximum:
                maximum = value
            elif value < minimum:
                minimum = value
    if minimum <=0:
        for i in range(len(table)):
            for j in range(len(table[i])):
                table[i][j]+= abs(minimum)+1

if __name__=="__main__":
    parser = parseGifxml.gifxmlParser(sys.stdin)
    iterator = parser.documentIterator()
    counter = 0
    for document in iterator:
        for child in document:
            if child.tag == "sentence":
                predictions = getSimplePredictions(child)
                if len(predictions) > 0:
                    table, table_transpose, keys = toTable(predictions)
                    five = nbest.decode(table_transpose, 100)
                    print table
                    print five
                    counter += 1
                    if counter > 100:
                        assert False
