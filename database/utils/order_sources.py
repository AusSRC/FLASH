import os
import sys
from glob import glob
import re

def returnBrightestSources(names,number=None):

    namedir = {}

    for name in names:
        source_num = int(re.split('(\d+)',name)[-2])
        if source_num not in namedir.keys():
            namedir[int(source_num)] = [name]
        else:
            namedir[int(source_num)].append(name)

    keys = list(namedir.keys())
    keys.sort()
    sorted_sources = {i: namedir[i] for i in keys}
   
    if number: 
        n = int(number)
    else:
        n = len(sorted_sources)
    bright_sources = []
    for idx,(key,sources) in enumerate(sorted_sources.items()):
        if idx == n: 
            break
        sources.sort()
        for source in sources:
            bright_sources.append(source)
    return bright_sources,idx

##########################################################################################
##########################################################################################

if __name__ == "__main__":

    directory = sys.argv[1]
    try:
        number = sys.argv[2]
    except IndexError:
        number = None
    try:
        plottype = sys.argv[3]
    except IndexError:
        plottype = "opd"

    names = glob(f"{directory}/*{plottype}.png")
    names = [os.path.basename(f) for f in names]
    sources,number = returnBrightestSources(names,number)
    print(f"\nBrightest {number} sources ({len(sources)} components)\n")
    for idx,source in enumerate(sources):
        print("    ",idx+1,source)
