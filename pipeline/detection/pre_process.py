#########################################################################################
#
#   Script to identify spectral ascii files that contain a large % of NaN values for flux or noise
#
#   GWHG @ CSIRO Apr 2023
#   Revised: Aug 2025
#
#########################################################################################

import os
import os.path
import sys
import fnmatch
import subprocess

CUTOFF = 0.4 # files with above this fraction of Nan values will be deemed 'bad'

def usage():
    print("python3 pre_process.py <directory to move bad files to> <directory of spectral ascii files> <optional dir of spectral plot files>")

def findpercentNan(fname):
    ''' Check how many lines in file contain NaN values'''

    line_count = 0
    fluxes = 0.
    noises = 0.

    with open(fname,"r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            freq,flux,noise = line.lower().split()
            if flux == "nan":
                fluxes += 1.0
            if noise == "nan":
                noises += 1.0
            line_count += 1
    fluxes = float(fluxes/line_count)
    noises = float(noises/line_count)

    return fluxes,noises
        

def flagNoiseInOpd(name):
    data = []
    # Ensure every line has 3 columns
    output = subprocess.check_output("awk 'NF!=3{print $0}' %s" % name, shell=True)
    if output != b'':
        return False, "malformed"

    flux,noise = findpercentNan(name)
    if flux > CUTOFF:
        return False, "flux"
    elif noise > CUTOFF:
        return False, "noise"

    return True, "OK"

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
    fluxes = 0
    noises = 0
    malformed = 0
    bad_files = []
    bad_files_dir = sys.argv[1]
    ascii_dirname = sys.argv[2]
    if len(sys.argv) == 4: 
        do_plot_files = True
        plot_dirname = sys.argv[3]
    os.system(f"mkdir -p {bad_files_dir}/malformed")
    os.system(f"mkdir -p {bad_files_dir}/flux")
    os.system(f"mkdir -p {bad_files_dir}/noise")
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
            elif status == "flux":
                print(f"{name} : flux values Nan > 50% = moving file")
                os.system(f"mv {ascii_dirname}/{name} {bad_files_dir}/flux/")
                fluxes += 1
                if do_plot_files:
                    movePlotFile(plot_dirname,f"{bad_files_dir}/flux/",name)
            elif status == "noise":
                print(f"{name} : noise values Nan > 50% = moving file")
                os.system(f"mv {ascii_dirname}/{name} {bad_files_dir}/noise/")
                noises += 1
                if do_plot_files:
                    movePlotFile(plot_dirname,f"{bad_files_dir}/noise/",name)
            if name.endswith(".dat"):
                bad_files.append(name.replace(".dat",""))
    print()
    print(f"From total {tot_files} files, {fluxes} sources found with >{CUTOFF*100}% NaN flux values")
    print(f"From total {tot_files} files, {noises} sources found with >{CUTOFF*100}% NaN noise values")
    print(f"From total {tot_files} files, {malformed} sources found with malformed values")
