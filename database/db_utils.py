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
#       version 1.06 25/06/2024
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
BADFILES = "bad_ascii_files" # relative to SBIDDIR
SBIDS = []
VERSIONS = [] # This list should correspond to the above sbids list = set to empty for just the latest version of each sbid.
CATDIR = SBIDDIR + "/catalogues"
DATADIR = CATDIR
UNTAR = False
INVERT=False # if in detection mode, are we looking for inverted detections or normal ones?
DELETE_CATS = False # save space by deleting catalogues after processing
ONLY_CATS = True # Only download catalogues - not spectral and noise data
DUMMY=False # Set to true to only query - don't download or upload anything.
REJECTED=True # If set, process sbids even if marked as 'REJECTED'.
CASDA_EMAIL = ""
PASSWD = ""

###############################################################################################################
############ - FLASHDB details ################################################################################
HOST = "10.0.2.225"
PORT = 5432

#HOST = "146.118.64.208"
#PORT = 2095

####################################################################################################################
########################## DO NOT EDIT FURTHER #####################################################################
####################################################################################################################

def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-m', '--mode',
            default="CATALOGUE",
            help='Specify run mode: CATALOGUE, CHECK_SBIDS, BAD_COMPS, DETECT_TARBALL, CHECK_LOCAL_SBIDS, GETNEWSBIDS, SBIDSTODETECT (default: %(default)s)')
    parser.add_argument('-s', '--sbid_list',
            default=None,
            help='Specify the sbid list eg 11346,11348 (default: %(default)s)')    
    parser.add_argument('-ht', '--host',
            default="10.0.2.225",
            help='database host ip (default: %(default)s)')    
    parser.add_argument('-pt', '--port',
            default="5432",
            help='database host port (default: %(default)s)')    
     parser.add_argument('-d', '--sbid_dir',
            default="/scratch/ja3/ger063/data/casda",
            help='Specify local directory to use (default: %(default)s)')   
    parser.add_argument('-i', '--invert',
            default=False,
            action='store_true',
            help='Specify if using inverted spectra for SBIDSTODETECT (default: %(default)s)')   
    parser.add_argument('-c', '--catalogues_only',
            default=False,
            action='store_true',
            help='Specify whether you want to download catalogues only (default: %(default)s)')    
    parser.add_argument('-e', '--email_address',
            default=CASDA_EMAIL,
            help='Specify email address for login to CASDA (default: %(default)s)')
    parser.add_argument('-p', '--password',
            default=None,
            help='Specify the password for login to CASDA (default: %(default)s)')    
    parser.add_argument('-pw', '--flashpw',
            default=None,
            help='Specify the password for login to FLASHDB (default: %(default)s)')    
    parser.add_argument('-a', '--add_cat',
            default=None,
            help='Add the catalogue data to the database? (default: %(default)s)')  
    parser.add_argument('-n', '--no_action',
            default=False,
            action='store_true',
            help='If set, only query - dont download or upload anything. (default: %(default)s)')  
    parser.add_argument('-r', '--rejected',
            default=False,
            action='store_true',
            help='If set, process sbids even if marked as "REJECTED". (default: %(default)s)')  
  
    args = parser.parse_args()
    return args

def set_mode_and_values(args):
    global RUN_TYPE, SBIDDIR, DATADIR, CATDIR, SBIDS, VERSIONS, ONLY_CATS, ADD_CAT, INVERT, DUMMY, REJECTED, CASDA_EMAIL
    global HOST, PORT, PASSWD

    RUN_TYPE = args.mode.strip().upper()
    SBIDDIR = args.sbid_dir.strip()
    DATADIR = SBIDDIR
    CATDIR = SBIDDIR + "/catalogues"
    if args.sbid_list:
        sbids = args.sbid_list.split(',')
        for sbid in sbids:
            if ":" in sbid:
                SBIDS.append(sbid.split(":")[0])
                VERSIONS.append(sbid.split(":")[1])
            else:
                SBIDS.append(sbid)
                VERSIONS.append(None)
    CASDA_EMAIL = args.email_address.strip()
    ONLY_CATS = args.catalogues_only
    INVERT = args.invert
    ADD_CAT = args.add_cat
    DUMMY = args.no_action
    REJECTED = args.rejected
    PASSWD = args.flashpw
    HOST = args.host.strip()
    PORT = args.port.strip()



def connect(db="flashdb",user="flash",host=HOST,port=PORT,password=None):

    if not password:
        password = PASSWD
    conn = psycopg2.connect(
        database = db,
        user = user,
        password = password,
        host = host,
        port = port
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

def check_db_detection_run(conn,invert=False):
    # check the flashdb for any sbids that need to have the LINEFINDER run against them.
    # This only checks Survey sbids (not pilot) and will check if any sbid with quality not 'BAD', 'REJECTED' or 'NOT_VALIDATED'
    # has not been processed by the linfinder

    sbids = []
    cur = get_cursor(conn)
    if invert:
        print("For inversion:")
        query = "select sbid_num from sbid where quality not in ('BAD','NOT_VALIDATED','REJECTED') and (invert_detectionF = false or invert_detectionF is NULL) and sbid_num > 43426 order by sbid_num;"
    else:
        query = "select sbid_num from sbid where quality not in ('BAD','NOT_VALIDATED','REJECTED') and detectionF = false and sbid_num > 43426 order by sbid_num;"
    cur.execute(query,)
    result = cur.fetchall()
    for res in result:
        sbids.append(res[0])
    return sbids
   
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

###############################################
def create_large_object(conn,data):

    print(f"Trying to create lob from {data}")
    #lob = conn.lobject(0,'wb',0,data)
    #print(f"Created lob {lob.oid} in db")
    with open(data, "rb") as fd:
        try:
            lob = conn.lobject(0,'wb',0)
            lob.write(fd.read())
            print(f"Created lob {lob.oid} in db")
        except (psycopg2.Warning, psycopg2.Error) as e:
            print("Exception: {}".format(e))
    return lob
    

################################################
def update_pointings_from_casda(conn,args):

    # This function is defined in module 'casda_download'
    casda,casdatap = authenticate(args)

    cur =  get_cursor(conn)
    # Get all the sbids in the FLASHDB
    query = "select sbid_num from sbid where pointing = 'Unknown'"
    cur.execute(query)
    result = cur.fetchall()
    sbids = []
    for res in result:
        sbids.append(res[0])
    
# Now query CASDA for pointing field of each sbid
    for sbid in sbids:
        job = casdatap.launch_job_async("SELECT filename FROM casda.observation_evaluation_file oef inner join casda.observation o on oef.observation_id = o.id where o.sbid = %s and filename like 'SourceSpectra-image%%'" % sbid)
        r = job.get_results()
        name = str(r['filename'])
        try:
            fieldname = "FLASH_" + name.split('FLASH_')[1].split('.')[0]
        except:
            print(f"{sbid} does not have a valid SourceSpectra filename ({name}), so skipping")
            continue
        flash_query = "update sbid set pointing = %s where sbid_num = %s"
        cur.execute(flash_query,(fieldname,sbid))
        print(f"Updated sbid {sbid} with pointing field = {fieldname}")

    return cur

def set_bad_components(conn, args):

    cur =  get_cursor(conn)
    # get a list of files in the bad_ascii_files directory
    bad_files_dir = f"{SBIDDIR}/{BADFILES}"
    bad_files_list = [f.split("_opd.dat")[0] for f in os.listdir(bad_files_dir) if f.endswith("opd.dat")]

    for fname in bad_files_list:
        # check the last word of the file
        last_word = 'eof error'
        with open(f'{bad_files_dir}/{fname}_opd.dat') as f:
            for line in f:
                pass
            last_word = line.split()[-1]        
        if last_word == 'nan':
            comment = 'nan'
        update = "update component set processState = 'BAD', comment = %s where comp_id like %s;"
        like = '%{}%'.format(fname)
        cur.execute(update,(comment,like))
        print(f"Set component {fname} to processState = 'BAD' - due to {comment}")

    return cur
    

##########################################################################################################
###################################### Catalogue data ####################################################
def update_quality_from_casda(conn,casda,casdatap,get_rejected):
    # This function is defined in module 'casda_download'
    casda_sbids,quality_dict = get_sbids_in_casda(args,casda,casdatap,get_rejected)
    cur = get_cursor(conn)
    quality_changed = []
    print("Checking QUALITY tags in FLASHDB")
    # For each sbid, find it in the FLASHDB and update the quality
    for sbid in casda_sbids:
        print(f"\t{sbid}",end="")
        sbid_id,version = get_max_sbid_version(cur,sbid)
        query = "select sbid_num,quality from sbid where id = %s"
        cur.execute(query,(sbid_id,))
        result = cur.fetchone()

        if result and int(result[0]) == int(sbid):
            db_quality = result[1]
            if db_quality == quality_dict[sbid]:
                print(f" quality current at {db_quality}")
                continue
            else:
                print(f" : updating quality from {db_quality} to {quality_dict[sbid]}")
                sql = "update sbid set quality = %s where id = %s"
                cur.execute(sql,(quality_dict[sbid],sbid_id))
                quality_changed.append(f"{sbid}:{quality_dict[sbid]}")
        else:
            print(" not found in FLASHDB")
    print(f"Quality changes: {quality_changed}")
    return cur,casda_sbids


def get_new_sbids(conn,args,get_rejected=False):

    # This function is defined in module 'casda_download'
    casda,casdatap = authenticate(args)

    cur,casda_sbids = update_quality_from_casda(conn,casda,casdatap,get_rejected)
    # Get existing sbids in db
    query = "select sbid_num from sbid;"
    cur.execute(query,)
    results = cur.fetchall()
    db_sbids = []
    for res in results:
        db_sbids.append("%s" % res[0])
    db_sbids.sort(reverse=True)

    # Return only sbids that are not in the FLASH db
    new_sbids = list(set(casda_sbids) - set(db_sbids))
    new_sbids.sort(reverse=True)
    # if arg '-s' is given, limit size of array to first 's' values
    if args.sbid_list:
        new_sbids = new_sbids[0:int(args.sbid_list)]

    return cur,new_sbids,casda,casdatap
    

def get_catalogues(args,casda=None,casdatap=None,get_rejected=False):
    # These functions are defined in module 'casda_download'
    if not DOWNLOAD_CAT:
        print("Catalogues not downloaded")
        return
    #args = set_parser()
    #args.catalogues_only = catalogue_only
    #sbid_list = get_sbids(args)
    sbid_list = SBIDS
    if not casda or not casdatap:
        casda,casdatap = authenticate(args)
    bad_sbids = process_sbid_list(sbid_list,args,casda,casdatap,DATADIR,CATDIR,exists=True,get_rejected=get_rejected)
    sbid_list = list(set(sbid_list) - set(bad_sbids))
    print(f"Retrieved catalogues for sbids: {sbid_list}")
    if not args.catalogues_only:
        print("   + spectra and noise data")
    return bad_sbids

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
    print(f"Items in catalogue: {len(components_data.keys())}, in db: {len(components_db)}")
    for comp_id in components_db:
        name = comp_id.replace(".fits","").replace("spec_","")
        comp_data = components_data[name]
        __add_component_catalog_to_db(cur,comp_id,comp_data)
    print()
    print(f"Added catalogue data for {sbid}")
    return cur

###############################################

def update_detection_tarball(conn,sbids,versions=None):

    os.chdir(DATADIR)
    for sbid,version in zip (sbids,versions):
        cur = get_cursor(conn)
        detect_data = None
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # delete current lob in db:
        oid_query = "select detect_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()[0]
        oid_delete = "SELECT lo_unlink(%s);"
        cur.execute(oid_delete,(lon,))

        # read in new tarball
        output_tarball = f"{sbid}/{sbid}_linefinder_outputs.tar.gz"
        with open(output_tarball,'rb') as f:
            detect_data = f.read()
        print(f"detect_data = {len(detect_data)}",flush=True)
        # Create a large object in the database:
        print("    -- loading to database")
        lob = create_large_object(conn,output_tarball)
        #lob = conn.lobject(oid=0,mode="wb", new_file=ascii_tarball)
        new_oid = lob.oid
        lob.close()
        update_query = "UPDATE SBID SET detect_results = %s, detect_tar = %s where id = %s;"
        cur.execute(update_query,(psycopg2.Binary(detect_data),new_oid,sbid_id))
        print(f"sbid table updated with detection tarball for sbid = {sbid}, version {version}")
        conn.commit()
        cur.close()



############################################################################################################################################
############################################################################################################################################

if __name__ == "__main__":

    starttime = time.time()
    args = set_parser()
    set_mode_and_values(args)

    conn = connect()
    bad_sbids = []
    casda = None
    casdatap = None

    if RUN_TYPE == "GETNEWSBIDS":
        cur,SBIDS,casda,casdatap = get_new_sbids(conn,args,get_rejected=REJECTED)
        print(f"\nValid sbids to process are: {SBIDS}\n")
        cur.close()
        if not DUMMY:
            RUN_TYPE = "CATALOGUE"
    if RUN_TYPE == "CATALOGUE" and not DUMMY:
        print(f"Processing sbids {SBIDS}")
        bad_sbids = get_catalogues(args,casda,casdatap,get_rejected=REJECTED)
        if bad_sbids:
            print(f"These sbids were not downloaded correctly: {bad_sbids}")
        SBIDS = list(set(SBIDS) - set(bad_sbids))
        
        if ADD_CAT:
            for i,sbid in enumerate(SBIDS):
                ver = VERSIONS[i]
                cur = add_sbid_catalogue(conn,sbid,CATDIR,ver)
            conn.commit()
            cur.close()
        if ADD_CAT and DELETE_CATS:
            for sbid in SBIDS:
                try:
                    os.system(f"rm -R {CATDIR}/{sbid}")
                except:
                    continue
            print(f"Downloaded catalogues deleted: {SBIDS}")
        conn.commit()
        conn.close()
    elif RUN_TYPE == "SBIDSTODETECT":
        sbids = check_db_detection_run(conn,INVERT)
        print("SBIDS that need detection analysis:")
        print(sbids)
        sys.exit()
        conn.commit()
        conn.close()
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
    elif RUN_TYPE == "CAT_TO_DB":
        for i,sbid in enumerate(SBIDS):
            ver = VERSIONS[i]
            cur = add_sbid_catalogue(conn,sbid,CATDIR,ver)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "UPDATE_POINTING":
        cur = update_pointings_from_casda(conn,args)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "BAD_COMPS":
        cur = set_bad_components(conn,args)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "DETECT_TARBALL":
        update_detection_tarball(conn,SBIDS,VERSIONS)
        conn.close()
            
    print(f"Job took {time.time()-starttime} sec for {len(SBIDS)} sbids:\n{SBIDS}")

