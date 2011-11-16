f = open("/home/jari/data/BioNLP11SharedTask/resources/lpsn-alintro.html", "rt")
outFile = open("/home/jari/data/BioNLP11SharedTask/resources/lpsn-bacteria-names.txt", "wt")

count = 0
for line in f:
    count += 1
    if count < 178:
        continue
    if "#FF0000" in line:
        splits = line.strip().split("<font color=\"#FF0000\"><i><b>")
        #print splits
        tokens = []
        for split in splits:
            if "</b></i>" in split:
                split2 = split.split("</b></i>")[0]
                assert split2.strip() == split2, (split2, line)
                if split2[0] != "<" and split2[-1] != ">":
                    tokens.append(split2)
        tokenString = " ".join(tokens).strip()
        if tokenString != "":
            print tokenString
            outFile.write(tokenString + "\n")

f.close()
outFile.close()