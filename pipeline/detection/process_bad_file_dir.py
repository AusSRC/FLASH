#########################################################################################
#   Use this script to create a json file of the listed 'bad_ascii_files' kept in the bad_ascii_file directory:
#           python3 process_bad_file_dir.py <bad_ascii directory>
#
#    The created json file will list files that meet the criteria of 'bad' - one of:
#           1. More than 40% of flux values are NaN
#           2. More than 40% of noise values are NaN
#           3. Malformed lines of data
#
#   Optionally, you can merge an older json file with the new data:
#           python3 process_bad_file_dir.py <bad_ascii directory> <previous bad_ascii json file>
#
#   The json file should be pushed to the Oracle FLASH VM periodically.
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
    print("\nUse this script to create a json file of the listed 'bad_ascii_files' kept in the bad_ascii_file directory:")
    print("        python3 process_bad_file_dir.py <bad_ascii directory>")
    print("\n This file will list files that meet the criteria of 'bad' - one of:")
    print("        1. More than 40% of flux values are NaN")
    print("        2. More than 40% of noise values are NaN")
    print("        3. Malformed lines of data")
    print("\nOptionally, you can merge an older json file with the new data:")
    print("        python3 process_bad_file_dir.py <bad_ascii directory> <previous bad_ascii json file>")

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

def readOldJson(fname):
    with open(fname, 'r') as file:
        data = json.load(file)

    return data

def _appendData(dat,old_data,new_data):
    for line in new_data[dat]:
        # Check if sbid in old data
        if line in old_data[dat]:
            for val in old_data[dat][line]:
                if val not in new_data[dat][line]:
                    new_data[dat][line].append(val)
    return new_data

def appendToJson(old_data,new_data):

    new_vals = {}
    # Flux data first
    new_data = _appendData("flux",old_data,new_data)
    # malformed data
    new_data = _appendData("malformed",old_data,new_data)
    # noise data
    new_data = _appendData("noise",old_data,new_data)

    return new_data

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
    
    print("Got new data")

    # read the old bad_ascii file, if provided:
    if len(sys.argv) > 2:
        old_data = readOldJson(sys.argv[2])
        # Merge the new and old data
        print("Got old data: merging")
        vals = appendToJson(old_data,vals)
    
    # Write to file
    with open("bad_files.json", "w") as file:
        json.dump(vals, file, indent=4)

        
