import os
import os.path
import sys

def flagNoiseInOpd(name):
    data = []
    with open(name,"r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            data = line.split()[-1].lower()
            if data != "nan":
                return True
    return False

if __name__ == "__main__":
    dir_name = sys.argv[1]
    with os.scandir(dir_name) as listings:
        for listing in listings:
            flag = flagNoiseInOpd(f"{dir_name}/{listing.name}")
            if not flag:
                print(listing.name,f" : {flag}")
