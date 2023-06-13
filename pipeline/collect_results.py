###########################################################################################
# collect_results.py
#
# GWHG @ CSIRO June 2023
#
# This script will search all directories below a parent directory for files that match 'results*.dat',
# and concatenate them all into one summary file.
#
# It will NOT include any matching files found:
#   1. in the top-layer parent directory,
#   2. in the summary directory (where the summary file will be saved),
#   3, in any other directories declared in the calling statement.
#
# The resultant summary file will have the entries from each 'found' input file organised by component 
# number. There will be an empty line between entries from each input file.
#
#   Usage:
#
#   python3 collect_results.py <parent_dir> <summary_dir> <other dirs to ignore> ...

###########################################################################################

import os
import sys
from glob import glob
from datetime import datetime

def find_results_files(path,string="results*.dat"):

    files = glob(f"{path}/**/{string}",recursive=True)
    return files

def ignore_previous_results(files,ignore_dirs):

# if there are results files in the ignore directories,
# ignore them.
    valid_files = []
    for name in files:
        path = os.path.dirname(name)
        if path in ignore_dirs:
            continue
        else:
            valid_files.append(name)
    return valid_files

def write_header(summary_dir):
    dt_string = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    result_file = f"{summary_dir}/results_{dt_string}.dat"
    
    f = open(result_file,"w")
    header = "#Name ModeNum x0_1_maxl dx_1_maxl y0_1_maxl abs_peakz_median abs_peakz_siglo abs_peakz_sighi abs_peakopd_median abs_peakopd_siglo abs_peakopd_sighi abs_intopd_median(km/s) abs_intopd_siglo(km/s) abs_intopd_sighi(km/s) abs_width_median(km/s) abs_width_siglo(km/s) abs_width_sighi(km/s) ln(B)_mean ln(B)_sigma chisq_mean chisq_sigma\n"
    f.write(header)
    f.close()
    return result_file

def order_names(names):
    namedir = {}

    for name in names:
        source_num = re.split('(\d+)',name.split()[0])[-2]
        if source_num not in namedir.keys():
            namedir[source_num] = [name]
        else:
            namedir[source_num].append(name)

    keys = list(namedir.keys())
    keys.sort()
    sorted_sources = {i: namedir[i] for i in keys}
    
    bright_sources = []
    for idx,(key,sources) in enumerate(sorted_sources.items()):
        for source in sources:
            bright_sources.append(source)
    return bright_sources

def process_files(results,files):
    r = open(results,"a")
    lines = []
    for name in files:
        f = open(name,"r")
        print(name)
        file_lines = f.readlines()[1:]
        file_lines = order_names(file_lines)
        lines = lines + file_lines + ["\n"]
        f.close()
    r.write("".join(map(str,lines)))
    r.close()
    print(f"Finished writing to {results}")
        
    

##########################################################################################
##########################################################################################

if __name__ == "__main__":

    parent_dir = sys.argv[1]
    summary_dir = sys.argv[2]
    num_dirs_to_ignore = len(sys.argv)
    ignore_dirs = sys.argv[1:num_dirs_to_ignore]
    res_files = find_results_files(parent_dir)
    valid_files = ignore_previous_results(res_files,ignore_dirs)
    results = write_header(summary_dir)
    process_files(results,valid_files)
    
    




