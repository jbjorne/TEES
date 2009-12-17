def preprocess(filename, steps=[]):
    f = open(filename, "rt")
    lines = f.readlines()
    f.close()
    
    for step in steps:
        lines = step(lines)
        
    f = open(filename, "wt")
    for line in lines:
        f.write(line)
    f.close()

def conditional(lines):
    keepLines = True
    linesToKeep = []
    for line in lines:
        if line.find("IF LOCAL") != -1:
            keepLines = False
        elif line.find("ENDIF") != -1:
            keepLines = True
        else:
            if keepLines:
                linesToKeep.append(line)
    return linesToKeep
        
            
    