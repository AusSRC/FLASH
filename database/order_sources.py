import os
import sys
from glob import glob
import re

def returnBrightestSources(names,number,plottype="opd"):

    namedir = {}

    for name in names:
        source_num = re.split('(\d+)',name)[-2]
        if source_num not in namedir.keys():
            namedir[source_num] = [name]
        else:
            namedir[source_num].append(name)

    keys = list(namedir.keys())
    keys.sort()
    sorted_sources = {i: namedir[i] for i in keys}
    
    n = int(number)
    bright_sources = []
    for idx,(key,sources) in enumerate(sorted_sources.items()):
        if idx == n: 
            break
        for source in sources:
            bright_sources.append(source)
    return bright_sources

##########################################################################################
##########################################################################################

if __name__ == "__main__":

    directory = sys.argv[1]
    number = sys.argv[2]
    try:
        plottype = sys.argv[3]
    except IndexError:
        plottype = "opd"

    names = glob(f"{directory}/*{plottype}.png")
    names = [os.path.basename(f) for f in names]

    sources = returnBrightestSources(names,number,plottype=plottype)
    print(f"\nBrightest {number} sources ({len(sources)} components)\n")
    print(sources)
