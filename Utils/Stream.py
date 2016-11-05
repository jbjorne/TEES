"""
Capture stdout or stderr messages to a log file

Based on code by Greg Pinero (Primary Searcher)

Capture print statments and write them to a log file
but still allow them to be printed on the screen.
"""
import sys, os
import time
import codecs

class StreamModifier:
    """
    This class implements a write-method and can therefore replace a stream
    such as sys.stderr or sys.stdout. The write method first writes the text
    to a log file, then passes it on to the original stream.
    """
    def __init__(self, stream):
        self.stream = stream
        self.logfiles = []
        self.logfilenames = []
        self.indent = None
        self.timeStamp = None
        self.timeStampDuplicates = False
        self.prevTime = None
        self.newLine = True
        self.buffer = ""
    
    def setLog(self, logfile=None):
        if logfile != None:
            self.logfiles = [logfile]
            self.logfilenames = [logfile.name]
        else:
            self.logfiles = []
            self.logfilenames = []
    
    def addLog(self, logfile):
        self.logfiles.append(logfile)
        self.logfilenames.append(logfile.name)
    
    def removeLog(self, logfileName, streamName):
        logfilesToKeep = []
        logfilenamesToKeep = []
        removed = None
        removedName = None
        for i in range(len(self.logfiles)):
            if self.logfilenames[i] != logfileName:
                logfilesToKeep.append(self.logfiles[i])
                logfilenamesToKeep.append(self.logfilenames[i])
            else:
                removed = self.logfiles[i]
                removedName = self.logfilenames[i]
        self.logfiles = logfilesToKeep
        self.logfilenames = logfilenamesToKeep
        
        if removedName != None:
            print >> sys.stderr, "Stopped logging", streamName, "to", removedName
        else:
            print >> sys.stderr, "Log not open for ", streamName + ":", logfileName
        return removed
    
    def setIndent(self, indent=None):
        self.indent = indent
    
    def setTimeStamp(self, format=None, duplicates=False):
        self.timeStamp = format
        self.timeStampDuplicates = duplicates
    
    def writeToStream(self, text):
        """
        Write directly to the stream without adding to the log file
        """
        self.stream.write(text)
    
    def writeToLog(self, text, filename):
        """
        Write directly to the log file without sending the input to the stream
        """
        for logfile in self.logfiles:
            if filename == None or logfile.name == filename:
                logfile.write(text)
                logfile.flush()
    
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
        if len(self.logfiles) > 0:
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
                    for logfile in self.logfiles:
                        logfile.write(self.buffer + "\n")
                    self.buffer = ""
                else:
                    self.buffer += char
            for logfile in self.logfiles:
                logfile.flush()
    
    def flush(self):
        self.stream.flush()

def openLog(filename="log.txt", clear=False, logCmd=True):
    if os.path.dirname(filename) != "" and not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    setLog(filename, clear)
    setTimeStamp("[%H:%M:%S %d/%m]", True)
    logOpenTime = str(time.ctime(time.time()))
    print >> sys.stderr, "Opening log", filename, "at", logOpenTime
    logOpenMessage = "####### Log opened at " + str(time.ctime(time.time())) + " #######\n"
    writeToLog(logOpenMessage, filename)
    if logCmd:
        writeToLog("Command line: " + " ".join(sys.argv) + "\n", filename)

def closeLog(filename):
    assert isinstance(sys.stdout, StreamModifier)
    removedStdout = sys.stdout.removeLog(filename, "stdout")
    assert isinstance(sys.stderr, StreamModifier)
    removedStderr = sys.stderr.removeLog(filename, "stderr")
    # These are most often the same file, so they (it) must be closed after removed from all streams
    removedStdout.close()
    removedStderr.close()

def writeToScreen(text):
    assert isinstance(sys.stderr, StreamModifier)
    sys.stderr.writeToStream(text)

def writeToLog(text, filename=None):
    assert isinstance(sys.stdout, StreamModifier)
    sys.stdout.writeToLog(text, filename)

def setLog(filename=None, clear=False, encoding="utf-8"):
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
            logfile = codecs.open(filename, "wt", encoding)
        else:
            logfile = codecs.open(filename, "at", encoding)
        sys.stdout.addLog(logfile)
        sys.stderr.addLog(logfile)

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
