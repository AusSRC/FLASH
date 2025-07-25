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
#       version 1.03 25/06/2024
#
#       Edit USER SECTION below to define the type of operation

############################################### USER SECTION ###################################################
# If an attribute doesn't apply, set it to ""

# Note that these are out of date; the required attribs are set via the cmd line - see set_parser() below.
RUN_TYPE = ""
SUBMODE = "STD" # For deletion of detections. specify the type to delete: STD (deletes all), INVERT or MASK 
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
DBHOST = ""
DBPORT = ""


####################################################################################################################
########################## DO NOT EDIT FURTHER #####################################################################
####################################################################################################################

def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-m', '--mode',
            default="CATALOGUE",
            help='Specify run mode: DELETESBIDS, DELETEDETECTION, CHECK_SBIDS, CHECK_LOCAL_SBIDS (default: %(default)s)')
    parser.add_argument('-sm', '--submode',
            default="STD",
            help='For deletion of detections. specify the type to delete: STD (deletes all), INVERT or MASK (default: %(default)s)')

    parser.add_argument('-s', '--sbid_list',
            default=None,
            help='Specify the sbid list eg 11346,11348 (default: %(default)s)')    
    parser.add_argument('-d', '--sbid_dir',
            default="/scratch/ja3/ger063/data/casda",
            help='Specify local directory to use (default: %(default)s)')    
    parser.add_argument('-e', '--email_address',
            default=None,
            help='Specify email address for login to CASDA (default: %(default)s)')
    parser.add_argument('-ht', '--host',
            default="10.0.2.225",
            help='database host ip (default: %(default)s)')    
    parser.add_argument('-pt', '--port',
            default="5432",
            help='database host port (default: %(default)s)')    
    parser.add_argument('-p', '--password',
            default=None,
            help='Specify the password for login to CASDA (default: %(default)s)')    
    parser.add_argument('-pw', '--flashpw',
            default=None,
            help='Specify the password for login to FLASHDB (default: %(default)s)')    
    args = parser.parse_args()
    return args

def set_mode_and_values(args):
    global RUN_TYPE, SBIDDIR, DATADIR, SBIDS, VERSIONS, ONLY_CATS, ADD_CAT, PASSWD, DBHOST, DBPORT, SUBMODE

    RUN_TYPE = args.mode.strip().upper()
    if RUN_TYPE == "DELETEDETECTION":
        SUBMODE = args.submode.strip().upper()
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
    DBHOST = args.host.strip()
    DBPORT = args.port.strip()


def connect(db="flashdb",user="flash",password=None):

    if not password:
        password = PASSWD
    conn = psycopg2.connect(
        database = db,
        user = user,
        password = password,
        host = DBHOST,
        port = DBPORT
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
def get_detection_flags(cur,sbid_id):
    mode_query = "select detectionF,invert_detectionF,mask_detectionF from sbid where id = %s"
    cur.execute(mode_query,(sbid_id,))
    modes = cur.fetchone()
    stdF = modes[0]
    invertF = modes[1]
    maskF = modes[2]

    return stdF,invertF,maskF,cur


def delete_sbids(conn,sbids,versions=None):

    cur = get_cursor(conn)
    if not versions:
        versions = [None]*len(sbids)

    for sbid,version in zip (sbids,versions):
        # Get rid of any associated files on the compute resource
        #os.system(f"rm -Rf {SBIDDIR}/{sbid}")
        #os.system(f"rm -f {CATDIR}/*{sbid}*.xml*") 
        if not sbid:
            continue
        print(f"For {sbid}:{1 if version == None else version} :")
        print("\tFinding ascii LOB")
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Delete associated large object of ascii files
        oid_query = "select ascii_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()
        print("\tDeleting ascii LOB")
        oid_delete = "SELECT lo_unlink(%s);"
        try:
            for i in lon:
                cur.execute(oid_delete,(i,))
            print("\tDeleted ascii LOB",flush=True)
        except TypeError:
            print(f"ascii LOB for {sbid}:{version} not found")
            
        # This sbid will possibly be referenced in the detect_run table. Remove the reference.
        print(f"Check for {sbid}:{version} detection run",flush=True)
        cur.execute(f"SELECT detect_runid from sbid where id = {sbid_id};")
        runid = cur.fetchall()[0][0]

        sbid_query = "SELECT id,SBIDS from detect_run where %s = ANY (SBIDS);"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            cur = remove_sbids_from_detection(conn,[sbid],[version],runid)
            print("\tRemoved reference in detect_run table",flush=True)
        except IndexError:
            print(f"\tNo detection run found for sbid {sbid}:{version}",flush=True)
        # It will DEFINITELY be referenced in the spect_run table - remove
        sbid_query = "SELECT id from spect_run where %s = ANY (SBIDS);"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            remove_sbid_from_spectral(cur,sbid,runid)
            print("\tRemoved reference in spectral_run table",flush=True)
        except IndexError:
            # This should NEVER happen
            print(f"\tNo spectral run found for sbid {sbid}:{version}",flush=True)

        # Now remove the sbid from the SBID table (remove associated components first)
        print("\tDeleting components ...This may take 30min or so")
        # Check if there are any components to delete:
        count_comps = "select count(*) from component where sbid_id = %s"
        cur.execute(count_comps,(sbid_id,))
        count = int(cur.fetchall()[0][0])
        # This delete can take 20mins or more:
        #comp_delete = "delete from component where sbid_id = %s;"
        if count > 0:
            comp_delete = "select delete_comps(%s);"
            cur.execute(comp_delete,(sbid_id,))
        sbid_delete = "DELETE from SBID where id = %s;"
        cur.execute(sbid_delete,(sbid_id,))
        print(f"\t{sbid}:{version} deleted!",flush=True)

    return cur
     
def remove_sbids_from_detection(conn,selected_sbids,versions=None,runid=None,mode=None):

    cur = get_cursor(conn)
    if not mode:
        mode = "STD"
    if not versions:
        versions = [None]*len(selected_sbids)
    runflagid = runid
    for sbid,version in zip(selected_sbids,versions):
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        print(f"{sbid}:{version} - deleting outputs lob ")

        # Determine what detection modes have been run
        stdF,invertF,maskF,cur = get_detection_flags(cur,sbid_id)

        # Remove the config and mask files
        config_delete = "UPDATE sbid SET detect_config_tar = NULL,mask = NULL where id = %s"
        cur.execute(config_delete,(sbid_id,))

        # Delete associated large object of detection outputs
        # STD, INVERT and MASK
        # 
        oid = ""
        if mode == "STD" and stdF:
            print(" -- Deleting STD detection data")
            oid_query = f"select detect_tar from sbid where id = %s;"
            cur.execute(oid_query,(sbid_id,))
            lon = cur.fetchone()
            oid_delete = "SELECT lo_unlink(%s);"
            for i in lon:
                cur.execute(oid_delete,(i,))
            if not runid:
                # Need to get detection id 
                sbid_query = "SELECT detect_runid from sbid where id = %s;"
                cur.execute(sbid_query,(sbid_id,))
                runflagid = cur.fetchone()[0]
            # Remove detection flag and detection data from the sbid
            sbid_update = "UPDATE sbid SET detectionF = %s, detect_tar = NULL, detect_results = NULL, results = NULL, detect_runid = NULL where id = %s;"
            cur.execute(sbid_update,(False,sbid_id))
            
            # Remove reference in detect_run
            print(f"{sbid}:{version} - removing reference in detect_run ")
            sbid_query = "SELECT SBIDS from detect_run where id = %s;"
            cur.execute(sbid_query,(runflagid,))
            print(runflagid,sbid)
            sbids = None
            try:
                sbids = cur.fetchone()[0]
                sbids.remove(int(sbid))
            except TypeError or IndexError:
                print(f"{sbid}:{version} - nothing to remove ")
            # Check if sbids list now empty, in which case delete whole detection
            if not sbids:
                detect_stat = "DELETE from detect_run where id = %s;"
                cur.execute(detect_stat,(runflagid,))
                print(f"    -- Deleted detection {runflagid}")
            else:
            # Update detection by removing sbid from row
                detect_stat = "UPDATE detect_run SET SBIDS = %s where id = %s;"
                cur.execute(detect_stat,(sbids,runflagid))
                print(f"    -- Updated detection {runflagid}")

        if mode in ("STD","INVERT") and invertF:
            print(" -- Deleting INVERT detection data")
            oid_query = f"select invert_detect_tar from sbid where id = %s;"
            cur.execute(oid_query,(sbid_id,))
            lon = cur.fetchone()
            oid_delete = "SELECT lo_unlink(%s);"
            for i in lon:
                cur.execute(oid_delete,(i,))
            if not runid:
                # Need to get detection id 
                sbid_query = "SELECT invert_detect_runid from sbid where id = %s;"
                cur.execute(sbid_query,(sbid_id,))
                runflagid = cur.fetchone()[0]
            # Remove detection flag and inverted detection data from the sbid
            sbid_update = "UPDATE sbid SET invert_detectionF = %s, invert_detect_tar = NULL, invert_detect_results = NULL, invert_results = NULL, invert_detect_runid = NULL where id = %s;"
            cur.execute(sbid_update,(False,sbid_id))
            
            # Remove reference in detect_run
            print(f"{sbid}:{version} - removing reference in detect_run ")
            sbid_query = "SELECT SBIDS from detect_run where id = %s;"
            cur.execute(sbid_query,(runflagid,))
            print(runflagid,sbid)
            sbids = None
            try:
                sbids = cur.fetchone()[0]
                sbids.remove(int(sbid))
            except TypeError or IndexError:
                print(f"{sbid}:{version} - nothing to remove ")
            # Check if sbids list now empty, in which case delete whole detection
            if not sbids:
                detect_stat = "DELETE from detect_run where id = %s;"
                cur.execute(detect_stat,(runflagid,))
                print(f"    -- Deleted detection {runflagid}")
            else:
            # Update detection by removing sbid from row
                detect_stat = "UPDATE detect_run SET SBIDS = %s where id = %s;"
                cur.execute(detect_stat,(sbids,runflagid))
                print(f"    -- Updated detection {runflagid}")
        if mode in ("STD","MASK") and maskF:
            print(" -- Deleting MASK detection data")
            oid_query = f"select mask_detect_tar from sbid where id = %s;"
            cur.execute(oid_query,(sbid_id,))
            lon = cur.fetchone()
            oid_delete = "SELECT lo_unlink(%s);"
            for i in lon:
                cur.execute(oid_delete,(i,))
            if not runid:
                # Need to get detection id 
                sbid_query = "SELECT invert_detect_runid from sbid where id = %s;"
                cur.execute(sbid_query,(sbid_id,))
                runflagid = cur.fetchone()[0]
            # Remove detection flag and masked detection data from the sbid
            sbid_update = "UPDATE sbid SET mask_detectionF = %s, mask_detect_tar = NULL, mask_detect_results = NULL, mask_results = NULL, mask_detect_runid = NULL where id = %s;"
            cur.execute(sbid_update,(False,sbid_id))
            
            # Remove reference in detect_run
            print(f"{sbid}:{version} - removing reference in detect_run ")
            sbid_query = "SELECT SBIDS from detect_run where id = %s;"
            cur.execute(sbid_query,(runflagid,))
            print(runflagid,sbid)
            sbids = None
            try:
                sbids = cur.fetchone()[0]
                sbids.remove(int(sbid))
            except TypeError or IndexError:
                print(f"{sbid}:{version} - nothing to remove ")
            # Check if sbids list now empty, in which case delete whole detection
            if not sbids:
                detect_stat = "DELETE from detect_run where id = %s;"
                cur.execute(detect_stat,(runflagid,))
                print(f"    -- Deleted detection {runflagid}")
            else:
            # Update detection by removing sbid from row
                detect_stat = "UPDATE detect_run SET SBIDS = %s where id = %s;"
                cur.execute(detect_stat,(sbids,runflagid))
                print(f"    -- Updated detection {runflagid}")
    return cur

def remove_detection_from_components(conn,cur,sbids,versions,mode=None):
    if not versions:
        versions = [None]*len(sbids)
    if not mode:
        mode = "STD"
    for sbid,version in zip(sbids,versions):
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        detect_state = "detection"
        # load the detection flags from the db
        stdF,invertF,maskF,cur = get_detection_flags(cur,sbid_id)
        print(f"{sbid}:{version} - deleting detection from components ")
        if mode == "STD":
            # delete all detection variables from components of this sbid
            delete_detection = "UPDATE component SET processState = 'spectral',mode_num = NULL,invert_mode_num = NULL,mask_mode_num = NULL,ln_mean = NULL, invert_ln_mean = NULL,mask_ln_mean = NULL,detection_date = NULL,invert_detection_date = NULL,mask_detection_date = NULL where sbid_id = %s"
            cur.execute(delete_detection,(sbid_id,))
        elif mode == "INVERT":
            # delete all invert detection variables from components of this sbid
            # Set the detection state correctly
            if maskF:
                detect_state = "masked_detection"    
            delete_detection = "UPDATE component SET processState = %s,invert_mode_num = NULL,invert_ln_mean = NULL,invert_detection_date = NULL where sbid_id = %s"
            cur.execute(delete_detection,(detect_state,sbid_id))
        elif mode == "MASK":
            # delete all mask detection variables from components of this sbid
            # Set the detection state correctly
            if invertF:
                detect_state = "inverted_detection"    
            delete_detection = "UPDATE component SET processState = %s,mask_mode_num = NULL,mask_ln_mean = NULL,mask_detection_date = NULL where sbid_id = %s"
            cur.execute(delete_detection,(detect_state,sbid_id))
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
        cur = remove_sbids_from_detection(conn,SBIDS,VERSIONS,mode=SUBMODE)
        cur = remove_detection_from_components(conn,cur,SBIDS,VERSIONS,mode=SUBMODE)
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


