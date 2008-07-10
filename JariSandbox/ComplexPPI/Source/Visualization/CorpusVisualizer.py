import sys, os, shutil
import GraphToSVG
from HtmlBuilder import *
import networkx as NX

class CorpusVisualizer:
    def __init__(self, outputDirectory, deleteDirectoryIfItExists=False):
        self.outDir = outputDirectory
        self.__makeOutputDirectory(deleteDirectoryIfItExists)
        self.builder = None

    def __makeOutputDirectory(self, deleteDirectoryIfItExists):
        if os.path.exists(self.outDir):
            if deleteDirectoryIfItExists:
                print >> sys.stderr, "Output directory exists, removing", self.outDir
                shutil.rmtree(self.outDir)
            else:
                sys.exit("Error, output directory exists.")
        print >> sys.stderr, "Creating output directory", self.outDir
        os.mkdir(self.outDir)
        os.mkdir(self.outDir+"/sentences")
        os.mkdir(self.outDir+"/svg")
        shutil.copytree("../../PPIDependencies/Visualization/js",self.outDir+"/js")
    
    def getMatchingEdgeStyles(self, graph1, graph2, posColor, negColor):
        arcStyles = {}
        labelStyles = {}
        annEdges = graph1.edges()
        for annEdge in annEdges:
            if graph2.has_edge(annEdge[0], annEdge[1]) or graph2.has_edge(annEdge[1], annEdge[0]):
                arcStyles[annEdge] = {"stroke":posColor}
                labelStyles[annEdge] = {"fill":posColor}
            else:
                arcStyles[annEdge] = {"stroke":negColor}
                labelStyles[annEdge] = {"fill":negColor}
        return arcStyles, labelStyles
    
    def makeExampleGraph(self, builder, sentenceGraph, examples):
        exampleGraph = NX.XDiGraph()
        for token in sentenceGraph.tokens:
            exampleGraph.add_node(token)
        for example in examples:
            exampleGraph.add_edge(example[3]["t1"], example[3]["t2"])

        builder.header("Classification",4)
        svgTokens = GraphToSVG.tokensToSVG(sentenceGraph.tokens)
        arcStyles, labelStyles = self.getMatchingEdgeStyles(exampleGraph, sentenceGraph.interactionGraph, "green", "red" )
        svgEdges = GraphToSVG.edgesToSVG(svgTokens, exampleGraph, arcStyles, labelStyles, None)
        sentenceId = sentenceGraph.getSentenceId()
        svgElement = GraphToSVG.writeSVG(svgTokens, svgEdges, self.outDir+"/svg/"+sentenceId+"_learned.svg")
        builder.svg("../svg/" + sentenceId + "_learned.svg",svgElement.attrib["width"],svgElement.attrib["height"],id="learned_graph")
        builder.lineBreak()
    
    def makeSentencePage(self, sentenceGraph, examples, prevAndNextId=None):
        entityElements = sentenceGraph.entities
        entityTextById = {}
        for entityElement in entityElements:
            entityTextById[entityElement.get("id")] = entityElement.get("text")
        
        # Boot-it NG
        builder = HtmlBuilder()
        sentenceId = sentenceGraph.getSentenceId()
        builder.newPage("Sentence " + sentenceId, "../")
        builder.addScript("../js/highlight_svg.js")
        builder.body.set("onload","for(i in document.forms){document.forms[i].reset();}")
        
        builder.div()
        builder.header("Sentence " + sentenceId,1)
        #builder.lineBreak()
        
        if prevAndNextId != None:
            if prevAndNextId[0] != None:
                builder.link(prevAndNextId[0]+".html","previous")
            else:
                builder.span("previous","color:#0000FF;")
            if prevAndNextId[1] != None:
                builder.link(prevAndNextId[1]+".html","next")
            else:
                builder.span("next","color:#0000FF;")
    
        builder.span("BioInfer-ID: " + sentenceGraph.sentenceElement.attrib["origId"])
        builder.closeElement() # div      
        builder.lineBreak()
        
        # Parse SVG
        builder.header("Parse",4)
        svgTokens = GraphToSVG.tokensToSVG(sentenceGraph.tokens)
        svgDependencies = GraphToSVG.edgesToSVG(svgTokens, sentenceGraph.dependencyGraph)
        svgElement = GraphToSVG.writeSVG(svgTokens, svgDependencies,self.outDir+"/svg/"+sentenceId+".svg")
        builder.svg("../svg/" + sentenceId + ".svg",svgElement.attrib["width"],svgElement.attrib["height"],id="dep_graph")
        builder.lineBreak()
        
        # Interaction SVG
        if sentenceGraph.interactionGraph != None:
            builder.header("Annotation",4)
            arcStyles, labelStyles = self.getMatchingEdgeStyles(sentenceGraph.interactionGraph, sentenceGraph.dependencyGraph, "orange", "#F660AB" )
            svgInteractionEdges = GraphToSVG.edgesToSVG(svgTokens, sentenceGraph.interactionGraph, arcStyles, labelStyles)
            svgElement = GraphToSVG.writeSVG(svgTokens, svgInteractionEdges,self.outDir+"/svg/"+sentenceId+"_ann.svg")
            builder.svg("../svg/" + sentenceId + "_ann.svg",svgElement.attrib["width"],svgElement.attrib["height"],id="ann_graph")
            builder.lineBreak()
        
        # Classification svg
        self.makeExampleGraph(builder, sentenceGraph, examples)      
        
        builder.table(0,align="center",width="100%")
        builder.tableRow()
        # interactions
        pairElements = sentenceGraph.interactions
        builder.tableData(valign="top")
        builder.header("Interactions",4)
        builder.table(1,True)
        builder.tableHead()
        builder.tableRow()
        builder.tableHeader("id", True)
        builder.tableHeader("e1", True)
        builder.tableHeader("e2", True)
        builder.tableHeader("e1 word", True)
        builder.tableHeader("e2 word", True)
        builder.tableHeader("interaction", True)
        th = builder.tableHeader("view",True)
        th.set("class","{sorter: false}")
        builder.closeElement()
        builder.closeElement() # close tableHead
        builder.tableBody()
        for pairElement in sentenceGraph.interactions:
            tr = builder.tableRow()
            #tr.set( "onmouseover", getPairHighlightCommand("main_parse",pairElement.get("e1"),pairElement.get("e2"),entityTokens,"highlightPair") )
            #tr.set( "onmouseout", getPairHighlightCommand("main_parse",pairElement.get("e1"),pairElement.get("e2"),entityTokens,"deHighlightPair") )
            builder.tableData(pairElement.get("id").split(".")[-1][1:], True)
            builder.tableData(pairElement.get("e1").split(".")[-1][1:], True)
            builder.tableData(pairElement.get("e2").split(".")[-1][1:], True)
            builder.tableData(entityTextById[pairElement.get("e1")], True)
            builder.tableData(entityTextById[pairElement.get("e2")], True)
            builder.tableData("Dummy", True)
            builder.tableData()
            builder.form()
            input = builder.formInput("checkbox")
            #input.set("onClick",getPairHighlightCommand("main_parse",pairElement.get("e1"),pairElement.get("e2"),entityTokens,"toggleSelectPair",pairElement.get("id")) )
            builder.closeElement() # form
            builder.closeElement() # tableData
            builder.closeElement()
        builder.closeElement() # close tableBody
        builder.closeElement() # close table
        
        # entities
        builder.tableData(valign="top")
        builder.header("Entities",4)
        builder.table(1,True)
        builder.tableHead()
        builder.tableRow()
        builder.tableHeader("id", True)
        builder.tableHeader("text", True)
        builder.tableHeader("type", True)
        builder.tableHeader("charOffset", True)
        builder.closeElement() # close tableRow
        builder.closeElement() # close tableHead
        entityElements = sentenceGraph.entities
        builder.tableBody()
        for entityElement in entityElements:
            builder.tableRow()
            builder.tableData(entityElement.get("id").split(".")[-1][1:], True)
            builder.tableData(entityElement.get("text"), True)
            builder.tableData(entityElement.get("type"), True)
            builder.tableData(entityElement.get("charOffset"), True)
            builder.closeElement()
        builder.closeElement() # close tableBody
        builder.closeElement() # close table
        
        builder.closeElement() # close row
        builder.closeElement() # close table
        
        builder.closeElement() # close row
        builder.closeElement() # close table
            
        builder.write(self.outDir + "/sentences/"+sentenceId+".html")
        repairApostrophes(self.outDir + "/sentences/"+sentenceId+".html")

def repairApostrophes(filename):
    f = open(filename)
    lines = f.readlines()
    f.close()
    
    for i in range(len(lines)):
        apos = lines[i].find("&apos;")
        while apos != -1:
            lines[i] = lines[i][:apos] + "'" + lines[i][apos + 6:]
            apos = lines[i].find("&apos;")
        
        lt = lines[i].find("&lt;")
        while lt != -1:
            lines[i] = lines[i][:lt] + "<" + lines[i][lt + 4:]
            lt = lines[i].find("&lt;")

        gt = lines[i].find("&gt;")
        while gt != -1:
            lines[i] = lines[i][:gt] + ">" + lines[i][gt + 4:]
            gt = lines[i].find("&gt;")
    
    f = open(filename,"wt")
    f.writelines(lines)
    f.close()
