#!/usr/bin/python
################################################################################################################
#
#       NOTE: FLASH project code is AS209
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
        casda.login(username=username)
    casdatap = TapPlus(url="https://casda.csiro.au/casda_vo_tools/tap")
    print("Logged in!")
    return casda,casdatap

################################################################################################################
def get_sbids_in_casda(args,casda,casdatap):
    print('Querying CASDA for FLASH sbids')
    job = casdatap.launch_job_async("SELECT sbid FROM casda.observation_evaluation_file where project_code = 'AS209' order by sbid desc;")
    r = job.get_results()
    sbids = r['sbid'][0:-1]
    return sbids

################################################################################################################

if __name__ == "__main__":

    args = set_parser()
    casda,casdatap = authenticate(args)
    casda_sbids = get_sbids_in_casda(args,casda,casdatap)




