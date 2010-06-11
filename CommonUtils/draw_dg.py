# (c) Filip Ginter
#
# Copyleft: Do whatever you want with this code. :)
#

#Python 2.4 vs 2.5+
try:
    import cElementTree as ET
except ImportError:
    import xml.etree.cElementTree as ET
    
import sys
import re
import codecs

class SVGOptions:

    fontSize=24
    labelFontSize=20
    tokenSpace=10 #horizontal space between tokens
    depVertSpace=20
    minDepPadding=10 #How many points, at least, should be reserved horizontally for the dependency rounded corner
    lineSep=5 #How many points, vertically, should go between lines?
    
    whAttributes=True #Insert width&height attributes of the SVG element

def strint(i):
    return str(int(i))

def textWidth(txt,fontSize):
    return len(txt)*fontSize*0.65

tokenSpec=re.compile(r"^(.*)_([0-9]+)$")
def tokSpec(tokTxt):
    match=tokenSpec.match(tokTxt)
    if match:
        return match.group(1),match.group(2)
    else:
        return tokTxt,None

class Token:

    def __init__(self,txt,pos,styleDict={}):
        
        self.txt,self.spec=tokSpec(txt)
        self.otherLines=[] #text in all other lines
        self.pos=pos #index in the sentence
        self.x=0#layout() fills this
        self.y=0#layout() fills this
        self.styleDict={"text-anchor":"middle",
                    "fill":"black","font-size":str(SVGOptions.fontSize)+"px","font-family":"Monospace"}
        #override the defaults
        for k,v in styleDict.items():
            self.styleDict[k]=v

    def matches(self,txt,spec):
        return self.txt==txt and self.spec==spec

    def width(self):
        mainW=textWidth(self.txt,SVGOptions.fontSize)
        if self.otherLines:
            lineW=max(textWidth(txt,SVGOptions.fontSize) for txt in self.otherLines)
        else:
            lineW=0
        return max(mainW,lineW)

    def toSVG(self):
        runningY=self.y
        texts=[self.txt]+self.otherLines
        texts.reverse()
        nodes=[]
        for txt in texts:
            node=ET.Element("text")
            node.set("systemLanguage","en")
            node.set("x",strint(self.x))
            node.set("y",strint(runningY))
            styleStr=";".join("%s:%s"%(var,val) for var,val in self.style().items())
            node.set("style",styleStr)
            node.text=txt
            nodes.append(node)
            runningY-=SVGOptions.fontSize+SVGOptions.lineSep
        return nodes

    def style(self):
        return self.styleDict


class Dep:

    #Makes a dependency from tok1 to tok2
    def __init__(self,tok1,tok2,dType,arcStyleDict={},labelStyleDict={}):
        self.tok1=tok1
        self.tok2=tok2
        if tok1.pos>tok2.pos:
            raise ValueError("Dep should always have tokens in linear order and no self dependencies: %d-%d %s %s %s"%(tok1.pos,tok2.pos,tok1.txt,tok2.txt,dType))
        self.type=dType
        self.height=0#layout() fills this later on
        #default style
        self.arcStyleDict={"fill":"none",
                       "stroke":"black",
                       "stroke-width":"1"}
        self.labelStyleDict={"text-anchor":"middle",
                            "fill":"black","font-size":str(SVGOptions.labelFontSize)+"px","font-family":"Monospace"}
        if self.type.startswith("*") and self.type.endswith("*"): #handle the *-marked bold-font
            self.type=self.type[1:-1]
            self.arcStyleDict["stroke-width"]="3"
            self.labelStyleDict["font-weight"]="bold"
        #override the defaults
        for k,v in arcStyleDict.items():
            self.arcStyleDict[k]=v
        #override the defaults
        for k,v in labelStyleDict.items():
            self.labelStyleDict[k]=v

    def minWidth(self):
        return textWidth(self.type,SVGOptions.labelFontSize)+2*SVGOptions.minDepPadding

    def computeParameters(self,textLines):
        y=self.tok1.y-(SVGOptions.fontSize+SVGOptions.lineSep)*textLines
        frox=self.tok1.x
        tox=self.tok2.x
        corner1x,corner1y=frox,y-self.height*SVGOptions.depVertSpace
        corner2x,corner2y=tox,y-self.height*SVGOptions.depVertSpace
        c1bx,c1by=corner1x,corner1y #Top left control point, beginning
        c1ex,c1ey=corner1x,corner1y
        c2bx,c2by=corner2x,corner2y
        c2ex,c2ey=corner2x,corner2y
        linebx=frox
        lineex=tox
        lineby=corner1y+(y-corner1y)*0.6
        lineey=lineby
        midx,midy=frox+(tox-frox)//2,y-self.height*SVGOptions.depVertSpace

        textW=textWidth(self.type,SVGOptions.labelFontSize)
        textH=SVGOptions.labelFontSize
        txtX,txtY=midx,midy+textH/2-4
        recx=txtX-textW/2-1
        recy=txtY-SVGOptions.labelFontSize
        recw=textW+4
        self.param={'frox':frox,
                    'y':y,
                    'c1bx':c1bx,
                    'c1by':c1by,
                    'c1ex':c1ex,
                    'c1ey':c1ey,
                    'midx':midx,
                    'midy':midy,
                    'c2bx':c2bx,
                    'c2by':c2by,
                    'c2ex':c2ex,
                    'c2ey':c2ey,
                    'tox':tox,
                    'linebx':linebx,
                    'lineby':lineby,
                    'lineex':lineex,
                    'lineey':lineey,
                    'textW':textW,
                    'textH':textH,
                    'txtX':txtX,
                    'txtY':txtY,
                    'recx':recx,
                    'recy':recy,
                    'recxe':recx+recw,
                    'recw':recw,
                    'rech':SVGOptions.labelFontSize+8}

    def arcSVG(self):
        spec1="M%(frox)d,%(y)d L%(linebx)d,%(lineby)d C%(c1bx)d,%(c1by)d %(c1ex)d,%(c1ey)d %(recx)d,%(midy)d"%self.param
        spec2="M%(recxe)d,%(midy)d C%(c2bx)d,%(c2by)d %(c2ex)d,%(c2ey)d %(lineex)d,%(lineey)d L%(tox)d,%(y)d"%self.param
        arcN1=ET.Element("path")
        arcN1.set("d",spec1)
        styleStr=";".join("%s:%s"%(var,val) for var,val in self.arcStyle().items())
        arcN1.set("style",styleStr)
        
        arcN2=ET.Element("path")
        arcN2.set("d",spec2)
        styleStr=";".join("%s:%s"%(var,val) for var,val in self.arcStyle().items())
        arcN2.set("style",styleStr)

        return [arcN1,arcN2]

    def labelSVG(self):
            

            recNode=ET.Element("rect")
            recNode.set("x",strint(self.param["recx"]))
            recNode.set("y",strint(self.param["recy"]))
            recNode.set("width",strint(self.param["recw"]))
            recNode.set("height",strint(self.param["rech"]))
            recNode.set("style","fill:white;")#stroke:black")
            
            labNode=ET.Element("text")
            labNode.set("systemlanguage","en")
            labNode.set("x",strint(self.param['txtX']))
            labNode.set("y",strint(self.param['txtY']))
            labNode.set("txt",self.type)
            labNode.text=self.type
            styleStr=";".join("%s:%s"%(var,val) for var,val in self.labelStyle().items())
            labNode.set("style",styleStr)
            return [recNode,labNode]

    def arcStyle(self):
        return self.arcStyleDict

    def labelStyle(self):
        return self.labelStyleDict


def simpleTokenLayout(tokens,dependencies,baseY):
    #First a simple, initial layout for the tokens
    widths=[t.width() for t in tokens]
    
    y=baseY
    tokens[0].x=widths[0]//2
    tokens[0].y=y
    for idx in range(1,len(tokens)):
        tokens[idx].x=tokens[idx-1].x+widths[idx-1]//2+SVGOptions.tokenSpace+widths[idx]//2
        tokens[idx].y=y

#nudges tokens, taking into account dependencies on one level
def nudgeTokens(tokens,deps):
    deps.sort(cmp=lambda a,b: cmp(a.tok1.pos,b.tok1.pos)) #we have dependencies on one level, no ties should happen!
    nudge=[0 for t in tokens]
    for d in deps:
        currentDX=d.tok2.x - d.tok1.x
        minW=d.minWidth()
        if minW>currentDX: #need to nudge token2 a bit to the right
            nudge[d.tok2.pos]=minW-currentDX
    #now apply the nudge
    cumulative=0
    for idx,nudgeX in enumerate(nudge):
        cumulative+=nudgeX
        tokens[idx].x+=cumulative

#calls nudgeTokens() one layer at a time
def improveTokenLayout(tokens,dependencies):
    dependencies.sort(cmp=lambda a,b:cmp(a.height,b.height))
    #gather height breaks
    breaks=[]
    for idx in range(1,len(dependencies)):
        if dependencies[idx].height!=dependencies[idx-1].height:
            breaks.append(idx-1)
    breaks=[0]+breaks+[len(dependencies)-1]
    for idx in range(1,len(breaks)):
        nudgeTokens(tokens,dependencies[breaks[idx-1]:breaks[idx]+1])
        

def depCMP(a,b):
    aLen=a.tok2.pos-a.tok1.pos
    bLen=b.tok2.pos-b.tok1.pos
    if aLen!=bLen:
        return cmp(aLen,bLen)
    else:
        return cmp(a.tok1.pos,b.tok1.pos)

def depHeights(tokenCount,deps):
    if tokenCount<2:
        return 0
    heights=[0 for x in range(tokenCount-1)]
    deps.sort(cmp=depCMP)
    for dep in deps:
        maxH=max(heights[tPos] for tPos in range(dep.tok1.pos,dep.tok2.pos))
        dep.height=maxH+1
        for tPos in range(dep.tok1.pos,dep.tok2.pos):
            heights[tPos]=maxH+1
    return max(heights)

widthRe=re.compile(r".*stroke-width:([0-9]+).*")
def recoverWidth(styleStr):
    match=widthRe.match(styleStr)
    if match:
        return int(match.group(1))
    else:
        return 0

def drawOrder(a,b):
    if a.tag!=b.tag:
        if a.tag=="path": #always draw the arcs first
            return -1
        if a.tag=="text": #always draw text last
            return +1
        assert a.tag=="rect", a.tag
        if b.tag=="path":
            return +1
        if b.tag=="text":
            return -1
        assert False
    elif a.tag=="path" and b.tag=="path":
        return cmp(recoverWidth(a.get("style")),recoverWidth(b.get("style")))
    else:
        return 0
    
def generateSVG(tokens,dependencies):
    layout(tokens,dependencies)
    tree=ET.Element("svg")
    tree.set("xmlns","http://www.w3.org/2000/svg")
    tree.set("xmlns:xlink","http://www.w3.org/1999/xlink")
    tree.set("version","1.1")
    tree.set("baseProfile","full")
    allNodes=[]
    totalWidth=0
    totalHeight=tokens[0].y+10
    if SVGOptions.whAttributes:
        tree.set("height",strint(totalHeight))
    for t in tokens:
        allNodes.extend(t.toSVG())
        tokX=t.x+t.width()
        if tokX>totalWidth:
            totalWidth=tokX
    if SVGOptions.whAttributes:
        tree.set("width",strint(totalWidth))
    for d in dependencies:
        allNodes.extend(d.arcSVG())
        allNodes.extend(d.labelSVG())
    allNodes.sort(cmp=drawOrder)
    for n in allNodes:
        tree.append(n)
    return tree

#The main layout function -> fills in all the parameters needed to draw the tree
def layout(tokens,deps):
    maxHeight=depHeights(len(tokens),deps)
    baseY=(len(tokens[0].otherLines)+1)*(SVGOptions.fontSize+SVGOptions.lineSep)+SVGOptions.lineSep+maxHeight*SVGOptions.depVertSpace+SVGOptions.labelFontSize//2+5
    simpleTokenLayout(tokens,deps,baseY)
    improveTokenLayout(tokens,deps)
    for dep in deps:
        dep.computeParameters(1+len(tokens[0].otherLines))


def styleStr2Dict(s):
    if not s:
        return {}
    s=s.strip()
    if s.endswith(";"):
        s=s[:-1]
    d={}
    for x in s.split(";"):
        try:
            k,v=x.split(":")
        except:
            print >> sys.stderr, ">>",x,"<<"
            raise
        d[k]=v
    return d

depRe=re.compile(r"^(\S+) +(\S+) +(\S+) *(#ARC *(.*?))? *(#LAB *(.*))?$")
tokRe=re.compile(r"^(\S+) *#TXT *(.*)")

def readInput(fName):
    lines=codecs.open(fName,"rt","utf-8")
    tokens=None
    deps=[]
    for line in lines:
        line=line.strip()
        if not line or line[0]=="#":
            continue
        if line.startswith("tokens:"):
            tokLine=line[7:].strip()
            if not tokens:
                tokens=[Token(txt,idx) for (idx,txt) in enumerate(tokLine.split())]
            else:
                texts=tokLine.split()
                assert len(texts)==len(tokens), "This token line has an uneven number of tokens: %s"%tokLine
                for tok,txt in zip(tokens,texts):
                    if txt!="<<NONE>>":
                        tok.otherLines.append(txt)
                    else:
                        tok.otherLines.append("")
        else: #we have a dependency or token style
            if not tokens:
                raise ValueError("You must have tokens line, starting with \"tokens:\"")
            match=tokRe.match(line)
            if match:
                tokTxt,tokenSpec=tokSpec(match.group(1))
                candidates=[tok for tok in tokens if tok.matches(tokTxt,tokenSpec)]
                if len(candidates)!=1:
                    raise ValueError("I have %d candidates for %s in dependency \"%s\""%(len(candidates),match.group(1),line))
                token=candidates[0]
                txtStyleDict=styleStr2Dict(match.group(2))
                for k,v in txtStyleDict.items():
                    token.styleDict[k]=v
                continue
            match=depRe.match(line)
            if match:
                t1=match.group(1)
                dType=match.group(2)
                t2=match.group(3)
                t1txt,t1spec=tokSpec(t1)
                matching1=[tok for tok in tokens if tok.matches(t1txt,t1spec)]
                if len(matching1)!=1:
                    raise ValueError("I have %d candidates for %s in dependency \"%s\""%(len(matching1),t1,line))
                t2txt,t2spec=tokSpec(t2)
                matching2=[tok for tok in tokens if tok.matches(t2txt,t2spec)]
                if len(matching2)!=1:
                    raise ValueError("I have %d candidates for %s in dependency \"%s\""%(len(matching2),t2,line))
                tok1=matching1[0]
                tok2=matching2[0]
                arcStyleDict=styleStr2Dict(match.group(5))
                labStyleDict=styleStr2Dict(match.group(7))
                if tok1==tok2:
                    print >> sys.stderr, "Warning: Ignoring a self-dependency!"
                    continue
                deps.append(Dep(tok1,tok2,dType,arcStyleDict,labStyleDict))
                continue
            raise ValueError("Do not understand this line: %s"%line)
            
    if len(deps)==0:
        raise ValueError("Zero dependencies read!")
    return tokens,deps
                                 
        
def indent(elem, level=0):
    #shamelessly stolen from ET documentation
    """ indent-function as defined in cElementTree-documentation
    
    This function will become part of cElementTree in some future
    release. Until then, it can be used from here. This function
    indents the xml-tree, so that it is more readable when written
    out. 
    
    Keyword arguments:
    elem -- (Element) root of the tree to indent 
    level -- (int) starting level of indentation
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def writeUTF8(rootElement,out):
    indent(rootElement)
    if isinstance(out,str):
        f=open(out,"wt")
        print >> f, '<?xml version="1.0" encoding="UTF-8"?>'
        ET.ElementTree(rootElement).write(f,"utf-8")
        f.close()
    else:
        print >> out, '<?xml version="1.0" encoding="UTF-8"?>'
        ET.ElementTree(rootElement).write(out,"utf-8")
    

if __name__=="__main__":
    import optparse
    desc=\
"""A program for plotting dependency structures into SVG.

cat example.dep | python draw_dg.py > example.svg

The format of the dependency file is specified in example.dep

To convert a .svg to .pdf, you can use for example inkscape

inkscape -A file.pdf file.svg
"""
    parser=optparse.OptionParser(usage=desc)
    parser.add_option("--tokenSize", dest="fontSize",action="store",default=24,help="Token font size.", metavar="INTEGER")
    parser.add_option("--labelSize", dest="labelFontSize",action="store",default=20,help="Dependency label font size.", metavar="INTEGER")
    parser.add_option("--depVSpace", dest="depVertSpace",action="store",default=20,help="Vertical space between dependency layers.", metavar="INTEGER")
    parser.add_option("--tokenHSpace", dest="tokenSpace",action="store",default=10,help="Horizontal space between tokens.", metavar="INTEGER")
    parser.add_option("--lineVSpace", dest="lineSep",action="store",default=5,help="Vertical separation between text lines.", metavar="INTEGER")
    parser.add_option("--minDepPadding", dest="minDepPadding",action="store",default=10,help="Horizontal space reserved for the curve of a dependency.", metavar="INTEGER")
    (options,args)=parser.parse_args()

    SVGOptions.fontSize=int(options.fontSize)
    SVGOptions.labelFontSize=int(options.labelFontSize)
    SVGOptions.depVertSpace=int(options.depVertSpace)
    SVGOptions.tokenSpace=int(options.tokenSpace)
    SVGOptions.lineSep=int(options.lineSep)
    SVGOptions.minDepPadding=int(options.minDepPadding)
    
    
    
    
    tokens,deps=readInput("/dev/stdin")
    t=generateSVG(tokens,deps)
    writeUTF8(t,sys.stdout)
    print
