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
import fnmatch
import subprocess

def usage():
    print("python3 pre_process.py <directory to move bad files to> <directory of spectral ascii files> <optional dir of spectral plot files>")

def flagNoiseInOpd(name):
    data = []
    # Ensure every line has 3 columns
    output = subprocess.check_output("awk 'NF!=3{print $0}' %s" % name, shell=True)
    if output != b'':
        return False, "malformed"
    # Ensure file has at least ONE valid line
    with open(name,"r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            data = line.split()[-1].lower()
            # See if there are any valid numerics
            if data != "nan":
                return True, "OK"
    return False, "NaN"

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

    do_plot_files = False
    count = 0
    nan = 0
    malformed = 0
    bad_files = []
    bad_files_dir = sys.argv[1]
    ascii_dirname = sys.argv[2]
    if len(sys.argv) == 4: 
        do_plot_files = True
        plot_dirname = sys.argv[3]
    os.system(f"mkdir -p {bad_files_dir}/malformed")
    os.system(f"mkdir -p {bad_files_dir}/nan")
    files = (file for file in os.listdir(ascii_dirname) if os.path.isfile(os.path.join(ascii_dirname, file)))
    tot_files = (len(fnmatch.filter(os.listdir(ascii_dirname), '*.dat')))
    for name in files:
        if not name.endswith(".dat"):
            continue
        flag,status = flagNoiseInOpd(f"{ascii_dirname}/{name}")
        if not flag:
            count += 1
            if status == "malformed":
                print(f"{name} : Missing values on line - moving file")
                os.system(f"mv {ascii_dirname}/{name} {bad_files_dir}/malformed/")
                malformed += 1
                if do_plot_files:
                    movePlotFile(plot_dirname,f"{bad_files_dir}/malformed/",name)
            else:
                print(f"{name} : All NaN values - moving file")
                os.system(f"mv {ascii_dirname}/{name} {bad_files_dir}/nan/")
                nan += 1
                if do_plot_files:
                    movePlotFile(plot_dirname,f"{bad_files_dir}/nan/",name)
            if name.endswith(".dat"):
                bad_files.append(name.replace(".dat",""))
    print()
    print(bad_files)
    print(f"From total {tot_files} files, {nan} sources found with all NaN values")
    print(f"From total {tot_files} files, {malformed} sources found with malformed values")
