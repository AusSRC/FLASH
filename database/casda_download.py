#!/usr/bin/python
# Imports
from astroquery.utils.tap.core import TapPlus
import numpy as np
from astroquery.casda import Casda 
import os
import sys
import glob
import getpass
from argparse import ArgumentParser, RawTextHelpFormatter

UNTAR = False
DATADIR = "/home/ger063/src/flash_data/casda"

# Set up the argument parser
parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument('-e', '--email_address',
        default=None,
        help='Specify email address for login to CASDA (default: %(default)s)')
parser.add_argument('-p', '--password',
        default=None,
        help='Specify the password for login to CASDA (default: %(default)s)')    
parser.add_argument('-s', '--sbid_list',
        default=None,
        help='Specify list of SBIDs to download as a comma-separated list (default: %(default)s)')
parser.add_argument('-c', '--catalogues_only',
        default=False,
        action='store_true',
        help='Specify whether you want to download catalogues only (default: %(default)s)')    
args = parser.parse_args()

# Get list of SBIDs
if args.sbid_list != None:
    sbid_list = args.sbid_list.split(',')
    print('List of SBIDs to download: %s' % sbid_list)
else:
    print('Please include a list of SBIDs to download! Exiting...')
    sys.exit()

# Authentication/setup
if args.email_address != None:
    username = args.email_address
else:
    username = input("Enter your OPAL/CASDA email address: ")
if args.password == None:
    password = getpass.getpass(str("Enter your OPAL/CASDA password: "))
else:
    password = args.password
casda = Casda(username, password)
casdatap = TapPlus(url="https://casda.csiro.au/casda_vo_tools/tap")
print("Logged in!")

# Loop over each SBID
for sbid in sbid_list:

    # Make a folder
    try:
        os.mkdir(f'{DATADIR}/%s' % sbid)
    except:
        pass

    # Start by downloading the catalogues - just the components (not islands)
    print('Querying CASDA to download catalogues...')
    job = casdatap.launch_job_async("SELECT * FROM ivoa.obscore where obs_id = '%s' and obs_publisher_did like 'catalogue%%' and dataproduct_subtype like '%%component'" % sbid)
    r = job.get_results()
    print(f'Staging and downloading the catalogues for {sbid}')
    url_list = casda.stage_data(r)
    filelist = casda.download_files(url_list, savedir=f'{DATADIR}/%s/' % sbid)
    print('... done!')

    #if spectral download specified
    if not args.catalogues_only:
        # Loop over the variable list
        for variable in variable_list:

            # Get the TAP information
            print('Querying CASDA for relevant file...')
            job = casdatap.launch_job_async("SELECT * FROM casda.observation_evaluation_file oef inner join casda.observation o on oef.observation_id = o.id where o.sbid = %s" % sbid)
            r = job.get_results()
            filename =  r[np.char.startswith(r['filename'], variable)]

            #stage and download the data
            print('Staging and downloading the %s data...' % variable)
            url_list = casda.stage_data(filename)
            filelist = casda.download_files(url_list, savedir='%s/' % sbid)
            print('... done!')
        if UNTAR:
            # Untar the data and then delete the tar files
            tarfiles = glob.glob('%s/*.tar' % sbid)
            for tarfile in tarfiles:
                os.system('tar -xvf %s -C %s' % (tarfile,sbid))

            # Removal the tarballs after
            os.system('rm %s/*.tar' % sbid)

print(f"Processed sbids {sbid_list}")

