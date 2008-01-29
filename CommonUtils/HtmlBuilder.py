# A tool for building HTML-pages. Undocumented, because I didn't
# have time to document this yes, but still in CommonUtils because
# it was needed to visualize the PPI_learning stuff.

import cElementTree as ET
import cElementTreeUtils as ETUtils

# Doesn't work yet
class FrameSetBuilder:
    def __init__(self):
        self.page = None
        self.body = None
    
    def newPage(self, title, rootDirectory="../"):
         # build a tree structure
        root = ET.Element("html")
        head = ET.SubElement(root, "head")
        title = ET.SubElement(head, "title")
        title.text = title
        body = ET.SubElement(root, "body")
        body.set("bgcolor", "#ffffff")
        
        self.page = root
        self.head = head
        self.body = body
        self.parents = [self.body]
        self.tableSorterIncluded = False
        
        self.rootDirectory = rootDirectory
        self.jQueryPath = rootDirectory + "js/jquery/" 

# This one works
class HtmlBuilder:
    def __init__(self):
        self.page = None
        self.body = None
    
    def newPage(self, title, rootDirectory="../"):
         # build a tree structure
        root = ET.Element("html")
        head = ET.SubElement(root, "head")
        title = ET.SubElement(head, "title")
        title.text = title
        body = ET.SubElement(root, "body")
        body.set("bgcolor", "#ffffff")
        
        self.page = root
        self.head = head
        self.body = body
        self.parents = [self.body]
        self.tableSorterIncluded = False
        
        self.rootDirectory = rootDirectory
        self.jQueryPath = rootDirectory + "js/jquery/" 
        
    def includeTableSorter(self):
        self.themeLink("css/jq.css")
        self.themeLink(self.jQueryPath+"themes/blue/style.css")
        self.addScript(self.jQueryPath+"jquery-latest.js")
        self.addScript(self.jQueryPath+"jquery.dimensions.pack.js")
        self.addScript(self.jQueryPath+"jquery.metadata.js")
        self.addScript(self.jQueryPath+"jquery.tablesorter.pack.js")
        self.addScript(self.jQueryPath+"addons/pager/jquery.tablesorter.pager.js")
        self.addScript(None, 'window.tableFile="table-metadata-disable.html";')
        tableSorterString = "$(document).ready(function()\n{\n"
        tableSorterString += "// call the tablesorter plugin, the magic happens in the markup\n"
        tableSorterString += "$(\"table\").tablesorter();\n});\n"
        self.addScript(None, tableSorterString, "js")
        self.tableSorterIncluded = True
    
    def addScript(self, src, text=None, id=None):
        script = ET.SubElement(self.head, "script")
        script.set("type","text/javascript")
        if src != None:
            script.set("src",src)
        if text != None:
            script.text = text
        else:
            script.text = " "
        if id != None:
            script.set("id",id)
        return script

    def themeLink(self,href):
        themeLink = ET.SubElement(self.head, "link")
        themeLink.set("rel","stylesheet")
        themeLink.set("type","text/css")
        themeLink.set("media","print, projection, screen")
        themeLink.set("href",href)
    
    def lineBreak(self):
        return ET.SubElement(self.parents[-1], "br")
    
    def header(self,text,level=1):
        header = ET.SubElement(self.parents[-1], "h"+str(level))
        header.text = text
    
    def div(self):
        div = ET.SubElement(self.parents[-1], "div")
        self.parents.append(div)
        return div
    
    def span(self,text,style=None):
        span = ET.SubElement(self.parents[-1], "span")
        span.text = text
        if style != None:
            span.set("style",style)
    
    def svg(self,filename,width=None,height=None,id=None,onload=None):
        #if title == None:
        #    title = filename
        #object = ET.SubElement(self.parents[-1], "object")
        object = ET.SubElement(self.parents[-1], "embed")
        #object.set("type","image/svg+xml")
        #object.set("name",title)
        #object.set("data",filename)
        object.set("src",filename)
        if width != None:
            object.set("width",str(width))
        if height != None:
            object.set("height",str(height))
        if onload != None:
            object.set("onload",onload)
        if id != None:
            object.set("id",id)
        object.text = " "
        return object
    
    def paragraph(self):
        return ET.SubElement(self.parents[-1], "p")
        
    def write(self, filename):
        # wrap it in an ElementTree instance, and save as XML
        ETUtils.indent(self.page)
        tree = ET.ElementTree(self.page)
        tree.write(filename)
    
    def link(self, url, title=None):
        if title == None:
            title = url
        link = ET.SubElement(self.parents[-1], "a")
        link.set("href", url)
        link.text = title
        return link
    
    def table(self, border, sortable=False, align=None, width=None):
        table = ET.SubElement(self.parents[-1], "table")
        if sortable:
            if not self.tableSorterIncluded:
                self.includeTableSorter()
            table.set("class","tablesorter")
            table.set("cellspacing",str(1))
        else:
            table.set("border",str(border))
        if align != None:
            table.set("align", align)
        if width != None:
            table.set("width", str(width))
        self.parents.append(table)
        return table
    
    def tableRow(self):
        row = ET.SubElement(self.parents[-1], "tr")
        self.parents.append(row)
        return row
    
    def closeElement(self):
        self.parents.pop()
    
    def tableData(self, text=None, closeImmediately=False, valign=None):
        data = ET.SubElement(self.parents[-1], "td")
        if text != None:
            data.text = text
        if valign != None:
            data.set("valign",valign)
        if not closeImmediately:
            self.parents.append(data)
        return data
    
    def tableHeader(self, text=None, closeImmediately=False):
        data = ET.SubElement(self.parents[-1], "th")
        if text != None:
            data.text = text
        if not closeImmediately:
            self.parents.append(data)
        return data
    
    def tableHead(self):
        thead = ET.SubElement(self.parents[-1], "thead")
        self.parents.append(thead)
        return thead
    
    def tableBody(self):
        tbody = ET.SubElement(self.parents[-1], "tbody")
        self.parents.append(tbody)
    
    def form(self):
        form = ET.SubElement(self.parents[-1], "form")
        self.parents.append(form)
        return form
    
    def formInput(self, type, name=None, text=None ):
        input = ET.SubElement(self.parents[-1], "input")
        input.set("type",type)
        if name != None:
            input.set("name",name)
        if text != None:
            input.set("text",text)
        return input