from Utils.InteractionXML.GraphViz import toGraphViz
import Tkinter as tk
import Utils.ElementTreeUtils as ETUtils
import base64
#import Image, ImageTk, rsvg, cairo
#from PIL import ImageTk, Image

class Application(tk.Frame):
    def __init__(self, xml, index=0, parse="McCC", color="set27", colorNum=7, colorParse="set27", colorNumParse=7, master=None):
        tk.Frame.__init__(self, master)
        self.xml = ETUtils.ETFromObj(xml)
        self.sentences = self.xml.findall("document/sentence")
        self.index = 0
        self.parse = parse
        self.color = color
        self.colorNum = colorNum
        self.colorParse = colorParse
        self.colorNumParse = colorNumParse
        self.pack(fill=tk.BOTH, expand=tk.YES)
        self.createWidgets()
        self.showSentence()
        self.bind("<Configure>", self.onResize)
    
    def onResize(self, event):
        self.showSentence(event.width, event.height)
    
    def nextSentence(self):
        self.index = min(len(self.sentences) - 1, self.index + 1)
        self.showSentence()
    
    def prevSentence(self):
        self.index = max(0, self.index - 1)
        self.showSentence()
    
    def showSentence(self, width=None, height=None):
        sentence = self.sentences[self.index]
        sentenceId = sentence.get("id")
        self.label['text'] = sentenceId
        if sentence.get("relation") != None:
            self.label['text'] += " (" + sentence.get("relation") + ")"
        if width == None:
            width = self.canvas.winfo_width()
        if height == None:
            height = self.canvas.winfo_height()
        if width == 1:
            width = self.canvas["width"]
        if height == 1:
            height = self.canvas["height"]
        print width, height
        #gif = toGraphViz(self.xml, sentenceId, None, self.parse, self.color, self.colorNum, self.colorParse, self.colorNumParse, width=self.canvas['width'], height=self.canvas['height'])
        gif = toGraphViz(self.xml, sentenceId, None, self.parse, self.color, self.colorNum, self.colorParse, self.colorNumParse, width, height)
        gif = base64.b64encode(gif)
        self.photo = tk.PhotoImage(data=gif)
        #self.photo = self.photo.subsample(700)
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')

    def createWidgets(self):
        self.canvas = tk.Canvas(self, width=700, height=300, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        
#         self.QUIT = Button(self)
#         self.QUIT["text"] = "QUIT"
#         self.QUIT["fg"]   = "red"
#         self.QUIT["command"] =  self.quit
#         self.QUIT.pack({"side": "left"})
        
        self.label = tk.Label(self)
        self.label["text"] = "N/A",
        self.label.pack({"side": "left"})

        self.next = tk.Button(self)
        self.next["text"] = "Next",
        self.next["command"] = self.nextSentence
        self.next.pack({"side": "right"})
        
        self.next = tk.Button(self)
        self.next["text"] = "Prev",
        self.next["command"] = self.prevSentence
        self.next.pack({"side": "right"})

# def svgPhotoImage(self, svgString):
#     "Returns a ImageTk.PhotoImage object represeting the svg file" 
#     # Based on pygame.org/wiki/CairoPygame and http://bit.ly/1hnpYZY        
#     svg = rsvg.Handle(svgString) #rsvg.Handle(file=file_path_name)
#     width, height = svg.get_dimension_data()[:2]
#     surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
#     context = cairo.Context(surface)
#     #context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
#     svg.render_cairo(context)
#     tk_image=ImageTk.PhotoImage('RGBA')
#     image=Image.frombuffer('RGBA',(width,height),surface.get_data(),'raw','BGRA',0,1)
#     tk_image.paste(image)
#     return tk_image

def run(inPath, firstId, outPath, parse, color, colorNum, colorParse, colorNumParse):
    #xml = ETUtils.ETFromObj(inPath)
    #sentences = xml.findall("document/sentence")
    #if firstId == None:
    #    firstId = sentences[0].get("id")
    #gif = toGraphViz(xml, firstId, None, parse, color, colorNum, colorParse, colorNumParse)
    #gif = base64.b64encode(gif)
    #print svg
    #tk_image = svgPhotoImage
    root = tk.Tk()
    app = Application(master=root, xml=inPath)
    #app.FRAME.configure(image=gif)
    #app.canvas.create_image(0, 0, image=photo, anchor='nw')
    app.mainloop()
    root.destroy()

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input interaction XML file")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file stem")
    optparser.add_option("-d", "--id", default=None, dest="id", help="sentence id")
    optparser.add_option("-p", "--parse", default="McCC", dest="parse", help="parse name")
    optparser.add_option("-c", "--color", default="set27", dest="color", help="Event color scheme")
    optparser.add_option("-e", "--colorParse", default="set27", dest="colorParse", help="Parse color scheme")
    optparser.add_option("-n", "--colorNum", default=7, type="int", dest="colorNum", help="Number of colors in the event color scheme")
    optparser.add_option("-m", "--colorNumParse", default=7, type="int", dest="colorNumParse", help="Number of colors in the parse color scheme")
    (options, args) = optparser.parse_args()
    
    if options.output == None:
        run(options.input, options.id, options.output, options.parse, options.color, options.colorNum, options.colorParse, options.colorNumParse)
    else:
        toGraphViz(options.input, options.id, options.output, options.parse, options.color, options.colorNum, options.colorParse, options.colorNumParse)