import os

fls = os.listdir()

for fl in fls:
    if ".m3u" in fl:
        tmp = ""
        with open(fl, "r") as f:
            x = f.readlines()
            for line in x:
                if not "/Music/" in line:
                    tmp += "/Music/"+line
                else:
                    tmp += line
        with open(fl, "w") as f:
            f.write(tmp)
