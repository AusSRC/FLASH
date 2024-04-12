import os
import sys
import logging
import time
import datetime as dt
import os.path
import psycopg2
import xmltodict
from glob import glob

from casda_download import *


##################################### db_utils  ################################################################
#
#       This script deletes data held in the FLASH db at 146.118.64.208
#       GWHG @ CSIRO, July 2023
#
#       version 1.02 02/10/2023
#
#       Edit USER SECTION below to define the type of operation

############################################### USER SECTION ###################################################
# If an attribute doesn't apply, set it to ""

# Note that these are all now set via cmd line key arguments - see set_parser() below.
RUN_TYPE = ""
DOWNLOAD_CAT = True # If the catalogues are not already downloaded, set this to True
ADD_CAT = True # Don't just download the catalogues - add them to the database too.
SBIDDIR = "/scratch/ja3/ger063/data/casda"
DATADIR = SBIDDIR
SBIDS = []
VERSIONS = [] # This list should correspond to the above sbids list = set to empty for just the latest version of each sbid.
CATDIR = SBIDDIR + "/catalogues"
UNTAR = False
DELETE_CATS = False # save space by deleting catalogues after processing
ONLY_CATS = True # Only download catalogues - not spectral and noise data
PASSWD = ""


####################################################################################################################
########################## DO NOT EDIT FURTHER #####################################################################
####################################################################################################################

def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-m', '--mode',
            default="CATALOGUE",
            help='Specify run mode: DELETESBIDS, DELETEDETECTION, CHECK_SBIDS, CHECK_LOCAL_SBIDS (default: %(default)s)')
    parser.add_argument('-s', '--sbid_list',
            default=None,
            help='Specify the sbid list eg 11346,11348 (default: %(default)s)')    
    parser.add_argument('-d', '--sbid_dir',
            default="/scratch/ja3/ger063/data/casda",
            help='Specify local directory to use (default: %(default)s)')    
    parser.add_argument('-e', '--email_address',
            default=None,
            help='Specify email address for login to CASDA (default: %(default)s)')
    parser.add_argument('-p', '--password',
            default=None,
            help='Specify the password for login to CASDA (default: %(default)s)')    
    parser.add_argument('-pw', '--flashpw',
            default=None,
            help='Specify the password for login to FLASHDB (default: %(default)s)')    
    args = parser.parse_args()
    return args

def set_mode_and_values(args):
    global RUN_TYPE, SBIDDIR, DATADIR, SBIDS, VERSIONS, ONLY_CATS, ADD_CAT, PASSWD

    RUN_TYPE = args.mode.strip().upper()
    SBIDDIR = args.sbid_dir.strip()
    DATADIR = SBIDDIR
    if args.sbid_list:
        sbids = args.sbid_list.split(',')
        for sbid in sbids:
            if ":" in sbid:
                SBIDS.append(sbid.split(":")[0])
                VERSIONS.append(sbid.split(":")[1])
            else:
                SBIDS.append(sbid)
                VERSIONS.append(None)
    PASSWD = args.flashpw



def connect(db="flashdb",user="flash",host="146.118.64.208",password=None):

    if not password:
        password = PASSWD
    conn = psycopg2.connect(
        database = db,
        user = user,
        password = password,
        host = host
    )
    #print(conn.get_dsn_parameters(),"\n")
    return conn

def get_cursor(conn):

    cursor = conn.cursor()
    return cursor

###############################################

def get_max_sbid_version(cur,sbid_num,version=None):

    # If version=None, returns the sbid_id:version for the latest version number of the sbid_num in the SBID table
    # Otherwise returns the sbid_id:version for the sbid_num and version combination provided
    # If the sbid_num doesn't exist, returns None:0

    if version:
        query = "select id from sbid where sbid_num = %s and version = %s;"
        cur.execute(query,(sbid_num,version))
        try:
            sbid_id = int(cur.fetchall()[0][0])
        except IndexError:
            # sbid for this version doesn't exist
            sbid_id = None
    else:
        query = "select id,version from sbid where sbid_num = %s and version = (select max(version) from sbid where sbid_num = %s);"
        cur.execute(query,(sbid_num,sbid_num))
        try:
            sbid_id,version = cur.fetchall()[0]
        except IndexError:
            # sbid doesn't exist
            sbid_id = None
            version = 0
    return sbid_id,version

###############################################

def check_sbids_in_db(conn,sbids=SBIDS,mode="verbose"):

    # Check if the sbids listed in sbids are in the db

    cur = get_cursor(conn)
    removed_sbids = []
    for i,sbid in enumerate(sbids):
        sbid_id,ver = get_max_sbid_version(cur,sbid)
        if mode == "verbose":
            print(f"{i}: {sbid}: id = {sbid_id}, version = {ver}")
        if not sbid_id:
            removed_sbids.append(sbid)
    sbids = list(set(sbids) - set(removed_sbids))
    if mode == "verbose":
        print(f"Missing sbids in db {removed_sbids}")
    return cur,sbids

###############################################

def check_local_processed_sbids(directory):

    # Check if local sbid directories contain any spectral ascii files, which is indicative 
    # of a spectral run being done over those sbids.
    
    print(f"In {directory}, processed sbids are:")
    subdirs = glob(f"{directory}/*/")
    sbids = []
    for name in subdirs:
        subname = name.split("/")[-2]
        try:
            n = int(subname)
            sbids.append(n)
        except ValueError:
            pass
    sbids.sort()
    for sbid in sbids:
        ascii_files = glob(f"{directory}/{sbid}/spectra_ascii/*.dat")
        if len(ascii_files) > 0:
            print(f"{sbid},",end="")

##########################################################################################################
###################################### DELETING RUNS #####################################################

def delete_sbids(conn,sbids,versions=None):

    cur = get_cursor(conn)
    if not versions:
        versions = [None]*len(sbids)

    for sbid,version in zip (sbids,versions):
        # Get rid of any associated files on the compute resource
        os.system(f"rm -Rf {SBIDDIR}/{sbid}")
        os.system(f"rm -f {CATDIR}/*{sbid}*.xml*") 
        if not sbid:
            continue
        print(f"For {sbid}:{1 if version == None else version} :")
        print("\tFinding ascii LOB")
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Delete associated large object of ascii files
        oid_query = "select ascii_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()
        oid_delete = "SELECT lo_unlink(%s);"
        try:
            for i in lon:
                cur.execute(oid_delete,(i,))
            print("\tDeleted ascii LOB")
        except TypeError:
            pass
            
        # This sbid will possibly be referenced in the detect_run table. Remove the reference.
        cur.execute(f"SELECT detect_runid from sbid where id = {sbid_id};")
        runid = cur.fetchall()[0][0]

        sbid_query = "SELECT id,SBIDS from detect_run where %s = ANY (SBIDS);"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            cur = remove_sbids_from_detection(conn,[sbid],[version],runid)
            print("\tRemoved reference in detect table")
        except IndexError:
            print(f"\tNo detection run found for sbid {sbid}:{version}")

        # It will DEFINITELY be referenced in the spect_run table - remove
        sbid_query = "SELECT id from spect_run where %s = ANY (SBIDS);"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            remove_sbid_from_spectral(cur,sbid,runid)
            print("\tRemoved reference in spectral_run table")
        except IndexError:
            # This should NEVER happen
            print(f"\tNo spectral run found for sbid {sbid}:{version}")

        # Now remove the sbid from the SBID table (will also remove associated components) and any large objects
        print("\tDeleting components ...")
        sbid_delete = "DELETE from SBID where id = %s;"
        cur.execute(sbid_delete,(sbid_id,))
        print(f"\t{sbid}:{version} deleted!")

    return cur
     
def remove_sbids_from_detection(conn,selected_sbids,versions=None,runid=None):

    cur = get_cursor(conn)
    if not versions:
        versions = [None]*len(selected_sbids)

    for sbid,version in zip(selected_sbids,versions):
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Delete associated large object of detection outputs
        oid_query = "select detect_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()
        oid_delete = "SELECT lo_unlink(%s);"
        for i in lon:
            cur.execute(oid_delete,(i,))
        
        # Remove detection flag and oid from the sbid
        sbid_update = "UPDATE sbid SET detectionF = %s, detect_tar = NULL, detect_runid = NULL where id = %s;"
        cur.execute(sbid_update,(False,sbid_id))

        # Get detection that lists this sbid
        if not runid:
            # Need to get detection id 
            sbid_query = "SELECT detect_runid from sbid where id = %s;"
            cur.execute(sbid_query,(sbid_id,))
            runid = cur.fetchone()[0]
        
        # Remove reference in detect_run
        sbid_query = "SELECT SBIDS from detect_run where id = %s;"
        cur.execute(sbid_query,(runid,))
        sbids = None
        try:
            sbids = cur.fetchone()[0]
            sbids.remove(int(sbid))
        except TypeError or IndexError:
            pass 
        # Check if sbids list now empty, in which case delete whole detection
        if not sbids:
            detect_stat = "DELETE from detect_run where id = %s;"
            cur.execute(detect_stat,(runid,))
            print(f"    -- Deleted detection {runid}")
        else:
        # Update detection by removing sbid from row
            detect_stat = "UPDATE detect_run SET SBIDS = %s where id = %s;"
            cur.execute(detect_stat,(sbids,runid))
            print(f"    -- Updated detection {runid}")
    return cur

def remove_sbid_from_spectral(cur,sbid,runid):
    
    # Get list of sbids for detection
    sbid_query = "SELECT SBIDS from spect_run where id = %s;"
    cur.execute(sbid_query,(runid,))
    sbids = cur.fetchone()[0]
    if int(sbid) in sbids:
        sbids.remove(int(sbid))
    # Check if sbids list now empty, in which case delete whole detection
    if not sbids:
        detect_stat = "DELETE from spect_run where id = %s;"
        cur.execute(detect_stat,(runid,))
        print(f"    -- Deleted spectral run {runid}")
    else:
    # Update detection by removing sbid from row
        detect_stat = "UPDATE spect_run SET SBIDS = %s where id = %s;"
        cur.execute(detect_stat,(sbids,runid))
        print(f"    -- Updated spect_run {runid}")

def delete_detection(conn,runid):

    cur = get_cursor(conn)

    # Get the sbids that this detection run processed
    sbid_query = "select SBIDS from detect_run where id = %s;"
    cur.execute(sbid_query,(runid,))
    sbids = cur.fetchone()[0]

    # Delete from the detect_run table
    delete_stat = "DELETE from detect_run where id = %s;"
    cur.execute(delete_stat,(runid,))

    # Process SBIDs
    for sbid in sbids:
        # Get the large object number for the detection tarball
        oid_query = "select detect_tar from sbid where sbid_num = %s and detect_runid = %s;"
        cur.execute(oid_query,(sbid,runid))
        lon = cur.fetchone()[0]
        # Delete it from large object table
        oid_delete = "SELECT lo_unlink(%s);"
        cur.execute(oid_delete,(lon,))
        # Reset runid, detection flag and tarball in table SBID
        sbid_reset = "UPDATE SBID SET detect_runid=NULL,detectionF = %s, detect_tar = NULL where sbid_num = %s and detect_runid = %s;"
        cur.execute(sbid_reset,(False,sbid,runid))
    return cur


############################################################################################################################################
############################################################################################################################################

if __name__ == "__main__":

    starttime = time.time()

    args = set_parser()
    set_mode_and_values(args)
    conn = connect()

    # Add run
    if RUN_TYPE == "REJECTED":
        rejected_sbids = get_rejects_from_casda(args)
        rejected_sbids.sort(reverse=True)
        print("Rejected sbids:")
        print(rejected_sbids)
        #cur,rejected_sbids = check_sbids_in_db(conn,rejected_sbids,mode="quiet")
        cur,rejected_sbids = check_sbids_in_db(conn,rejected_sbids)
        print("Rejected sbids in db to be deleted:")
        rejected_sbids.sort(reverse=True)
        print(rejected_sbids)
        cur.close()
        cur = delete_sbids(conn,rejected_sbids) 
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "DELETESBIDS":
        cur = delete_sbids(conn,SBIDS,VERSIONS)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "DELETEDETECTION":
        cur = remove_sbids_from_detection(conn,SBIDS,VERSIONS)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "CHECK_SBIDS":
        cur,sbids = check_sbids_in_db(conn)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "CHECK_LOCAL_SBIDS":
        cur = check_local_processed_sbids(SBIDDIR)
        conn.commit()
        cur.close()
        conn.close()
            
    print(f"Job took {time.time()-starttime} sec for {len(SBIDS)} sbids {SBIDS}")


