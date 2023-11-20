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
DATADIR = CATDIR
UNTAR = False
DELETE_CATS = False # save space by deleting catalogues after processing
ONLY_CATS = True # Only download catalogues - not spectral and noise data

####################################################################################################################
########################## DO NOT EDIT FURTHER #####################################################################
####################################################################################################################

def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-m', '--mode',
            default="CATALOGUE",
            help='Specify run mode: DELETESBIDS, SBIDSPLOTONLY, CATALOGUE, CHECK_SBIDS, CHECK_LOCAL_SBIDS (default: %(default)s)')
    parser.add_argument('-s', '--sbid_list',
            default=None,
            help='Specify the sbid list eg 11346,11348 (default: %(default)s)')    
    parser.add_argument('-d', '--sbid_dir',
            default="/scratch/ja3/ger063/data/casda",
            help='Specify local directory to use (default: %(default)s)')    
    parser.add_argument('-c', '--catalogues_only',
            default=False,
            action='store_true',
            help='Specify whether you want to download catalogues only (default: %(default)s)')    
    parser.add_argument('-e', '--email_address',
            default="gordon.german@csiro.au",
            help='Specify email address for login to CASDA (default: %(default)s)')
    parser.add_argument('-p', '--password',
            default=None,
            help='Specify the password for login to CASDA (default: %(default)s)')    
    parser.add_argument('-a', '--add_cat',
            default=None,
            help='Add the catalogue data to the database? (default: %(default)s)')    
    args = parser.parse_args()
    return args

def set_mode_and_values(args):
    global RUN_TYPE, SBIDDIR, DATADIR, CATDIR, SBIDS, VERSIONS, ONLY_CATS, ADD_CAT

    RUN_TYPE = args.mode.strip().upper()
    SBIDDIR = args.sbid_dir.strip()
    DATADIR = SBIDDIR
    CATDIR = SBIDDIR + "/catalogues"
    sbids = args.sbid_list.split(',')
    for sbid in sbids:
        if ":" in sbid:
            SBIDS.append(sbid.split(":")[0])
            VERSIONS.append(sbid.split(":")[1])
        else:
            SBIDS.append(sbid)
            VERSIONS.append(None)
    ONLY_CATS = args.catalogues_only
    ADD_CAT = args.add_cat


def connect(db="flashdb",user="flash",host="146.118.64.208",password="aussrc"):

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

def check_sbids_in_db(conn):

    # Check if the sbids listed in SBIDS are in the db

    cur = get_cursor(conn)
    for sbid in SBIDS:
        sbid_id,ver = get_max_sbid_version(cur,sbid)
        print(f"{sbid}: id = {sbid_id}, version = {ver}")

    return cur

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
###################################### Catalogue data ####################################################

def get_catalogues(args):
    # These functions are defined in module 'casda_download'
    print(DATADIR,CATDIR)
    if not DOWNLOAD_CAT:
        print("Catalogues not downloaded")
        return
    #args = set_parser()
    #args.catalogues_only = catalogue_only
    #sbid_list = get_sbids(args)
    sbid_list = SBIDS
    casda,casdatap = authenticate(args)
    process_sbid_list(sbid_list,args,casda,casdatap,DATADIR,CATDIR,exists=True)
    print(f"Retrieved catalogues for sbids {sbid_list}")
    if not args.catalogues_only:
        print("   + spectra and noise data")

def __get_component_catalog_data(catname,comp_name):

    with open(catname,'r',encoding = 'utf-8') as file:
        xml_data = file.read()
    xml_dict = xmltodict.parse(xml_data)
    fieldnames = []
    datadict = {}
    # Get field names
    for row in xml_dict['VOTABLE']['RESOURCE']['TABLE']['FIELD']:
        fieldnames.append(row['@name'].strip())

    # Get data for given component
    for row in xml_dict['VOTABLE']['RESOURCE']['TABLE']['DATA']['TABLEDATA']['TR']:
        if row['TD'][1] == comp_name:
            for i,val in enumerate(row['TD']):
                datadict[fieldnames[i]] = val
            break
    return datadict

def __get_sbid_catalog_data(catname):

    with open(catname,'r',encoding = 'utf-8') as file:
        xml_data = file.read()
    xml_dict = xmltodict.parse(xml_data)
    fieldnames = []
    datadict = {}
    catdict = {}
    # Get field names
    for row in xml_dict['VOTABLE']['RESOURCE']['TABLE']['FIELD']:
        fieldnames.append(row['@name'].strip())

    # Get data for all listed components
    for row in xml_dict['VOTABLE']['RESOURCE']['TABLE']['DATA']['TABLEDATA']['TR']:
        comp_name =  row['TD'][1]
        for i,val in enumerate(row['TD']):
            datadict[fieldnames[i]] = val
        catdict[comp_name] = datadict
        datadict = {}
    return catdict

def __get_sbid_components_in_db(cur,sbid,version):
    sbid_id,version = get_max_sbid_version(cur,sbid,version)
    query = "select comp_id from component where sbid_id = %s"
    cur.execute(query,(sbid_id,))
    components = cur.fetchall()
    component_names = []
    for comp in components:
        component_names.append(comp[0])
    return component_names

def __add_component_catalog_to_db(cur,comp_id,catdict):

    query = "UPDATE component set component_name = %s, ra_hms_cont = %s, dec_dms_cont = %s, ra_deg_cont = %s, dec_deg_cont = %s, flux_peak = %s, flux_int = %s, has_siblings = %s where comp_id = %s;"
    cur.execute(query,(catdict['component_name'],catdict['ra_hms_cont'],catdict['dec_dms_cont'],catdict['ra_deg_cont'],catdict['dec_deg_cont'],catdict['flux_peak'],catdict['flux_int'],catdict['has_siblings'],comp_id))
    print(".",end="")

def add_sbid_catalogue(conn,sbid,casda_folder,version=None):

    cur = get_cursor(conn)
    names = glob(f"{casda_folder}/*SB{sbid}*.components.xml")
    if len(names) != 1:
        print(f"Error in {sbid} catalogue name {names}. Not processing")
        return cur
    name = names[0]
    print(f"Reading {os.path.basename(name)}")
    
    # Get components listed in catalogue
    components_data = __get_sbid_catalog_data(name)
    # Get components listed in db for this sbid (will be much less than in catalogue)
    components_db = __get_sbid_components_in_db(cur,sbid,version)
    print(f"Components in catalogue: {len(components_data.keys())}, in db: {len(components_db)}")
    for comp_id in components_db:
        name = comp_id.replace(".fits","").replace("spec_","")
        comp_data = components_data[name]
        __add_component_catalog_to_db(cur,comp_id,comp_data)
    print()
    print(f"Added catalogue data for {sbid}")
    return cur

##########################################################################################################
###################################### DELETING RUNS #####################################################

def delete_sbids(conn,sbids,versions=None):

    cur = get_cursor(conn)
    if not versions:
        versions = [None]*len(sbids)

    for sbid,version in zip (sbids,versions):
        print(f"For {sbid}:{1 if version == None else version} :")
        print("\tFinding ascii LOB")
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Delete associated large object of ascii files
        oid_query = "select ascii_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()
        oid_delete = "SELECT lo_unlink(%s);"
        for i in lon:
            cur.execute(oid_delete,(i,))
        print("\tDeleted ascii LOB")
            
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
            sbids.remove(sbid)
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
    sbids.remove(sbid)
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
    conn = connect()

    args = set_parser()
    set_mode_and_values(args)

    # Add run
    if RUN_TYPE == "DELETESBIDS":
        cur = delete_sbids(conn,SBIDS,VERSIONS)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "SBIDSPLOTONLY":
        cur = remove_sbids_from_detection(conn,SBIDS,VERSIONS)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "CATALOGUE":
        print(f"Processing sbids {SBIDS}")
        get_catalogues(args)
        if ADD_CAT:
            for i,sbid in enumerate(SBIDS):
                ver = VERSIONS[i]
                cur = add_sbid_catalogue(conn,sbid,CATDIR,ver)
            conn.commit()
            cur.close()
        conn.close()
        if ADD_CAT and DELETE_CATS:
            for sbid in SBIDS:
                os.system(f"rm -R {CATDIR}/{sbid}")
            print(f"Downloaded catalogues deleted: {SBIDS}")
    elif RUN_TYPE == "CHECK_SBIDS":
        cur = check_sbids_in_db(conn)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "CHECK_LOCAL_SBIDS":
        cur = check_local_processed_sbids(SBIDDIR)
        conn.commit()
        cur.close()
        conn.close()
            
    print(f"Job took {time.time()-starttime} sec for {len(SBIDS)} sbids {SBIDS}")


