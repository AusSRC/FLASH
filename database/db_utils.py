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
#       version 1.02 02/09/2023
#
#       Edit USER SECTION below to define the type of operation

############################################### USER SECTION ###################################################
# If an attribute doesn't apply, set it to ""

# 1. Define the type of deletion run you want to run on the database from the following choices:


# Delete an sbid from the database. Also deletes any reference in a spectral or detection run
#RUN_TYPE = "DELETESBIDS" 
# Remove detection processing from an sbid -reverts to a 'spectral run' sbid
#RUN_TYPE = "SBIDSPLOTONLY"
# Add catalogue data - remember to add your Opal password as a command line arg with '-p'
RUN_TYPE = "CATALOGUE"
DOWNLOAD_CAT = False # If the catalogues are not already downloaded, set this to True
ADD_CAT = True # Don't just download the catalogues - add them to the database too.

# Check if the sbids exist in the db
#RUN_TYPE = "CHECK_SBIDS"

# Check for processed files in local sbid dirs
#RUN_TYPE = "CHECK_LOCAL_SBIDS"
SBIDDIR = "/scratch/ja3/ger063/data/casda"

# 2. List of sbids (and their corresponding versions) to process. 
# On slow connections, you might need to do this one sbid at a time, as per the example,
# in case of timeouts when connected to the database for multiple sbids with many components
SBIDS = [45825,45828,45833,45835]
VERSIONS = [] # This list should correspond to the above sbids list = set to empty for just the latest version of each sbid.

# 3. If adding catalogue data, provide the directory that holds, or will hold, the catalogues by sbid
CATDIR = "/scratch/ja3/ger063/data/casda/catalogues"
DATADIR = CATDIR
UNTAR = False
DELETE_CATS = False # save space by deleting catalogues after processing
ONLY_CATS = True # Only download catalogues - not spectral and noise data

####################################################################################################################
########################## DO NOT EDIT FURTHER #####################################################################
####################################################################################################################

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

def get_catalogues(catalogue_only = ONLY_CATS):
    # These functions are defined in module 'casda_download'

    args = set_parser()
    args.catalogues_only = catalogue_only
    #sbid_list = get_sbids(args)
    sbid_list = SBIDS
    casda,casdatap = authenticate(args)
    process_sbid_list(sbid_list,args,casda,casdatap,exists=True)
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

def __get_sbid_components_in_db(cur,sbid):
    sbid_id,version = get_max_sbid_version(cur,sbid)
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

def add_sbid_catalogue(conn,sbid,casda_folder):

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
    components_db = __get_sbid_components_in_db(cur,sbid)
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
        versions = [None]*len(selected_sbids)

    for sbid,version in zip (sbids,versions):
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Delete associated large object of ascii files
        oid_query = "select ascii_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()
        oid_delete = "SELECT lo_unlink(%s);"
        for i in lon:
            cur.execute(oid_delete,(i,))
            
        # This sbid will possibly be referenced in the detect_run table. Remove the reference.
        cur.execute(f"SELECT detect_runid from sbid where id = {sbid_id};")
        runid = cur.fetchall()[0][0]

        sbid_query = "SELECT id,SBIDS from detect_run where %s = ANY (SBIDS);"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            cur = remove_sbids_from_detection(conn,[sbid],version,runid)
        except IndexError:
            print(f"No detection run found for sbid {sbid}:{version}")

        # It will DEFINITELY be referenced in the spect_run table - remove
        sbid_query = "SELECT id from spect_run where %s = ANY (SBIDS);"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            remove_sbid_from_spectral(cur,sbid,runid)
        except IndexError:
            # This should NEVER happen
            print(f"No spectral run found for sbid {sbid}:{version}")

        # Now remove the sbid from the SBID table (will also remove associated components) and any large objects
        sbid_delete = "DELETE from SBID where id = %s;"
        cur.execute(sbid_delete,(sbid_id,))

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
        sbid_update = "UPDATE sbid SET detectionF = %s, detect_tar = NULL where id = %s;"
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
        get_catalogues()
        if ADD_CAT:
            for sbid in SBIDS:
                cur = add_sbid_catalogue(conn,sbid,CATDIR)
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


