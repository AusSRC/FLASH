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
    print("python3 pre_process.py <directory of spectral ascii files> <dir of spectral plot files> <directory to move bad files to>")

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

def movePlotFile(source_dir,dest_dir,ascii_name):
    # Find plot file associated with the given ascii file
    plotname = ascii_name.replace(".dat",".png")
    plotfile = os.path.join(source_dir,plotname)
    if os.path.isfile(plotfile):
        os.system(f"mv {plotfile} {dest_dir}")
    

##########################################################################################
##########################################################################################

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()
        sys.exit()
    count = 0
    bad_files = []
    ascii_dirname = sys.argv[1]
    plot_dirname = sys.argv[2]
    bad_files_dir = sys.argv[-1]
    os.system(f"mkdir -p {bad_files_dir}")
    files = (file for file in os.listdir(ascii_dirname) if os.path.isfile(os.path.join(ascii_dirname, file)))
    for name in files:
        flag = flagNoiseInOpd(f"{ascii_dirname}/{name}")
        if not flag:
            count += 1
            print(f"{name} : All NaN values - moving file")
            os.system(f"mv {ascii_dirname}/{name} {bad_files_dir}")
            movePlotFile(plot_dirname,bad_files_dir,name)
            if name.endswith("opd.dat"):
                bad_files.append(name.replace("_opd.dat",""))
    print(bad_files)
    print(f"{count} sources found with all NaN values. Associated plot and ascii files have been moved to {bad_files_dir}")
