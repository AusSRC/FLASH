#########################################################################################
#
#       This script will check the files stored in the BAD_ASCII_FILES directory and 
#       create a list of sbids and source names that were tagged 'bad'. This list will be pushed to
#       the Oracle FLASH VM periodically.
#
#      
#       GWHG @ AusSRC 2025
#
#########################################################################################
import os
import os.path
import sys
import json
import glob

def usage():
    print("python3 process_bad_file_dir.py <directory of bad files>")

def getSubDirs(path):
    subdirectories = [entry.name for entry in os.scandir(path) if entry.is_dir()]
    return subdirectories

def readFilesInDir(parent,path):
    files = glob.glob(f"{parent}/{path}/*opd.dat")
    return files

def getSbidsSourcesFromName(pathname):
    name = os.path.basename(pathname)
    bits = name.split('_')
    sbid = bits[0].split('SB')[1]
    source = bits[2]
    return sbid,source

##########################################################################################
##########################################################################################

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit()

    bad_files_dir = sys.argv[1]
    subdirs = getSubDirs(bad_files_dir)
    vals = {}
    for sub in subdirs:
        vals[sub] = {}
        print(f"{sub}:")
        files = readFilesInDir(bad_files_dir,sub)
        for pathname in files:
            sbid,source = getSbidsSourcesFromName(pathname)
            if not sbid in vals[sub].keys():
                vals[sub][sbid] = []
            vals[sub][sbid].append(source)
            #vals.append(f"{sbid}: {source}")
        # sort dict
        vals[sub] = dict(sorted(vals[sub].items()))
        for key in vals[sub].items():
            print(f"{key}")

    # Write to file
    with open("bad_files.json", "w") as file:
        json.dump(vals, file, indent=4)

        
