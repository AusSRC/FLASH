#########################################################################################
#
#   Script to identify spectral ascii files that only contain NaN values for noise
#
#   GWHG @ CSIRO Apr 2023
#
#########################################################################################

import os
import os.path
import sys

def usage():
    print("python3 pre_process.py <list of directories of spectral ascii files> <directory to move bad files to>")

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

##########################################################################################
##########################################################################################

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()
        sys.exit()
    dirnames = sys.argv[1:-1]
    bad_files_dir = sys.argv[-1]
    os.system(f"mkdir -p {bad_files_dir}")
    for dirname in dirnames:
        print(f"Processing directory {dirname}")
        files = (file for file in os.listdir(dirname) if os.path.isfile(os.path.join(dirname, file)))
        for name in files:
            flag = flagNoiseInOpd(f"{dirname}/{name}")
            if not flag:
                print(f"{name} : Bad NaN values - moving file")
                os.system(f"mv {dirname}/{name} {bad_files_dir}")
