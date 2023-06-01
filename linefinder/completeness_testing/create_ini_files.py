import os
import sys

# Use as: python3 create_ini_files.py <base linefinder.ini> <directory with all spectra subdirs>

seed_file = sys.argv[1]
dirs = sorted(next(os.walk(sys.argv[2]))[1])

with open(seed_file,'r') as f:
    seed_ini = f.readlines()

idx = 1
for spect_dir in dirs:

    os.system(f"mkdir -p {sys.argv[2]}/{spect_dir}/chains")
    os.system(f"mkdir -p {sys.argv[2]}/config")
    ini = open(f"{sys.argv[2]}/config/linefinder_{idx}.ini",'w')
    for line in seed_ini:
        if line.startswith("out_path"):
            line = f"out_path : {sys.argv[2]}/{spect_dir}/chains\n"
        elif line.startswith("data_path"):
            line = f"data_path : {sys.argv[2]}/{spect_dir}\n"
        ini.write(line)
    ini.close()
    idx += 1

