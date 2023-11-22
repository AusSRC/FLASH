#!/usr/bin/python
# Imports
from astroquery.utils.tap.core import TapPlus
import numpy as np
from astroquery.casda import Casda 
import os
import sys
from glob import glob
import getpass
from argparse import ArgumentParser, RawTextHelpFormatter

UNTAR = True
DATADIR = "/scratch/ja3/ger063/data/casda" # The expected structure is subdirs under here for sbids
CATDIR = "/scratch/ja3/ger063/data/casda/catalogues" # directory that holds catalogues
################################################################################################################

def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-e', '--email_address',
            default="gordon.german@csiro.au",
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
    return args
################################################################################################################

def get_sbids(args):
    # Get list of SBIDs
    if args.sbid_list != None:
        sbid_list = args.sbid_list.split(',')
        print('List of SBIDs to download: %s' % sbid_list)
    else:
        print('Please include a list of SBIDs to download! Exiting...')
        sys.exit()
    return sbid_list
################################################################################################################

def authenticate(args):
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
    # New authentication for astroquery 0.4.7:
    #casda = Casda()
    #casda.login(username=username)
    casdatap = TapPlus(url="https://casda.csiro.au/casda_vo_tools/tap")
    print("Logged in!")
    return casda,casdatap
################################################################################################################

def process_sbid_list(sbid_list,args,casda,casdatap,datadir=DATADIR,catdir=CATDIR,exists=False):


    # Loop over each SBID
    cwd = os.getcwd()
    # Make catalogue and SLURM log directories
    os.makedirs(f'{catdir}',exist_ok=True)
    os.makedirs(f'{datadir}/logs',exist_ok=True)
    for sbid in sbid_list:
        if exists and glob(f"{datadir}/{sbid}/*.xml") != []:
            continue

        # Make a folder
        try:
            os.mkdir(f'{datadir}/%s' % sbid)
        except:
            print(f"Error trying to make directory {datadir}/{sbid}")

        # Start by downloading the catalogues - just the components (not islands)
        print('Querying CASDA to download catalogues...')
        job = casdatap.launch_job_async("SELECT * FROM ivoa.obscore where obs_id = '%s' and obs_publisher_did like 'catalogue%%' and dataproduct_subtype like '%%component'" % sbid)
        r = job.get_results()
        print(f'Staging and downloading the catalogues for {sbid}')
        url_list = casda.stage_data(r)
        #filelist = casda.download_files(url_list, savedir=f'{DATADIR}/%s/' % sbid)
        filelist = casda.download_files(url_list, savedir=f'{catdir}')
        print('... done!')
        #if spectral download specified
        if not args.catalogues_only:
            # Loop over the variable list
            for variable in ['SourceSpectra','NoiseSpectra']:

                # Get the TAP information
                print('Querying CASDA for relevant SourceSpectra file...')
                job = casdatap.launch_job_async("SELECT * FROM casda.observation_evaluation_file oef inner join casda.observation o on oef.observation_id = o.id where o.sbid = %s" % sbid)
                r = job.get_results()
                filename =  r[np.char.startswith(r['filename'], variable)]

                #stage and download the data
                print('Staging and downloading the %s data...' % variable)
                url_list = casda.stage_data(filename)
                filelist = casda.download_files(url_list, savedir=f'{datadir}/%s/' % sbid)
                print('... done!')
            if UNTAR:
                # Untar the data and then delete the tar files
                tarfiles = glob(f'{datadir}/%s/*.tar' % sbid)
                os.chdir(f'{datadir}/{sbid}')
                for tarfile in tarfiles:
                    #os.system('tar -xvf %s -C %s' % (tarfile,sbid))
                    os.system('tar -xvf %s' % tarfile)
    os.chdir(cwd)


################################################################################################################
################################################################################################################

if __name__ == "__main__":

    args = set_parser()
    sbid_list = get_sbids(args)
    casda,casdatap = authenticate(args)
    process_sbid_list(sbid_list,args,casda,casdatap)
    print(f"Processed sbids {sbid_list}")
