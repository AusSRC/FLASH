#!/usr/bin/python
################################################################################################################
#
#       NOTE: FLASH project code is AS209
#       NOTE: casda ivoa.obscore defines 'obs_collection' as 'FLASH' for survey, and 'ASKAP Pilot Survey for FLASH' for pilot
#       NOTE: FLASH Pilot 1 dates are: before 11/2021
#       NOTE: FLASH Pilot 2 dates are: 11/2021 ~ 08/2022
#       NOTE: FLASH Survey dates are: 11/2022 on
#
################################################################################################################
# Imports
import astroquery as aq
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
    if args.password == None and aq.__version__[:5] < "0.4.7":
        password = getpass.getpass(str("Enter your OPAL/CASDA password: "))
    else:
        password = args.password
    if aq.__version__[:5] < "0.4.7":
        casda = Casda(username, password)
    else:
    # New authentication for astroquery 0.4.7:
        casda = Casda()
        casda.login(username=username,password = password)
    casdatap = TapPlus(url="https://casda.csiro.au/casda_vo_tools/tap")
    print("Logged in!")
    return casda,casdatap

################################################################################################################

def process_sbid_list(sbid_list,args,casda,casdatap,datadir=DATADIR,catdir=CATDIR,exists=False,get_rejected=False):


    # Loop over each SBID
    cwd = os.getcwd()
    # Make catalogue and SLURM log directories
    os.makedirs(f'{catdir}',exist_ok=True)
    os.makedirs(f'{datadir}/logs',exist_ok=True)
    bad_sbids = []
    for sbid in sbid_list:
        #try:
        if exists and glob(f"{datadir}/{sbid}/*.xml") != []:
            continue

        # Make a folder
        try:
            os.makedirs(f'{datadir}/{sbid}',exist_ok=True)
        except:
            print(f"Error trying to make directory {datadir}/{sbid}")
        # Next is downloading the catalogues - just the components (not islands)
        print(f'Querying CASDA to download {sbid} catalogues...')
        job = casdatap.launch_job_async("SELECT * FROM ivoa.obscore where obs_id = 'ASKAP-%s' and obs_publisher_did like 'catalogue%%' and dataproduct_subtype like '%%component'" % sbid)
        r = job.get_results()
        # checking the quality level of the observation - if it's been rejected, skip
        quality = str(r['quality_level']).split()[-1]
        print(f"Quality = {quality}",end="")
        if not get_rejected and quality == "REJECTED":
            print("  skipping ...")
            bad_sbids.append(sbid)
            continue
        else:
            # Log the quality level to file for later use
            with open(f"{datadir}/{sbid}/data_quality.txt","w") as fh:
                fh.write("%s" % quality)
            print()
            print(f'Staging and downloading the catalogues for {sbid}')
        try:
            url_list = casda.stage_data(r)
            filelist = casda.download_files(url_list, savedir=f'{catdir}')
            print(f'{sbid} from list {sbid_list}... done!')
        except Exception as e:
            print(f"Error in staging data for sbid {sbid}: {e}")
            bad_sbids.append(sbid)
            continue

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
                try:
                    url_list = casda.stage_data(filename)
                    filelist = casda.download_files(url_list, savedir=f'{datadir}/%s/' % sbid)
                    print('... done!')
                except Exception as e:
                    print(f"Error downloading {variable} in {sbid}: {e}")
                    bad_sbids.append(sbid)
                    continue
            if UNTAR:
                # Untar the data and then delete the tar files
                tarfiles = glob(f'{datadir}/%s/*.tar' % sbid)
                os.chdir(f'{datadir}/{sbid}')
                for tarfile in tarfiles:
                    os.system('tar -xvf %s' % tarfile)
            print(f"Untarred all files for {sbid}")
    os.chdir(cwd)
    return bad_sbids

################################################################################################################

def get_sbids_in_casda(args,casda,casdatap,get_rejected=False):
    print('Querying CASDA for FLASH sbids')
    quality_dict = {}
    if not get_rejected:
        job = casdatap.launch_job_async("SELECT obs_id,quality_level FROM ivoa.obscore where obs_collection = 'FLASH' and obs_publisher_did like 'catalogue%%' and dataproduct_subtype like '%%component' and quality_level not like 'REJECTED%%'")
    else:
        job = casdatap.launch_job_async("SELECT obs_id,quality_level FROM ivoa.obscore where obs_collection = 'FLASH' and obs_publisher_did like 'catalogue%%' and dataproduct_subtype like '%%component'")
        
    r = job.get_results()
    sbids = list(r['obs_id'][0:])
    quality = list(r['quality_level'][0:])
    for i,sbid in enumerate(sbids):
        sbid = sbid.split("-")[1]
        sbids[i] = sbid
        quality_dict[sbid] = quality[i]
    sbids.sort(reverse=True)
    print(f"{len(sbids)} sbids valid at CASDA: {sbids}")
    return sbids,quality_dict

################################################################################################################

def get_rejects_from_casda(args,casda=None,casdatap=None):
    print("Querying CASDA for rejected sbids")
    if not casda:
        casda,casdatap = authenticate(args)
    rejected_sbids = []
    job = casdatap.launch_job_async("SELECT obs_id,quality_level FROM ivoa.obscore where obs_collection = 'FLASH' and obs_publisher_did like 'catalogue%%' and dataproduct_subtype like '%%component' and quality_level like 'REJECTED%%'")
    r = job.get_results()
    for res in r:
        rejected_sbids.append(res['obs_id'])
    return rejected_sbids


################################################################################################################
################################################################################################################

if __name__ == "__main__":

    args = set_parser()
    sbid_list = get_sbids(args)
    casda,casdatap = authenticate(args)
    process_sbid_list(sbid_list,args,casda,casdatap)
    print(f"Processed sbids {sbid_list}")
