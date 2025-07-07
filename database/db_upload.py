import os
import sys
import subprocess
import logging
import time
import glob
import datetime as dt
import os.path
import tarfile
import psycopg2
from argparse import ArgumentParser, RawTextHelpFormatter
import db_utils as dbu

#######################################################################################
#       Script to upload data to the FLASH database
#       GWHG @ CSIRO, July 2023
#
#       version 1.12 10/06/2025
##################################### USER SET VARIABLES ###################################################

# For the below variables, set to "" if they don't apply.

# The expected data layout is:
# DATA_DIR ---
#       catalogues - all CASDA catalogue data
#       logs       - all SLURM logs
#       SBID 1 ---
#                |
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

# These are the default values (overridden by command line args):

RUN_TYPE = ""
SBIDS = []
VERSIONS = []
DATA_DIR = os.environ["DATA"]
TMP_TAR_DIR = os.environ["TMPDIR"]
SPECTRAL_CONFIG_DIR = DATA_DIR + "/config1"
LINEFINDER_CONFIG_DIR = ""
ERROR_LOG = "err.log"
STDOUT_LOG = "out.log"
LINEFINDER_OUTPUT_DIR = ""
LINEFINDER_SUMMARY_FILE = "results.dat"
PLATFORM = "setonix.pawsey.org.au"
RUN_TAG = "FLASH survey 1"
SBID_COMMENT = ""
QUALITY = "UNCERTAIN"
PASSWD = ""
DBHOST = ""
DBPORT = ""


# These are the allowed command line overrides:

def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-m', '--mode',
            default=None,
            help='Specify run mode: SPECTRAL, DETECTION, INVERTED, COMP_RESULTS, QUALITY, COMMENT , POINTING, ASCII_UPLOAD (default: %(default)s)')
    parser.add_argument('-q', '--quality',
            default="UNCERTAIN",
            help='Set value - GOOD, BAD, "NOT VALIDATED" or UNCERTAIN (default: %(default)s)')
    parser.add_argument('-n', '--name_tag',
            default="FLASH Survey 1",
            help='name tag for this run (default: %(default)s)')
    parser.add_argument('-s', '--sbid_list',
            default=None,
            help='Specify the sbid list eg 11346,11348,41050:1,50332 (default: %(default)s)')  
    parser.add_argument('-d', '--parent_dir',
            default=DATA_DIR,
            help='Specify local directory to use (default: %(default)s)')    
    parser.add_argument('-ht', '--host',
            default="10.0.2.225",
            help='database host ip (default: %(default)s)')    
    parser.add_argument('-pt', '--port',
            default="5432",
            help='database host port (default: %(default)s)')    
    parser.add_argument('-t', '--tmp_dir',
            default=TMP_TAR_DIR,
            help='Specify local directory to use as tmp (default: %(default)s)')    
    parser.add_argument('-p', '--platform',
            default=PLATFORM,
            help='Specify the compute platform used (default: %(default)s)')    
    parser.add_argument('-pw', '--flashpw',
            default=None,
            help='Specify the password for login to FLASHDB (default: %(default)s)')    
    parser.add_argument('-cs', '--config_spectral',
            default=SPECTRAL_CONFIG_DIR,
            help='Specify spectral config directory used for processing (default: %(default)s)')
    parser.add_argument('-cl', '--config_linefinder',
            default=LINEFINDER_CONFIG_DIR,
            help='Specify linefinder config directory used for processing (default: %(default)s)')
    parser.add_argument('-o', '--detect_output',
            default="outputs",
            help='Specify sub-dir to hold linefinder output - relative to the sbid directory (default: %(default)s)')
    parser.add_argument('-C', '--comment',
            default=SBID_COMMENT,
            help='Comment to add to sbid(s) (default: %(default)s)')
    parser.add_argument('-l', '--logfile',
            default=STDOUT_LOG,
            help='Path to SLURM stdout logfile (default: %(default)s)')
    parser.add_argument('-e', '--errfile',
            default=ERROR_LOG,
            help='Path to SLURM stderr logfile (default: %(default)s)')
    parser.add_argument('-r', '--results',
            default=LINEFINDER_SUMMARY_FILE,
            help='Path to linefinder final results file  (default: %(default)s)')
    args = parser.parse_args()
    return args,parser

def set_mode_and_values(args):

    global RUN_TYPE,SBIDS,VERSIONS,RUN_TAG,DATA_DIR,TMP_TAR_DIR,ERROR_LOG,STDOUT_LOG,PLATFORM, SBID_COMMENT, PASSWD
    global SPECTRAL_CONFIG_DIR,LINEFINDER_CONFIG_DIR,LINEFINDER_OUTPUT_DIR,LINEFINDER_SUMMARY_FILE, QUALITY
    global DBHOST, DBPORT

    RUN_TYPE = args.mode.strip().upper()
    if RUN_TYPE == "QUALITY":
        RUN_TYPE = args.quality.strip().upper()
        if RUN_TYPE not in ['GOOD','BAD','UNCERTAIN']:
            print(f"Quality value {RUN_TYPE} illegal!!")
            return
    sbids = args.sbid_list.split(',')
    for sbid in sbids:
        if ":" in sbid:
            SBIDS.append(int(sbid.split(":")[0]))
            VERSIONS.append(int(sbid.split(":")[1]))
        else:
            SBIDS.append(int(sbid))
            VERSIONS.append(None)
    DATA_DIR = args.parent_dir.strip()
    TMP_TAR_DIR = args.tmp_dir.strip()
    s_config_dir = args.config_spectral.strip()
    l_config_dir = args.config_linefinder.strip()
    if RUN_TYPE in ["SPECTRAL","POINTING"]:
        SPECTRAL_CONFIG_DIR = s_config_dir
    elif RUN_TYPE == "DETECTION":
        LINEFINDER_CONFIG_DIR = l_config_dir
    ERROR_LOG = args.errfile.strip()
    STDOUT_LOG = args.logfile.strip()
    LINEFINDER_OUTPUT_DIR = args.detect_output.strip()
    LINEFINDER_SUMMARY_FILE = args.results.strip()
    PLATFORM = args.platform.strip()
    RUN_TAG = args.name_tag.strip()
    SBID_COMMENT = args.comment.strip()
    QUALITY = args.quality.strip()
    PASSWD = args.flashpw
    DBHOST = args.host.strip()
    DBPORT = args.port.strip()

    print("CLI overriding defaults")


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


#########################################################################################################################
############################## Uploading to DB ##########################################################################
#########################################################################################################################


def createDataDict(data_path=DATA_DIR,sbids = SBIDS,component_dir=COMPONENT_PATH,plot_dir=SPECTRAL_PLOT_PATH,ascii_dir=SPECTRAL_ASCII_PATH,outputs=OUTPUT_PATH,versions = VERSIONS):
    data_path = DATA_DIR
    sbids = SBIDS
    component_dir=COMPONENT_PATH
    plot_dir=SPECTRAL_PLOT_PATH
    ascii_dir=SPECTRAL_ASCII_PATH
    outputs=OUTPUT_PATH
    versions = VERSIONS
    pointing_field = "Unknown"
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
        if RUN_TYPE not in ["DETECTION","INVERTED"]:
            # Get the list of various files
            asciis = [f for f in os.listdir(ascii_path) if f.endswith(".dat")]
            components = [f for f in os.listdir(component_path) if f.endswith(".fits")]
            plots = [f for f in os.listdir(plots_path) if f.endswith(".png")]
        else:
            components = None
            plots = None
            asciis = None
        if RUN_TYPE not in ["DETECTION","INVERTED"]:
            # Get the name of the SourceSpectra tarball, so we can extract the pointing field value
            sspectraname = [f for f in os.listdir(f'{data_path}/{sbid}') if f.startswith("SourceSpectra-image")][0]
            try:
                pointing_field = "FLASH_" + sspectraname.split("FLASH_")[1].split(".")[0]
            except IndexError:
                # No field data in name
                pointing_field = "Unknown"
            print(f'{sbid} pointing field = {pointing_field}')
        try:
            output_files = [f for f in os.listdir(output_path)]
        except FileNotFoundError:
            # Presumably outputs haven't been created yet
            output_files = None

        sbidsDict[sbid]["components"] = components
        sbidsDict[sbid]["plots"] = plots
        sbidsDict[sbid]["ascii"] = asciis
        sbidsDict[sbid]["outputs"] = output_files
        sbidsDict[sbid]["pointing"] = pointing_field
    print("Data dictionary created",flush=True)
    return sbidsDict

###############################################

def check_sbids(cur,sbids,versions,table="spect_run"):

    invalid_sbids = []
    if table == "spect_run":
        for i,sbid in enumerate(sbids):
            ver = versions[i]
            select_query = "SELECT spectralF from SBID where sbid_num = %s and version = %s;"
            cur.execute(select_query,(sbid,ver))
            result = cur.fetchall()
            if result and result[0][0]:
                print(f"SBID {sbid} already processed for spectral results!")
                invalid_sbids.append(sbid)
    elif table == "detect_run":
        for i,sbid in enumerate(sbids):
            ver = versions[i]
            select_query = "SELECT detectionF from SBID where sbid_num = %s and version = %s;"
            cur.execute(select_query,(sbid,ver))
            result = cur.fetchall()
            if result and result[0][0]:
                print(f"SBID {sbid} already processed for detection results!")
                invalid_sbids.append(sbid)

    return invalid_sbids

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

def tar_dir(name,source_dir,pattern=None):
    """ Only tars up files, not subdirectories"""
    files = (file for file in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, file)))
    tar = tarfile.open(name, "w:gz")
    count =0
    for file in files:
        if not pattern:
            tar.add(f"{source_dir}/{file}", arcname = file)
            count += 1
        else:
            if isinstance(pattern,str):
                pattern = [pattern] 
            for pat in pattern:
                if pat in file:
                    tar.add(f"{source_dir}/{file}", arcname = file)
                    count += 1
    tar.close() 
    return count

###############################################

def tar_dir2(name,source_dir,pattern=None):

    cwd = os.getcwd()
    print(cwd,source_dir,name,pattern)
    if not pattern:
        print("No tar pattern")
        subprocess.check_call(f"cd {source_dir}; tar -zcvf {name} *",executable='/bin/bash',shell=True)
    else:
        print(f"tar pattern = {pattern}")
        # Use process substitution with tar -T option (works for GNU tar and bash)
        # Use 'subprocess' instead of 'os.system' because the latter doesn't use bash
        subprocess.check_call(f"cd {source_dir}; tar -zcvf {name} -T <(\ls -1 *{pattern}*)",executable='/bin/bash',shell=True)

    os.system(f"cd {cwd}")
 
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
    
###############################################
def add_spect_run(conn,sbids,config_dir,errlog,stdlog,dataDict,platform):

    cur = get_cursor(conn)
    print(f"Adding spectral run for sbids {sbids}",flush=True)
    # Add the log files
    errdata = ""
    if errlog:
        with open(errlog,'r') as f:
            for line in f:
                line = line.replace("\"","'")
                errdata = errdata + line.strip() + "\n"
    stddata = ""
    if stdlog:
        with open(stdlog,'r') as f:
            for line in f:
                line = line.replace("\"","'")
                stddata = stddata + line.strip() + "\n"

    # Get current datetime and format for postgres
    spect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    # tar up the config files:
    flux = None
    config_data = None
    insert_query = "INSERT into spect_run(SBIDS,errlog,stdlog,platform,date,run_tag) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id;"
    cur.execute(insert_query,(sbids,errdata,stddata,platform,spect_date,RUN_TAG))
    runid = cur.fetchone()[0]
    print(f"Data inserted into table 'spect_run': runid = {runid}",flush=True)
    # Add the processed SBIDS
    for sbid in sbids:
        # Check if sbid exists - if it does, add it with a version number += 1:
        sbid_id,version = get_max_sbid_version(cur,sbid)
        version += 1
        # tar up the config files:
        flux = None
        config_data = None
        if config_dir:
            config_tardir = f"{DATA_DIR}/{sbid}/{config_dir}"
            config_tarball = f"{TMP_TAR_DIR}/{sbid}_spectral_config.tar.gz"
            tar_dir(config_tarball,config_tardir,pattern="config.py")
            config_data = None
            with open(config_tarball,'rb') as f:
                config_data = f.read()
            print(f"Tarred config for {sbid}:{version}",flush=True)
            # Try to get the peak flux value in the config file:
            try:
                with open(f"{config_tardir}/config.py","r") as f:
                    config = f.readlines()
                for line in config:
                    if line.startswith("PEAKFLUX"):
                        flux = float(line.split("=")[1].split("#")[0])
                        print(f"Found flux cutoff at {flux} mJy",flush=True)
            except FileNotFoundError:
                print(f"Could not find config file {config_tardir}/config.py",flush=True)
        add_sbid(conn,cur,sbid=sbid,spect_runid=runid,spectralF=True,dataDict=dataDict[sbid],datapath=dataDict["data_path"],ver=version,config=config_data,flux=flux)
        print(f"Added sbid {sbid} and its components to db",flush=True)
    return cur

###############################################
def add_detect_run(conn,sbids,config_dir,dataDict,platform,result_file,output_dir,invertF,versions=None,errlog=None,stdlog=None):

    cur = get_cursor(conn)
    if not invertF:
        print(f"Adding detection run for sbids {sbids}",flush=True)
    else:
        print(f"Adding inverted spectra detection for sbids {sbids}", flush =True)
    # Check if any of the sbids have been entered before
    repeated_sbids = check_sbids(cur,sbids,versions,table="detect_run")
    if repeated_sbids and not invertF:
        print(f"*** SKIPPING sbids {repeated_sbids} from list {sbids}!!")
        sbids = list(set(repeated_sbids).symmetric_difference(set(sbids)))
    if not sbids:
        return cur

    # Add the log files
    errdata = ""
    if errlog:
        with open(errlog,'r') as f:
            for line in f:
                line = line.replace("\"","'")
                errdata = errdata + line.strip() + "\n"
    stddata = ""
    if stdlog:
        with open(stdlog,'r') as f:
            for line in f:
                line = line.replace("\"","'")
                stddata = stddata + line.strip() + "\n"

    # Get current datetime and format for postgres
    detect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    # insert into detect_run table
    insert_query = "INSERT into detect_run(SBIDS,errlog,stdlog,result_filepath,platform,date,run_tag,invertF) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;"
    cur.execute(insert_query,(sbids,errdata,stddata,result_file,platform,detect_date,RUN_TAG,invertF))
    runid = cur.fetchone()[0]
    print(f"Data inserted into table 'detect_run': runid = {runid}",flush=True)

    # Add each of the processed SBIDS
    for i,sbid in enumerate(sbids):
        if not DATA_DIR in result_file:
            result_file = f"{DATA_DIR}/{sbid}/{output_dir}/{result_file}"
        # Create the results file
        results = ""
        with open(result_file,'r') as f:
            for line in f:
                line = line.replace("\"","'")
                results = results + line.strip() + "\n"

        if not DATA_DIR in config_dir:
            config_dir = f"{DATA_DIR}/{sbid}/{config_dir}"
        version = versions[i]
        sbid_id = None
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # tar up the config files:
        config_tarball = f"{TMP_TAR_DIR}/{sbid}_detect_config.tar.gz"
        config_data = None
        try:
            tar_dir(config_tarball,config_dir,pattern=".")
            print(f"{config_tarball} created")
            with open(config_tarball,'rb') as f:
                config_data = f.read()
        except FileNotFoundError:
            print(f"Config dir {config_dir} not found!!")
        
        # Update the sbid if it exists:
        if sbid_id:
            update_sbid_detection(cur,sbid=sbid,sbid_id=sbid_id,runid=runid,detectionF=True,dataDict=dataDict[sbid],datapath=output_dir,ver=version,config=config_data,results=results,invertF=invertF)

        else:
            print(f"ERROR: sbid:version {sbid}:{version} does not exist in database!! Skipping")

        # Process the results file against each component
        sbid_results = results.splitlines()
        max_ln_mean = 0
        #last_name = sbid_results[1].split()[0].rsplit("_",1)[0]
        last_name = ""
        for line in sbid_results[1:]:
            vals = line.split()
            name = vals[0].rsplit("_",1)[0]
            line_sbid = int(name.split("_")[0][2:])
            ln_mean = float(vals[17])
            mode_num = int(vals[1])
            if line_sbid != int(sbid):
                continue

            if name != last_name:
                max_ln_mean = 0
            if ln_mean > max_ln_mean: # we only store the modenum version with the largest ln_mean in component table
                if invertF:
                    update = "update component set invert_mode_num = %s, invert_ln_mean = %s where comp_id like %s and sbid_id = %s;"
                else:
                    update = "update component set mode_num = %s, ln_mean = %s where comp_id like %s and sbid_id = %s;"
                like= '%{}%'.format(name)
                cur.execute(update,(mode_num,ln_mean,like,sbid_id))
                max_ln_mean = ln_mean  
 
            last_name = name
    return cur

###############################################
def upload_ascii_tarball(conn,sbids,versions,dataDictMain):

    cur = get_cursor(conn)
    for i,sbid in enumerate(sbids):
        dataDict = dataDictMain[sbid]
        version = versions[i]
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Create the tarball of ascii output files
        ascii_tarball = f"{TMP_TAR_DIR}/{sbid}_ascii_tarball.tar.gz"
        if os.path.isfile(ascii_tarball):
            print(f"Using existing {ascii_tarball}",flush=True)
        else:
            print(f"Creating tarball {ascii_tarball}")
            tar_dir(ascii_tarball,f"{dataDict['ascii_path']}")
        # Delete old large object of ascii files
        oid_query = "select ascii_tar from sbid where id = %s;"
        cur.execute(oid_query,(sbid_id,))
        lon = cur.fetchone()
        print("\tDone!\nNOT deleting old ascii LOB. Use 'vacuumlo -U flash flashdb' after",flush=True)
        #oid_delete = "SELECT lo_unlink(%s);"
        #try:
        #    for i in lon:
        #        cur.execute(oid_delete,(i,))
        #    print("\tDeleted ascii LOB",flush=True)
        #except TypeError:
        #    print(f"ascii LOB for {sbid}:{version} not found")
            
        # Create a new large object in the database:
        print("    -- loading to database")
        lob = create_large_object(conn,ascii_tarball)
        new_oid = lob.oid
        lob.close()
        print("    -- Done!",flush=True)

        # Update oid in sbid table
        update_query = "update sbid set ascii_tar = %s where id = %s;"
        cur.execute(update_query,(new_oid,sbid_id))
    return cur
             

###############################################
def add_sbid(conn,cur,sbid,spect_runid,spectralF=True,detectionF=False,dataDict={},datapath="./",ver=1,config=None,flux=None):

    quality = QUALITY
    pointing_field = dataDict['pointing']
    insert_query = "INSERT into SBID(sbid_num,spect_runid,spectralF,detectionF,spectral_config_tar,ascii_tar,quality,version,pointing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);"
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
    if os.path.isfile(ascii_tarball):
        print(f"Using existing {ascii_tarball}",flush=True)
    else:
        print(f"Creating tarball {ascii_tarball}")
        tar_dir(ascii_tarball,f"{dataDict['ascii_path']}")

    # Create a large object in the database:
    print("    -- loading to database",flush=True)
    lob = create_large_object(conn,ascii_tarball)
    #lob = conn.lobject(oid=0,mode="wb", new_file=ascii_tarball)
    new_oid = lob.oid
    lob.close()
     
    cur.execute(insert_query, (sbid,runid,spectralF,detectionF,psycopg2.Binary(config),new_oid,quality,ver,pointing_field))
    # Get the generated id of the sbid just added:
    cur.execute(f"SELECT id from SBID where sbid_num = {sbid} and version = {ver};")
    sbid_id = int(cur.fetchall()[0][0])
    print(f"SBID {sbid_id}:{sbid} added to table 'SBID'",flush=True)

    # Add the components and associated outputs plots of the sbid
    for comp in dataDict["components"]:
        # Find associated plot outputs
        component_index = comp.split("component_")[1].split(".fits")[0]
        plotfiles = [f for f in dataDict["plots"] if ("component_%s" % component_index) in f]
        plot_path = f"{dataDict['plots_path']}"
        cur = add_component(cur,comp,sbid_id,plotfiles,plot_path,processState="spectral",fluxcutoff=flux)

###############################################
def add_sbid_comment(conn,sbid,comment,ver=None):

    cur = get_cursor(conn)
    if comment == "":
        return cur
    sbid_id,ver = get_max_sbid_version(cur,sbid,ver)
    date = dt.datetime.now()
    date_str = f"{date.day}/{date.month}/{date.year}"

    # Get any existing comment
    old_comment = ""
    get_comment = "select comment from sbid where id = %s"
    cur.execute(get_comment,(sbid_id,))
    try:
        old_comment = cur.fetchall()[0][0]
    except IndexError:
        print("Error getting previous comment")
    if not old_comment:
        old_comment = ""
    print(f"Previous comment was: {old_comment}") 
    comment = old_comment + "[" + date_str + ": " + comment + "]"

    add_query = "update sbid set comment = %s where id = %s"
    cur.execute(add_query,(comment,sbid_id))
    print(f"Comment added to SB{sbid}")
    return cur

###############################################
def add_sbid_pointing(conn,sbid,dataDict,cur=None,ver=None):

    if not cur:
        cur = get_cursor(conn)
    sbid_id,ver = get_max_sbid_version(cur,sbid,ver)
    pointing = dataDict["pointing"]
    if pointing == "":
        return cur
    add_query = "update sbid set pointing = %s where id = %s"
    cur.execute(add_query,(pointing,sbid_id))
    print(f"Pointing field {pointing} added to SB{sbid}")
    return cur
###############################################
def add_component_results(conn,sbids,result_file,output_dir,versions=None):

    cur = get_cursor(conn)
    print("Adding LINEFINDER results to components")
    # Get the results file
    results = ""
    with open(result_file,'r') as f:
        for line in f:
            line = line.replace("\"","'")
            results = results + line.strip() + "\n"

    for i,sbid in enumerate(sbids):
        version = versions[i]
        sbid_id = None
        sbid_id,version = get_max_sbid_version(cur,sbid,version)
        # Process the results file against each component
        sbid_results = results.splitlines()
        max_ln_mean = 0
        last_name = ""
        for line in sbid_results[1:]:
            vals = line.split()
            name = vals[0].rsplit("_",1)[0]
            line_sbid = int(name.split("_")[0][2:])
            ln_mean = float(vals[17])
            mode_num = int(vals[1])
            if line_sbid != int(sbid):
                continue

            if name != last_name:
                max_ln_mean = 0
            if ln_mean > max_ln_mean: # we only store the modenum version with the largest ln_mean in component table
                update = "update component set mode_num = %s, ln_mean = %s where comp_id like %s and sbid_id = %s;"
                like= '%{}%'.format(name)
                cur.execute(update,(mode_num,ln_mean,like,sbid_id))
                max_ln_mean = ln_mean  
 
            last_name = name
    return cur

    

###############################################
def add_detect_comment(conn,sbid,comment,ver=None):

    cur = get_cursor(conn)
    if comment == "":
        return cur
    sbid_id,ver = get_max_sbid_version(cur,sbid,ver)
    date = dt.datetime.now()
    date_str = f"{date.day}/{date.month}/{date.year}"

    # Get any existing comment
    old_comment = ""
    get_comment = "select comment from sbid where id = %s"
    cur.execute(get_comment,(sbid_id,))
    try:
        old_comment = cur.fetchall()[0][0]
    except IndexError:
        print("Error getting previous comment")
    if not old_comment:
        old_comment = ""
    print(f"Previous comment was: {old_comment}") 
    comment = old_comment + "[" + date_str + ": " + comment + "]"

    add_query = "update sbid set comment = %s where id = %s"
    cur.execute(add_query,(comment,sbid_id))
    print(f"Comment added to SB{sbid}")
    return cur

###############################################
def update_sbid_detection(cur,sbid,sbid_id,runid,detectionF,dataDict,datapath,ver,config,results,invertF=False):

    # Create tarball of linefinder output files:
    output_tarball = f"{TMP_TAR_DIR}/{sbid}_linefinder_output.tar.gz"
    if not os.path.isfile(output_tarball):
        print(f"Creating tarball {output_tarball}")
        count = tar_dir(output_tarball,f"{sbid}/{LINEFINDER_OUTPUT_DIR}",pattern=["stats.dat","result",".pdf"])
        print(f"   -- {count} files in tarball")
    with open(output_tarball,'rb') as f:
        detect_data = f.read()
    print(f"detect_data = {len(detect_data)}",flush=True)
    # Create a large object in the database:
    print("    -- loading to database")
    lob = create_large_object(conn,output_tarball)
    #lob = conn.lobject(oid=0,mode="wb", new_file=ascii_tarball)
    new_oid = lob.oid
    lob.close()

    if invertF:
        update_query = "UPDATE SBID SET invert_detect_runid = %s, invert_detectionF = %s, invert_detect_results = %s, detect_config_tar = %s, invert_results = %s where id = %s;"
        cur.execute(update_query,(runid,detectionF,psycopg2.Binary(detect_data),psycopg2.Binary(config),results,sbid_id))
    else:
        # We add both 'detect_data' byte array and the lob, for redundancy
        update_query = "UPDATE SBID SET detect_runid = %s, detectionF = %s, detect_results = %s, detect_tar = %s , detect_config_tar = %s, results = %s where id = %s;"
        cur.execute(update_query,(runid,detectionF,psycopg2.Binary(detect_data),new_oid,psycopg2.Binary(config),results,sbid_id))
    print(f"sbid table updated with detection for sbid = {sbid}, version {ver}")

    # Update the component table with the detection, first find the components (sources) used
    components = []
    sources = glob.glob(f"{DATA_DIR}/{sbid}/outputs/*{sbid}*opd_spectline_stats.dat")
    #for comp in dataDict["ascii"]:
    for source in sources:
        comp_number = source.split("component_")[1].split("_")[0]
        comp = f"SB{sbid}_component_{comp_number}_opd.dat"
        if invertF:
            update_component_detection(cur,comp,sbid_id,processState="inverted_detection")
        else:
            update_component_detection(cur,comp,sbid_id,processState="detection")

###############################################
def add_component(cur,comp,sbid_id,plot_list,plot_path,processState="spectral",fluxcutoff=None):
    # Determine status

    # Get current datetime and format for postgres
    spect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    detect_date = None

    # Read in plot images
    opddata = None
    fluxdata = None
    opd = ""
    flux = ""
    try:
        opd = f"{plot_path}/{[f for f in plot_list if 'opd' in f][0]}"
        flux = f"{plot_path}/{[f for f in plot_list if 'flux' in f][0]}"
        with open(opd,'rb') as f:
            opddata = f.read() 
        with open(flux,'rb') as f:
            fluxdata = f.read() 
    except IndexError:
        print(f"WARNING: plot data missing for {comp} - skipping",flush=True)
        return cur
       
    # check if component exists in db:
    query = "select count(*) from component where comp_id = %s and opd_image is not null"
    cur.execute(query,(comp,))
    res = int(cur.fetchone()[0])
    if res != 0:
        print(f"component {comp} exists in db - skipping!",flush=True)
        return cur

    # Generate short-form name:
    shortname = comp.split("component_")[1].split(".fits")[0] 
    # add component
    insert_q = "INSERT into component(comp_id,shortname,processState,opd_plotname,flux_plotname,opd_image,flux_image,spectral_date,detection_date,sbid_id,fluxfilter) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
    cur.execute(insert_q,(comp,shortname,processState,os.path.basename(opd),os.path.basename(flux),opddata,fluxdata,spect_date,detect_date,sbid_id,fluxcutoff))
    # Get id of just-added component:
    cur.execute(f"select id from component where comp_id = '{comp}' and sbid_id = {sbid_id};")
    id = int(cur.fetchall()[0][0])

    print(f"    Data inserted into table 'component': id = {id}, comp_id = {comp}",flush=True)
    return cur

###############################################
def update_component_detection(cur,comp,sbid_id,processState):
    # Get current datetime and format for postgres
    detect_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

    # change the component name into the right format
    if not comp.startswith("spec_"):
        comp = "spec_" + comp
    comp.replace(".dat",".fits")
    if processState == "inverted_detection":
        update_query = "UPDATE component SET processState = %s, invert_detection_date = %s where comp_id = %s and sbid_id = %s;"
    else:
        update_query = "UPDATE component SET processState = %s, detection_date = %s where comp_id = %s and sbid_id = %s;"
    cur.execute(update_query,(processState,detect_date,comp,sbid_id))
    print(f"    Detection updated into table 'component': comp_id = {comp}, sbid_id = {sbid_id}")
    return

###############################################

def update_quality(conn,SBIDS,quality,version=None):

    cur = get_cursor(conn)
    update_query = "UPDATE SBID SET quality = %s where sbid_num = %s and version = %s"
    for sbid in SBIDS:
        if not version:
            sbid_id,version = get_max_sbid_version(cur,sbid)
        cur.execute(update_query,(quality,sbid,version))
    
    print(f"Set quality {quality} for sbids {SBIDS}")
    
    return cur

####################################################################################################################
####################################################################################################################

if __name__ == "__main__":

    ADD_CAT = True
    starttime = time.time()
    args,parser = set_parser()
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    set_mode_and_values(args)
    conn = connect()

    # Add run
    if RUN_TYPE == "SPECTRAL":
        print("Starting SPECTRAL upload")
        # Change to data directory
        if DATA_DIR != "./":
            os.chdir(DATA_DIR)
        dataDict = createDataDict()
        cur = add_spect_run(conn,sbids=SBIDS,
                        config_dir=SPECTRAL_CONFIG_DIR,
                        errlog=ERROR_LOG,
                        stdlog=STDOUT_LOG,
                        dataDict=dataDict,
                        platform=PLATFORM)
        conn.commit()
        cur.close()
        if ADD_CAT:
            cat_dir = f"{DATA_DIR}/catalogues"
            for i,sbid in enumerate(SBIDS):
                ver = VERSIONS[i]
                cur = dbu.add_sbid_catalogue(conn,sbid,cat_dir,ver)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "COMPONENTS":
        # Change to data directory
        if DATA_DIR != "./":
            os.chdir(DATA_DIR)
        dataDict = createDataDict()
        cur = get_cursor(conn)
        for sbid in SBIDS:
            cat_dir = f"{DATA_DIR}/catalogues"
            sbid_id,version = get_max_sbid_version(cur,sbid)
            datadict = dataDict[sbid]
            len_comp = len(datadict['components'])
            for i,comp in enumerate(datadict['components']):
                component_index = comp.split("component_")[1].split(".fits")[0]
                plotfiles = [f for f in datadict["plots"] if ("component_%s" % component_index) in f]
                plot_path = f"{datadict['plots_path']}"
                cur = add_component(cur,comp,sbid_id,plotfiles,plot_path,processState="spectral",fluxcutoff=0.03)
                cur = dbu.add_sbid_catalogue(conn,sbid,cat_dir,version)
                print(f"{i+1} from total to process: {len_comp}",flush=True)
                if i % 20 == 0:
                    conn.commit()
        conn.commit()
        cur.close()
        conn.close()
        
    elif RUN_TYPE == "ASCII_UPLOAD":
        print("Starting ASCII upload")
        # Change to data directory
        if DATA_DIR != "./":
            os.chdir(DATA_DIR)
        dataDict = createDataDict()
        cur = upload_ascii_tarball(conn,sbids=SBIDS,versions=VERSIONS,dataDictMain=dataDict)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "DETECTION" or RUN_TYPE == "INVERTED":
        print("Starting DETECTION upload")
        inverted = False
        if RUN_TYPE == "INVERTED":
            inverted = True
        # Change to data directory
        if DATA_DIR != "./":
            os.chdir(DATA_DIR)
        print(f'main: DATA_DIR = {DATA_DIR}')
        dataDict = createDataDict(data_path=DATA_DIR)
        cur = add_detect_run(conn,
                        sbids=SBIDS,
                        config_dir=LINEFINDER_CONFIG_DIR,
                        dataDict=dataDict,
                        platform=PLATFORM,
                        result_file=LINEFINDER_SUMMARY_FILE,
                        output_dir=LINEFINDER_OUTPUT_DIR,
                        invertF = inverted,
                        versions=VERSIONS)
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "COMP_RESULTS":
        # Change to data directory
        if DATA_DIR != "./":
            os.chdir(DATA_DIR)
        print(f'main: DATA_DIR = {DATA_DIR}')
        dataDict = createDataDict(data_path=DATA_DIR)
        cur = add_component_results(conn,
                        sbids=SBIDS,
                        result_file=LINEFINDER_SUMMARY_FILE,
                        output_dir=LINEFINDER_OUTPUT_DIR,
                        versions=VERSIONS)
        conn.commit()
        cur.close()
        conn.close()

    elif RUN_TYPE == "GOOD":
        cur = update_quality(conn,SBIDS=SBIDS,quality="GOOD")
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "BAD":
        cur = update_quality(conn,SBIDS=SBIDS,quality="BAD")
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "UNCERTAIN":
        cur = update_quality(conn,SBIDS=SBIDS,quality="UNCERTAIN")
        conn.commit()
        cur.close()
        conn.close()
    elif RUN_TYPE == "POINTING":
        print("Adding Pointing field to sbids")
        dataDict = createDataDict(data_path=DATA_DIR)
        for i,sbid in enumerate(SBIDS):
            ver = VERSIONS[i]
            cur = add_sbid_pointing(conn,sbid,dataDict[sbid],ver)
            conn.commit()
            cur.close()
        conn.close()
        
    if args.comment.strip() != "":
        conn = connect()
        print("Adding comment to sbid")
        comment = args.comment.strip()
        for i,sbid in enumerate(SBIDS):
            ver = VERSIONS[i]
            if RUN_TYPE in ["SPECTRAL","COMMENT","ASCII_UPLOAD"]:
                cur = add_sbid_comment(conn,sbid,comment,ver)
            else:        
                cur = add_detect_comment(conn,sbid,comment,ver)

        conn.commit()
        cur.close()
        conn.close()
    print(f"Job took {time.time()-starttime} sec for sbids {SBIDS}")


