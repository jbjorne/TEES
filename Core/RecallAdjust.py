"""
Trade precision for recall
"""

try:
    import xml.etree.cElementTree as ET
except:
    import cElementTree as ET
import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Utils.ElementTreeUtils as ETUtils
import math
from optparse import OptionParser
import sys

#Scales the value; works correctly for both positive and negative values
def scaleVal(val,boost=1.0):
    if val>=0: #non-negative case
        val*=boost
    else: #negative case (pretend as if it were positive, and translate back)
        diff=abs(val)*boost-abs(val)
        val+=diff
    return val

def scaleRange(val, boost, classRange):
    if boost < 1.0 and val > 0:
        if val < (1.0-boost) * classRange[1]:
            return -val - 1
    #elif boost > 1.0 and val > 0:
    #    if val < (boost-1) * classRange[1]:
    #        return -val - 1
    return val

def adjustEntity(entityNode,targetLabel,multiplier,classRange=None):
    """Adjust the confidence of targetLabel in entityNode by multiplier"""
    predictions=entityNode.get("predictions")
    if not predictions: #nothing to do
        return
    maxConfidence=None
    maxLabel=None
    labMod=[] #list with modified "label:confidence"
    for labelConfidence in predictions.split(","):
        label,confidence=labelConfidence.split(":")
        confidence=float(confidence)
        if label!=targetLabel: #nothing to do
            labMod.append(labelConfidence)
        else:
            if classRange == None: #multiclass
                confidence=scaleVal(float(confidence),multiplier) #modify...
            else: #binary
                confidence=scaleRange(float(confidence),multiplier, classRange[label]) #modify...
            labMod.append(label+":"+str(confidence))
        if maxConfidence==None or maxConfidence<confidence:
            maxConfidence=confidence
            maxLabel=label

    #Done
    entityNode.set("predictions",",".join(labMod))
    entityNode.set("type",maxLabel)
    
def getClassRanges(entities):
    classRanges = {}
    for entity in entities:
        if entity.get("given") == "True":
            continue
        predictions=entity.get("predictions")
        if predictions:
            for labelConfidence in predictions.split(","):
                label,confidence=labelConfidence.split(":")
                confidence=float(confidence)
                if not classRanges.has_key(label):
                    classRanges[label] = [sys.maxint,-sys.maxint]
                classRanges[label] = [min(classRanges[label][0], confidence), max(classRanges[label][1], confidence)]
    return classRanges

def getClassRangesFromPredictions(predictions):
    classRanges = {1:[sys.maxint,-sys.maxint], 2:[sys.maxint,-sys.maxint]}
    for prediction in predictions:
        for cls in [1, 2]:
            classRanges[cls][0] = min(float(prediction[cls]), classRanges[cls][0])
            classRanges[cls][1] = max(float(prediction[cls]), classRanges[cls][1])
    return classRanges       

class RecallAdjust:    

    @classmethod
    def run(cls,inFile,multiplier=1.0,outFile=None,targetLabel="neg", binary=False):
        """inFile can be a string with file name (.xml or .xml.gz) or an ElementTree or an Element or an open input stream
        multiplier adjusts the level of boosting the non-negative predictions, it is a real number (0,inf)
        multiplier 1.0 does nothing, <1.0 decreases negative class confidence, >1.0 increases negative class confidence
        the root of the modified tree is returned and, if outFile is a string, written out to outFile as well"""
        print >> sys.stderr, "##### Recall adjust with multiplier " + str(multiplier)[:5] + " #####"
        tree=ETUtils.ETFromObj(inFile)
        if not ET.iselement(tree):
            assert isinstance(tree,ET.ElementTree)
            root=tree.getroot()
        else:
            root = tree
        
        if multiplier != -1:
            if binary:
                print >> sys.stderr, "Recall binary mode"
                classRanges = getClassRanges(root.getiterator("entity"))
                assert len(classRanges.keys()) in [0,2]
                if len(classRanges.keys()) == 0:
                    print >> sys.stderr, "Warning, recall adjustment skipped because no prediction weights found"
            else:
                print >> sys.stderr, "Recall multiclass mode"
                classRanges = None
            for entityNode in root.getiterator("entity"):
                adjustEntity(entityNode,targetLabel,multiplier,classRanges)
        if outFile:
            ETUtils.write(root,outFile)
        return tree

if __name__=="__main__":
    desc="Negative class adjustment in entity predictions. Reads from stdin, writes to stdout."
    parser = OptionParser(description=desc)
    parser.add_option("-i", "--input", default=None, dest="input", help="Predictions in interaction XML", metavar="FILE")
    parser.add_option("-o", "--output", default=None, dest="output", help="Predictions in interaction XML", metavar="FILE")
    parser.add_option("-l","--lambda",dest="l",action="store",default=None,type="float",help="The adjustment weight for the negative class. 1.0 does nothing, <1.0 decreases the predictions, >1.0 increases the predictions. No default.")
    parser.add_option("-t","--targetLabel",dest="targetLabel",action="store",default="neg",help="The label of the class to be adjusted. Defaults to 'neg'.")

    (options, args) = parser.parse_args()

    if options.l==None:
        print >> sys.stderr, "You need to give a lambda"
        sys.exit(1)

    #RecallAdjust.run(sys.stdin,options.l,sys.stdout,options.targetLabel)
    RecallAdjust.run(options.input,options.l,options.output,options.targetLabel)
