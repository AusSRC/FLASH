import os
import sys
import logging
import time
import datetime as dt
import os.path
import tarfile

import psycopg2

##################################### USER SET VARIABLES ###################################################

# For the below variables, set to "" if they don't apply.

# The expected data layout is:
# DATA_DIR ---
#       SBID 1 ---
#                |
#                   --- NoiseSpectra (inputs)
#                   --- SourceSpectra (inputs - components - ends in ".fits")
#                   --- spectra_plots (outputs - spectral image files - pairs of opd and flux per component - ends in ".png")
#                   --- spectra_ascii (outputs - files for detection - pairs of opd and flux per component - ends in "*.dat")
#                   --- outputs (directory holding outputs from linefinder for an sbid)
#       SBID 2 ---
#               etc
#
#   IF YOU NEED TO OVERRIDE THIS STRUCTURE, see USER SECTION 2, below
#
#   The (assumed) format for a component name is:
#       spec_SB<sb id>_component_<component id>.fits
#   eg:
#       "spec_SB45762_component_9b.fits"


############################################### USER SECTION 1 ###################################################
# If an attribute doesn't apply, set it to ""

# 1. Define the type of processing run you want to store in the database from the following choices:

# add a spectral processing run to the database (one or more SBID's)
RUN_TYPE = "spectral"   
# add a detection (Linefinder) processing run to the database (one or more SBID's). 
# The SBID(s) must already be in the database from a prior spectral run.
#RUN_TYPE = "detection"   
# Delete an sbid from the database. Also deletes any reference in a spectral or detection run
#RUN_TYPE = "DELETESBIDS" 
# Remove detection processing from an sbid -reverts to a 'spectral run' sbid
#RUN_TYPE = "SBIDSPLOTONLY"
# Set sbids to "GOOD" quality
#RUN_TYPE = "GOOD"
# Set sbids to "BAD" quality
#RUN_TYPE = "BAD"
# Set sbids to "UNCERTAIN" quality - this is the default when sbids are created in the db
#RUN_TYPE = "UNCERTAIN"

# 2. List of sbids to process. On slow connections, you might need to do this one sbid at a time, as per the example,
# in case of timeouts when connected to the database for multiple sbids with many components
SBIDS = [45762] #45823 45833 45815 45835 45762 45828 - 45825 has two ascii dirs??

# 3. Top level directory holding the SBID subdirs:
DATA_DIR = "/home/ger063/src/flash_data"

# 4. A temp directory where you have space and write access, to hold tarballs created during this script - these can be large!!
TMP_TAR_DIR = DATA_DIR

# 5. The SLURM error and stdout log files associated with the run (either spectral or linefinder)
ERROR_LOG = "/home/ger063/src/flash_data/45762/err.log"
STDOUT_LOG = "/home/ger063/src/flash_data/45762/stdout.log"

# 6. The compute platform used
PLATFORM = "setonix.pawsey.org.au"

# 7. The config file used for the spectral processing
SPECTRAL_CONFIG = "/home/ger063/src/flash_data/config_spectral/config.py"

# 8. The config directory used for the linefinder processing (contains linefinder.ini, model.txt and sources.log)
LINEFINDER_CONFIG_DIR = "/home/ger063/src/flash_data/config_linefinder"

# 9. The linefinder output directory, relative to each of the sbid directories
LINEFINDER_OUTPUT_DIR = "outputs"

# 10. The collected results file from a linefinder run
LINEFINDER_SUMMARY_FILE = "/home/ger063/src/flash_data/results.dat"

####################################################################################################################
############################################### USER SECTION 2 #####################################################
# Edit this if your data layout doesn't match the expected pattern above - these are relative to a single SBID directory
#
# Path to components for this sbid
COMPONENT_PATH = "SourceSpectra"

# Path to the spectral plots and spectral ascii files (they may be empty) for this sbid:
SPECTRAL_PLOT_PATH = "spectra_plots"
SPECTRAL_ASCII_PATH = "spectra_ascii"

# Path to the linefinder outputs (they may be empty) for this sbid
OUTPUT_PATH = "outputs"

# Path to Noise files for this sbid- not currently stored in the database, so not used:
NOISE_PATH = ""

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
    print(conn.get_dsn_parameters(),"\n")
    return conn

def get_cursor(conn):

    cursor = conn.cursor()
    return cursor


##########################################################################################################
###################################### DELETING RUNS #####################################################

def delete_sbids(conn,sbids):

    cur = get_cursor(conn)

    for sbid in sbids:
        # Delete associated large object of ascii files
        oid_query = "select ascii_tar from sbid where id = %s"
        cur.execute(oid_query,(sbid,))
        lon = cur.fetchone()
        oid_delete = "SELECT lo_unlink(%s);"
        for i in lon:
            cur.execute(oid_delete,(i,))
            
        # This sbid will possibly be referenced in the detect_run table. Remove the reference.
        sbid_query = "SELECT id,SBIDS from detect_run where %s = ANY (SBIDS)"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            cur = remove_sbids_from_detection(conn,[sbid],runid)
        except IndexError:
            print(f"No detection run processed sbid {sbid}")

        # It will DEFINITELY be referenced in the spect_run table - remove
        sbid_query = "SELECT id from spect_run where %s = ANY (SBIDS)"
        cur.execute(sbid_query,(sbid,))
        try:
            runid = cur.fetchall()[0][0]
            remove_sbid_from_spectral(cur,sbid,runid)
        except IndexError:
            # This should NEVER happen
            print(f"No spectral run processed sbid {sbid}")

        # Now remove the sbid from the SBID table (will also remove associated components) and any large objects
        sbid_delete = "DELETE from SBID where id = %s"
        cur.execute(sbid_delete,(sbid,))

    return cur
     
def remove_sbids_from_detection(conn,selected_sbids,runid=None):

    cur = get_cursor(conn)

    for sbid in selected_sbids:
        # Delete associated large object of detection outputs
        oid_query = "select detect_tar from sbid where id = %s"
        cur.execute(oid_query,(sbid,))
        lon = cur.fetchone()
        oid_delete = "SELECT lo_unlink(%s);"
        for i in lon:
            cur.execute(oid_delete,(i,))
        
        # Remove detection flag and oid from the sbid
        sbid_update = "UPDATE sbid SET detectionF = %s, detect_tar = NULL where id = %s"
        cur.execute(sbid_update,(False,sbid))

        # Get detection that lists this sbid
        if not runid:
            # Need to get detection id 
            sbid_query = "SELECT detect_runid from sbid where id = %s"
            cur.execute(sbid_query,(sbid,))
            runid = cur.fetchone()[0]
        
        # Remove reference in detect_run
        sbid_query = "SELECT SBIDS from detect_run where id = %s"
        cur.execute(sbid_query,(runid,))
        sbids = None
        try:
            sbids = cur.fetchone()[0]
            sbids.remove(sbid)
        except TypeError or IndexError:
            pass 
        # Check if sbids list now empty, in which case delete whole detection
        if not sbids:
            detect_stat = "DELETE from detect_run where id = %s"
            cur.execute(detect_stat,(runid,))
            print(f"    -- Deleted detection {runid}")
        else:
        # Update detection by removing sbid from row
            detect_stat = "UPDATE detect_run SET SBIDS = %s where id = %s"
            cur.execute(detect_stat,(sbids,runid))
            print(f"    -- Updated detection {runid}")
    return cur

def remove_sbid_from_spectral(cur,sbid,runid):
    
    # Get list of sbids for detection
    sbid_query = "SELECT SBIDS from spect_run where id = %s"
    cur.execute(sbid_query,(runid,))
    sbids = cur.fetchone()[0]
    sbids.remove(sbid)
    # Check if sbids list now empty, in which case delete whole detection
    if not sbids:
        detect_stat = "DELETE from spect_run where id = %s"
        cur.execute(detect_stat,(runid,))
        print(f"    -- Deleted spectral run {runid}")
    else:
    # Update detection by removing sbid from row
        detect_stat = "UPDATE spect_run SET SBIDS = %s where id = %s"
        cur.execute(detect_stat,(sbids,runid))
        print(f"    -- Updated spect_run {runid}")

    

def delete_detection(conn,runid):

    cur = get_cursor(conn)

    # Get the sbids that this detection run processed
    sbid_query = "select SBIDS from detect_run where id = %s"
    cur.execute(sbid_query,(runid,))
    sbids = cur.fetchone()[0]

    # Delete from the detect_run table
    delete_stat = "DELETE from detect_run where id = %s;"
    cur.execute(delete_stat,(runid,))

    # Process SBIDs
    for sbid in sbids:
        # Get the large object number for the detection tarball
        oid_query = "select detect_tar from sbid where id = %s"
        cur.execute(oid_query,(sbid,))
        lon = cur.fetchone()[0]
        # Delete it from large object table
        oid_delete = "SELECT lo_unlink(%s);"
        cur.execute(oid_delete,(lon,))
        # Reset runid, detection flag and tarball in table SBID
        sbid_reset = "UPDATE SBID SET detect_runid=NULL,detectionF = %s, detect_tar = NULL where id = %s"
        cur.execute(sbid_reset,(False,sbid))
    return cur

#########################################################################################################################
#########################################################################################################################


def createDataDir(data_path=DATA_DIR,sbids = SBIDS,component_dir=COMPONENT_PATH,plot_dir=SPECTRAL_PLOT_PATH,ascii_dir=SPECTRAL_ASCII_PATH,outputs=OUTPUT_PATH):

    sbidsDict = {"data_path":data_path}
    for sbid in sbids:
        sbidsDict[sbid] = {"components":[],"plots":[],"ascii":[]}
        component_path = f"{data_path}/{sbid}/{component_dir}"
        plots_path = f"{data_path}/{sbid}/{plot_dir}"
        ascii_path = f"{data_path}/{sbid}/{ascii_dir}"
        output_path = f"{data_path}/{sbid}/{outputs}"

        sbidsDict[sbid]["component_path"] = component_path
        sbidsDict[sbid]["plots_path"] = plots_path
        sbidsDict[sbid]["ascii_path"] = ascii_path
        sbidsDict[sbid]["output_path"] = output_path

        components = [f for f in os.listdir(component_path) if ".fits" in f]
        plots = [f for f in os.listdir(plots_path) if ".png" in f]
        asciis = [f for f in os.listdir(ascii_path) if ".dat" in f]
        try:
            output_files = [f for f in os.listdir(output_path)]
        except FileNotFoundError:
            # Presumably outputs haven't been created yet
            output_files = None

        sbidsDict[sbid]["components"] = components
        sbidsDict[sbid]["plots"] = plots
        sbidsDict[sbid]["ascii"] = asciis
        sbidsDict[sbid]["outputs"] = output_files
    return sbidsDict

###############################################

def check_sbids(cur,SBIDS,table="spect_run"):

    invalid_sbids = []
    if table == "spect_run":
        for sbid in SBIDS:
            select_query = "SELECT spectralF from SBID where id = %s;"
            cur.execute(select_query,(sbid,))
            result = cur.fetchall()
            if result and result[0][0]:
                print(f"SBID {sbid} already processed for spectral results!")
                invalid_sbids.append(sbid)
    elif table == "detect_run":
        for sbid in SBIDS:
            select_query = "SELECT detectionF from SBID where id = %s;"
            cur.execute(select_query,(sbid,))
            result = cur.fetchall()
            if result and result[0][0]:
                print(f"SBID {sbid} already processed for detection results!")
                invalid_sbids.append(sbid)

    return invalid_sbids

###############################################

def tar_dir(name,source_dir,recursive = False):
    """ By default, only tars up files, not subdirectories"""

    with tarfile.open(name, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir),recursive=recursive) 

###############################################
def add_spect_run(conn,SBIDS,config_dir,errlog,stdlog,dataDict,platform):

    cur = get_cursor(conn)

    # Check if any of the sbids have been entered before
    repeated_sbids = check_sbids(cur,SBIDS,table="spect_run")
    if repeated_sbids:
        print(f"*** SKIPPING sbids {repeated_sbids} from list {SBIDS}!!")
        SBIDS = list(set(repeated_sbids).symmetric_difference(set(SBIDS)))
    if not SBIDS:
        return cur

    # Add the log files
    errdata = ""
    with open(errlog,'r') as f:
        for line in f:
            line = line.replace("\"","'")
            errdata = errdata + line.strip() + "\n"
    stddata = ""
    with open(stdlog,'r') as f:
        for line in f:
            line = line.replace("\"","'")
            stddata = stddata + line.strip() + "\n"

    # Get current datetime and format for postgres
    spect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    # tar up the config files:
    config_tarball = f"{TMP_TAR_DIR}/spectral_config.tar.gz"
    tar_dir(config_tarball,config_dir)
    config_data = None
    with open(config_tarball,'rb') as f:
        config_data = f.read()
    
    # insert into spect_run table
    insert_query = "INSERT into spect_run(SBIDS,config_tar,errlog,stdlog,platform,date) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id;"
    cur.execute(insert_query,(SBIDS,psycopg2.Binary(config_data),errdata,stddata,platform,spect_date))
    runid = cur.fetchone()[0]
    print(f"Data inserted into table 'spect_run': runid = {runid}")
    # Add the processed SBIDS
    for sbid in SBIDS:
        # Check if sbid exits:
        cur.execute(f"SELECT count(*) from SBID where id = {sbid}")
        result = cur.fetchall()[0][0]
        if result ==0:
            add_sbid(conn,cur,sbid=sbid,spect_runid=runid,spectralF=True,dataDict=dataDict[sbid],datapath=dataDict["data_path"])
        else:
            print(f"ERROR: sbid {sbid} already in database!! Skipping ...")
    return cur

###############################################
def add_detect_run(conn,SBIDS,config_dir,errlog,stdlog,dataDict,platform,result_file,output_dir):

    cur = get_cursor(conn)

    # Check if any of the sbids have been entered before
    repeated_sbids = check_sbids(cur,SBIDS,table="detect_run")
    if repeated_sbids:
        print(f"*** SKIPPING sbids {repeated_sbids} from list {SBIDS}!!")
        SBIDS = list(set(repeated_sbids).symmetric_difference(set(SBIDS)))
    if not SBIDS:
        return cur

    # Add the log files
    errdata = ""
    with open(errlog,'r') as f:
        for line in f:
            line = line.replace("\"","'")
            errdata = errdata + line.strip() + "\n"
    stddata = ""
    with open(stdlog,'r') as f:
        for line in f:
            line = line.replace("\"","'")
            stddata = stddata + line.strip() + "\n"

    # Get current datetime and format for postgres
    detect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    # tar up the config files:
    config_tarball = f"{TMP_TAR_DIR}/detect_config.tar.gz"
    tar_dir(config_tarball,config_dir)
    config_data = None
    with open(config_tarball,'rb') as f:
        config_data = f.read()

    # Add the results file
    results = ""
    with open(result_file,'r') as f:
        for line in f:
            line = line.replace("\"","'")
            results = results + line.strip() + "\n"

    # insert into detect_run table
    insert_query = "INSERT into detect_run(SBIDS,config_tar,errlog,stdlog,result_filepath,results,platform,date) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;"
    cur.execute(insert_query,(SBIDS,psycopg2.Binary(config_data),errdata,stddata,result_file,results,platform,detect_date))
    runid = cur.fetchone()[0]
    print(f"Data inserted into table 'detect_run': runid = {runid}")

    # Add the processed SBIDS
    for sbid in SBIDS:
        # Check if sbid exists:
        cur.execute(f"SELECT count(*) from SBID where id = {sbid}")
        result = cur.fetchall()[0][0]
        if result ==1:
            update_sbid_detection(cur,sbid=sbid,runid=runid,detectionF=True,dataDict=dataDict[sbid],datapath=output_dir)
        else:
            print(f"ERROR: sbid {sbid} does not exist in database!! Skipping")
    return cur

###############################################
def add_sbid(conn,cur,sbid,spect_runid,spectralF=True,detectionF=False,dataDict={},datapath="./",quality="UNCERTAIN"):

    insert_query = "INSERT into SBID(id,spect_runid,spectralF,detectionF,ascii_tar,quality) VALUES (%s,%s,%s,%s,%s,%s);"
    run_table = "spect_run"
    runid = spect_runid
    # Check runid exists
    cur.execute(f"SELECT count(*) from {run_table} where id = {runid};")
    result = cur.fetchall()[0][0]
    if result == 0:
        print(f"ERROR: run id {runid} not found in table {run_table}; aborting")
        return
   
    # Create the tarball of ascii output files
    ascii_tarball = f"{TMP_TAR_DIR}/{sbid}_ascii_tarball.tar.gz"
    print(f"Creating tarball {ascii_tarball}")
    tar_dir(ascii_tarball,f"{dataDict['ascii_path']}")

    # Create a large object in the database:
    print("    -- loading to database")
    lob = conn.lobject(mode="wb", new_file=ascii_tarball)
    new_oid = lob.oid
    lob.close()
 
    cur.execute(insert_query, (sbid,runid,spectralF,detectionF,new_oid,quality))
    print(f"SBID {sbid} added to table 'SBID'")

    # Add the components and associated outputs plots of the sbid
    for comp in dataDict["components"]:
        # Find associated plot outputs
        component_index = comp.split("component_")[1].split(".fits")[0]
        plotfiles = [f for f in dataDict["plots"] if ("component_%s" % component_index) in f]
        plot_path = f"{dataDict['plots_path']}"
        add_component(cur,comp,sbid,plotfiles,plot_path,processState="spectral")

###############################################
def update_sbid_detection(cur,sbid,runid,detectionF,dataDict,datapath):

    # Create tarball of linefinder output files:
    output_tarball = f"{TMP_TAR_DIR}/{sbid}_linefinder_output.tar.gz"
    print(f"Creating tarball {output_tarball}")
    tar_dir(output_tarball,f"{sbid}/{LINEFINDER_OUTPUT_DIR}")

    # Create a large object in the database:
    print("    -- loading to database")
    lob = conn.lobject(mode="wb", new_file=output_tarball)
    new_oid = lob.oid
    lob.close()
 
    update_query = "UPDATE SBID SET detect_runid = %s, detectionF = %s, detect_tar = %s where id = %s;"
    cur.execute(update_query,(runid,detectionF,new_oid,sbid))
    print(f"sbid table updated with detection for sbid = {sbid}")

    # Update the component table with the detection
    for comp in dataDict["components"]:
        update_component_detection(cur,comp,processState="detection")
    

###############################################
def add_component(cur,comp,sbid,plot_list,plot_path,processState="spectral"):
    # Determine status
    #status = "NULL"
    #select_q = f"SELECT b.spectralF,b.detectionF from sbid a INNER JOIN run b on a.run_id = b.id where a.id = {sbid};"
    #cur.execute(select_q)
    #spectralF,detectionF = cur.fetchone()

    # Get current datetime and format for postgres
    spect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    detect_date = None

    # Read in plot images
    opd = f"{plot_path}/{[f for f in plot_list if 'opd' in f][0]}"
    flux = f"{plot_path}/{[f for f in plot_list if 'flux' in f][0]}"
    opddata = None
    fluxdata = None
    with open(opd,'rb') as f:
        opddata = f.read() 
    with open(flux,'rb') as f:
        fluxdata = f.read() 

    # add component
    insert_q = "INSERT into component VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s);"
    cur.execute(insert_q,(comp,sbid,processState,os.path.basename(opd),os.path.basename(flux),opddata,fluxdata,spect_date,detect_date))
    print(f"    Data inserted into table 'component': comp_id = {comp}")
    return

###############################################
def update_component_detection(cur,comp,processState):
    # Get current datetime and format for postgres
    detect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

    update_query = "UPDATE component SET processState = %s, detection_date = %s where comp_id = %s;"
    cur.execute(update_query,(processState,detect_date,comp))
    print(f"    Detection updated into table 'component': comp_id = {comp}")
    return

###############################################

def update_quality(conn,SBIDS,quality):

    cur = get_cursor(conn)
    
    update_query = "UPDATE SBID SET quality = %s where id = %s"
    for sbid in SBIDS:
        cur.execute(update_query,(quality,sbid))
    
    print(f"Set quality {quality} for sbids {SBIDS}")
    
    return cur

####################################################################################################################
####################################################################################################################

if __name__ == "__main__":

    starttime = time.time()
    conn = connect()

    # Change to data directory
    if DATA_DIR != "./":
        os.chdir(DATA_DIR)

    # Add run
    if RUN_TYPE == "spectral":
        dataDict = createDataDir()
        cur = add_spect_run(conn,SBIDS=SBIDS,
                        config_dir=SPECTRAL_CONFIG,
                        errlog=ERROR_LOG,
                        stdlog=STDOUT_LOG,
                        dataDict=dataDict,
                        platform=PLATFORM)
    elif RUN_TYPE == "detection":
        dataDict = createDataDir()
        cur = add_detect_run(conn,
                        SBIDS=SBIDS,
                        config_dir=LINEFINDER_CONFIG_DIR,
                        errlog=ERROR_LOG,
                        stdlog=STDOUT_LOG,
                        dataDict=dataDict,
                        platform=PLATFORM,
                        result_file=LINEFINDER_SUMMARY_FILE,
                        output_dir=LINEFINDER_OUTPUT_DIR)
    elif RUN_TYPE == "GOOD":
        cur = update_quality(conn,SBIDS=sbids,quality="GOOD")
    elif RUN_TYPE == "BAD":
        cur = update_quality(conn,SBIDS=sbids,quality="BAD")
    elif RUN_TYPE == "UNCERTAIN":
        cur = update_quality(conn,SBIDS=sbids,quality="UNCERTAIN")
    elif RUN_TYPE == "DELETESBIDS":
        cur = delete_sbids(conn,SBIDS)
    elif RUN_TYPE == "SBIDSPLOTONLY":
        cur = remove_sbids_from_detection(conn,SBIDS)
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"Job took {time.time()-starttime} sec for sbids {SBIDS}")


