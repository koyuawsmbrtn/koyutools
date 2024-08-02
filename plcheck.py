#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

fls = os.listdir()

for fl in fls:
    if ".m3u" in fl:
        tmp = ""
        with open(fl, "r", encoding="utf8") as f:
            x = f.readlines()
            for line in x:
                if not "/Music/" in line:
                    tmp += "/Music/"+line
                else:
                    tmp += line
        with open(fl, "w", encoding="utf8") as f:
            f.write(tmp)
