#Generates most probable candidates for sentences
import parseGifxml
import sys
import nbest
from optparse import OptionParser

#TODO: sentence level f-score
#Corpus level f-score
#Iterator for generating candidates
#oracle

def instantiateOptionParser():
    optparser = OptionParser(usage="python %prog [options] PREDICTION_FILE GSTANDARD_FILE")
    optparser.add_option("-n", "--nbest", default = 50, dest = "nbest", help = "the maximum number of candidates to be generated per sentence", type = "int")
    (options, args) = optparser.parse_args()
    return optparser
    

def compare(x,y):
    if x[0] > y[0]:
        return 1
    elif x[0] == y[0]:
        return 0
    else:
        return -1

def score(tp, fp, fn):
    s = tp-fp-fn
    return s

def getSimplePredictions(entities, pairs):
    """Returns the prediction lists with no normalizations,
    preprocessing etc."""
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

def getGSEdges(pairs, entities):
    gsedges = set([])
    outside_count = 0
    entity_info = {}
    for entity in entities:
        head, typ_e = entity.attrib["headOffset"], entity.attrib["type"]
        entity_info[entity.attrib["id"]] = (head, typ_e)
    for pair in pairs:
        if pair.attrib["e1"] in entity_info and pair.attrib["e2"] in entity_info:
            head1, type1 = entity_info[pair.attrib["e1"]]
            head2, type2 = entity_info[pair.attrib["e2"]]
            etype = pair.attrib["type"]
            gsedges.add(etype+head1+type1+head2+type2)
        else:
            outside_count += 1
    return gsedges, outside_count

def getPredictedEdges(predictions, keys, entities, choices):
    choices = choices[1]
    assert len(predictions) == len(choices)
    entity_info = {}
    p_edges = set([])
    for entity in entities:
        head, typ_e = entity.attrib["headOffset"], entity.attrib["type"]
        entity_info[entity.attrib["id"]] = (head, typ_e)
    for key, index in zip(keys, choices):
        values = predictions[key]
        etype = values[index][1]
        if not etype == "neg":
            e1, e2 = key.split("_")
            head1, type1 = entity_info[e1]
            head2, type2 = entity_info[e2]
            p_edges.add(etype+head1+type1+head2+type2)
    return p_edges
        

def getEntitiesAndPairs(sentence):
    entities = []
    pairs = []
    for child in sentence:
        if child.tag == "entity":
            entities.append(child)
        elif child.tag == "pair" or child.tag == "interaction":
            pairs.append(child)
    return entities, pairs

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

def oracleStatistics(p_iterator, g_iterator, n):
    TP = 0
    FP = 0
    FN = 0
    TP_oracle = 0
    FP_oracle = 0
    FN_oracle = 0
    counter = 0
    for p_document, g_document in zip(p_iterator, g_iterator):
        #counter3 += 1
        #counter += 1
        #if counter > 30:
        #    print FN
        #    sys.exit(0)
        for p_child, g_child in zip(p_document, g_document):
            if g_child.tag == "sentence":
                assert p_child.attrib["origId"]==g_child.attrib["origId"]
                p_entities, p_pairs = getEntitiesAndPairs(p_child)
                g_entities, g_pairs = getEntitiesAndPairs(g_child)
                if len(p_pairs) == 0:
                    FN += len(g_pairs)
                    FN_oracle += len(g_pairs)
                else:
                    g_edges, outside_count = getGSEdges(g_pairs, g_entities)
                    predictions = getSimplePredictions(p_entities, p_pairs)
                    table, table_transpose, keys = toTable(predictions)
                    best = nbest.decode(table_transpose, n)
                    p_edges = getPredictedEdges(predictions, keys, p_entities, best[0])
                    tp, fp, fn = getTP_FP_FN(g_edges, p_edges)
                    TP += tp
                    FP += fp
                    FN += fn
                    tp_best = tp
                    fp_best = fp
                    fn_best = fn
                    best_s = score(tp, fp, fn)
                    for i in range(1,len(best)):
                        p_edges = getPredictedEdges(predictions, keys, p_entities, best[i])
                        tp_c, fp_c, fn_c = getTP_FP_FN(g_edges, p_edges)
                        assert tp_c+fn_c == tp+fn
                        s = score(tp_c, fp_c, fn_c)
                        if s > best_s:
                            tp_best = tp_c
                            fp_best = fp_c
                            fn_best = fn_c
                            best_s = s
                    TP_oracle += tp_best
                    FP_oracle += fp_best
                    FN_oracle += fn_best
    PR = float(TP)/float(TP+FP)
    R = float(TP)/float(TP+FN)
    PR_oracle = float(TP_oracle)/float(TP_oracle+FP_oracle)
    R_oracle = float(TP_oracle)/float(TP_oracle+FN_oracle)
    assert TP_oracle+FN_oracle == TP+FN
    print "TP", TP
    print "FP", FP
    print "FN", FN
    print "F-score", (2*PR*R)/(PR+R)
    print "TP (oracle)", TP_oracle
    print "FP (oracle)", FP_oracle
    print "FN (oracle)", FN_oracle
    print "F-score (oracle)", (2*PR_oracle*R_oracle)/(PR_oracle+R_oracle)
    
    
def getTP_FP_FN(g_edges, p_edges):
    TP = len(g_edges.intersection(p_edges))
    FP = len(p_edges)-TP
    FN = len(g_edges)-TP
    return TP, FP, FN

if __name__=="__main__":
    optparser = instantiateOptionParser()
    (options, args) = optparser.parse_args()
    if len(args) != 2:
        sys.stdout.write(optparser.get_usage())
        print "python CandidateGenerator.py -h for options\n"
        sys.exit(0)
    p_file = open(args[0])
    g_file = open(args[1])
    p_parser = parseGifxml.gifxmlParser(p_file)
    p_iterator = p_parser.documentIterator()
    g_parser = parseGifxml.gifxmlParser(g_file)
    g_iterator = g_parser.documentIterator()
    counter = 1
    oracleStatistics(p_iterator, g_iterator, options.nbest)
    sys.exit(0)
    for p_document, g_document in zip(p_iterator, g_iterator):
        for p_child, g_child in zip(p_document, g_document):
            if p_child.tag == "sentence":
                assert p_child.attrib["id"]==g_child.attrib["id"]
                p_entities, p_pairs = getEntitiesAndPairs(p_child)
                g_entities, g_pairs = getEntitiesAndPairs(g_child)
                predictions = getSimplePredictions(p_entities, p_pairs)
                table, table_transpose, keys = toTable(predictions)
                best = nbest.decode(table_transpose,options.nbest)
                getTP_FP_FN(g_entities, g_pairs, p_entities, predictions, best)
                if counter > 30:
                    sys.exit(0)
                #if predictions:
                #    sys.exit(0)
                #if len(predictions) > 0:
                #    table, table_transpose, keys = toTable(predictions)
                #    five = nbest.decode(table_transpose, 100)
                #    print table
                #    print five
                #    counter += 1
                #    if counter > 100:
                #        assert False
