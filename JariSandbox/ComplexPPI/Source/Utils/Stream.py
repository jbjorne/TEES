"""
Capture stdout or stderr messages to a log file

Based on code by Greg Pinero (Primary Searcher)

Capture print statments and write them to a log file
but still allow them to be printed on the screen.
"""
import sys
import time

class StreamModifier:
    """
    This class implements a write-method and can therefore replace a stream
    such as sys.stderr or sys.stdout. The write method first writes the text
    to a log file, then passes it on to the original stream.
    """
    def __init__(self, stream):
        self.stream = stream
        self.logfile = None
        self.indent = None
        self.timeStamp = None
        self.timeStampDuplicates = False
        self.prevTime = None
        self.newLine = True
        self.buffer = ""
    
    def setLog(self, logfile=None):
        self.logfile = logfile
    
    def setIndent(self, indent=None):
        self.indent = indent
    
    def setTimeStamp(self, format=None, duplicates=False):
        self.timeStamp = format
        self.timeStampDuplicates = duplicates
    
    def writeToLog(self, text):
        """
        Write directly to the log file without sending the input to the stream
        """
        if self.logfile != None:
            self.logfile.write(text)
            self.logfile.flush()
    
    def write(self, text):
        if text == None or text == "":
            return
        """
        Send the text to the stream after optionally writing it to the log file.
        """
        if self.indent != None:
            if self.newLine:
                text = self.indent + text 
            lastChar = text[-1]
            text = text[:-1]
            if lastChar == "\n":
                self.newLine = True
            else:
                self.newLine = False
            text = text.replace("\n","\n"+self.indent)
            text += lastChar
        self.stream.write(text)
        self.stream.flush()
        if self.logfile != None:
            for char in text:
                if char == "\r":
                    self.buffer = ""
                elif char == "\n":
                    timeString = time.strftime(self.timeStamp)
                    if timeString == self.prevTime and not self.timeStampDuplicates:
                        timeString = len(timeString) * " "
                    else:
                        self.prevTime = timeString
                    if self.timeStamp != None:
                        self.buffer = timeString + "\t" + self.buffer
                    self.logfile.write(self.buffer + "\n")
                    self.buffer = ""
                else:
                    self.buffer += char
            self.logfile.flush()

def setLog(filename=None, clear=False):
    """
    Replace sys.stderr and sys.stdout with a StreamModifier, capturing
    all output for these streams to a log file while still passing it
    to the original stream.
    """
    if not isinstance(sys.stdout, StreamModifier):
        sys.stdout = StreamModifier(sys.stdout)
    if not isinstance(sys.stderr, StreamModifier):
        sys.stderr = StreamModifier(sys.stderr)
    if filename != None:
        if clear:
            logfile = open(filename,"wt")
        else:
            logfile = open(filename,"at")
        sys.stdout.setLog(logfile)
        sys.stderr.setLog(logfile)
    else:
        sys.stdout.setLog()
        sys.stdout.setLog()

def setIndent(string=None):
    if not isinstance(sys.stdout, StreamModifier):
        sys.stdout = StreamModifier(sys.stdout)
    if not isinstance(sys.stderr, StreamModifier):
        sys.stderr = StreamModifier(sys.stderr)
    sys.stdout.setIndent(string)
    sys.stderr.setIndent(string)

def setTimeStamp(format=None, duplicates=False):
    if not isinstance(sys.stdout, StreamModifier):
        sys.stdout = StreamModifier(sys.stdout)
    if not isinstance(sys.stderr, StreamModifier):
        sys.stderr = StreamModifier(sys.stderr)
    sys.stdout.setTimeStamp(format, duplicates)
    sys.stderr.setTimeStamp(format, duplicates)
