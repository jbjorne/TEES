from Utils.InteractionXML.GraphViz import toGraphViz
from Tkinter import *
import Utils.ElementTreeUtils as ETUtils
import base64
#import Image, ImageTk, rsvg, cairo
#from PIL import ImageTk, Image

class Application(Frame):
    def say_hi(self):
        print "hi there, everyone!"

    def createWidgets(self):
        self.canvas = Canvas(self, width=700, height=300, bg='white')
        self.canvas.pack(side='top', fill='both', expand='yes')
        
        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit

        self.QUIT.pack({"side": "left"})

        self.hi_there = Button(self)
        self.hi_there["text"] = "Hello",
        self.hi_there["command"] = self.say_hi

        self.hi_there.pack({"side": "left"})

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

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
    xml = ETUtils.ETFromObj(inPath)
    sentences = xml.findall("document/sentence")
    if firstId == None:
        firstId = sentences[0].get("id")
    gif = toGraphViz(xml, firstId, None, parse, color, colorNum, colorParse, colorNumParse)
    gif = base64.b64encode(gif)
    #print svg
    #tk_image = svgPhotoImage
    root = Tk()
    photo = PhotoImage(data=gif)
    app = Application(master=root)
    #app.FRAME.configure(image=gif)
    app.canvas.create_image(100, 100, image=photo, anchor='nw')
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