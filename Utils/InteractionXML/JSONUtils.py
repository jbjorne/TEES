import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range
import json

TAGKEY = "@"
LISTS = {"document":"documents", "sentence":"sentences", "entity":"entities", "interaction":"interactions"}

class IJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super(IJSONEncoder, self).__init__(*args, **kwargs)
        self.current_indent = 0
        self.current_indent_str = ""

    def iterencode(self, o, _one_shot=True):
        #Special Processing for lists
        if isinstance(o, (list, tuple)):
            primitives_only = True
            for item in o:
                if isinstance(item, (list, tuple, dict)):
                    primitives_only = False
                    break
            output = []
            if primitives_only:
                for item in o:
                    output.append(json.dumps(item))
                return "[" + ", ".join(output) + "]"
            else:
                self.current_indent += self.indent
                self.current_indent_str = "".join( [ " " for x in range(self.current_indent) ])
                for item in o:
                    output.append(self.current_indent_str + self.encode(item))
                self.current_indent -= self.indent
                self.current_indent_str = "".join( [ " " for x in range(self.current_indent) ])
                return "[\n" + ",\n".join(output) + "]"
        elif isinstance(o, dict):
            simpleKeys = []
            complexKeys = []
            for key in o:
                if key == TAGKEY:
                    simpleKeys = [TAGKEY] + simpleKeys
                if key == "id":
                    if simpleKeys[0] == TAGKEY:
                        simpleKeys = [TAGKEY, "id"] + simpleKeys[1:]
                    else:
                        simpleKeys = ["id"] + simpleKeys
                elif not isinstance(o[key], (list, tuple, dict)):
                    simpleKeys.append(key)
                elif isinstance(o[key], (list, tuple)) and "Offset" in key:
                    simpleKeys.append(key)
                else:
                    complexKeys.append(key)
            output = []
            self.current_indent += self.indent
            self.current_indent_str = "".join( [ " " for x in range(self.current_indent) ])
            for key in simpleKeys:
                output.append((self.current_indent_str if False else "") + json.dumps(key) + ":" + self.encode(o[key]))
            for key in complexKeys:
                output.append("\n" + self.current_indent_str + json.dumps(key) + ":" + self.encode(o[key]))
            self.current_indent -= self.indent
            self.current_indent_str = "".join( [ " " for x in range(self.current_indent) ])
            return "{" + ", ".join(output) + "}"
        else:
            return json.dumps(o)

def getAttributes(element):
    attrib = element.attrib.copy()
    #attrib[TAGKEY] = element.tag
    for key in attrib:
        if "offset" in key.lower():
            attrib[key] = Range.charOffsetToTuples(attrib[key])
            if len(attrib[key]) == 1:
                attrib[key] = attrib[key][0]
    return attrib

def addChild(parent, element):
    attrib = getAttributes(element)
    listKey = LISTS[element.tag]
    if listKey not in parent:
        parent[listKey] = []
    parent[listKey].append([element.tag, attrib])
    return attrib

def convertXML(xml, outPath):
    xml = ETUtils.ETFromObj(xml)
    corpusObj = {"name":None, "children":[]}
    root = xml.getroot()
    for document in root.getiterator("document"):
        docObj = addChild(corpusObj, document)
        for sentence in document.getiterator("sentence"):
            sentObj = addChild(docObj, sentence)
            for elType in ("entity", "interaction"):
                for element in sentence.getiterator(elType):
                    addChild(sentObj, element)
    with open(outPath, "wt") as f:
        json.dump(corpusObj, f, indent=2, cls=IJSONEncoder)
    
if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n.")
    optparser.add_option("-i", "--input", default=None, help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, help="Corpus in interaction xml format", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    convertXML(options.input, options.output)