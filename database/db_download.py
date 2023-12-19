
#######################################################################################
#       Script to download png files from flashdb database
#       GWHG @ CSIRO, July 2023
#
#       version 1.07 18/12/2023
#######################################################################################
import sys
import base64
import psycopg2
import re
from argparse import ArgumentParser, RawTextHelpFormatter

# default order for outputs from a query.
ORDERBY = "SBID"
#ORDERBY = "ID" # id is a proxy for date
MODE = "QUERY"
SBID = ""
VERSION = None
DIR = ""
BRIGHT = "-1"
LN_MEAN = "-1"
SQL = ""
#######################################################################################
def set_parser():
    # Set up the argument parser
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-m', '--mode',
            default=None,
            help='Specify run mode: PLOTS, ASCII, LINEFINDER, QUERY, SQL (default: %(default)s)')
    parser.add_argument('-s', '--sbid',
            default=None,
            help='Specify the sbid eg 11346 or 41050:1 for a specific version (use "-1" to get all sbids) (default: %(default)s)') 
    parser.add_argument('-S', '--sql_stat',
            default=None,
            help='SQL statement to pass to db (only with --mode SQL)') 
    parser.add_argument('-d', '--dir',
            default="/scratch/ja3/ger063/data/casda",
            help='Specify local directory to download to (default: %(default)s)')    
    parser.add_argument('-b', '--brightest',
            default="-1",
            help='in QUERY or PLOTS mode, enter number of top brightest sources to download (-1 for all). OR enter a filename that contains the source names to download, 1 per line (default: %(default)s)')
    parser.add_argument('-l', '--ln_mean',
            default="-1",
            help='in LINEFINDER mode, enter min ln_mean value for sources to download (-1 for all). OR enter a filename that contains the source names to download, 1 per line (default: %(default)s)')
    parser.add_argument('-f', '--flux',
            default=False,
            action='store_true',
            help='in PLOTS mode, get the flux plots instead of the opd ones (default: %(default)s)')
    args = parser.parse_args()
    return args,parser


def set_mode_and_values(args):

    global MODE, SBID, VERSION, DIR, BRIGHT, LN_MEAN, SQL

    MODE = args.mode.strip().upper()

    if MODE == "SQL":
        SQL = args.sql_stat.strip()
        return

    if MODE in ["QUERY","PLOTS"]:
        BRIGHT = args.brightest.strip()
    SBID = args.sbid
    if ":" in SBID:
        SBID = (int(args.sbid.split(":")[0]))
        VERSION = (int(args.sbid.split(":")[1]))
    else:
        SBID = int(args.sbid)
        VERSION = None
    DIR = args.dir.strip()
    if MODE == "LINEFINDER":
        LN_MEAN = args.ln_mean.strip()

    print("CLI overriding defaults")




#######################################################################################

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

##################################################################################################
##################################################################################################

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
##################################################################################################


def returnBrightestSources(names,number=None):

    # This will sort the sources by component number = relative brightness.
    # If 'number' is defined, it will only return that many component groups.
    # For example, number = 2 would return the sub-components of the top two source groups, say 
    # component_1a, component_1b and component_2a, component_2b and component_2c.

    namedir = {}

    for name in names:
        source_num = int(re.split('(\d+)',name)[-2])
        if source_num not in namedir.keys():
            namedir[int(source_num)] = [name]
        else:
            namedir[int(source_num)].append(name)

    keys = list(namedir.keys())
    keys.sort()
    sorted_sources = {i: namedir[i] for i in keys}
   
    if number: 
        n = int(number)
    else:
        n = len(sorted_sources)
    bright_sources = []
    for idx,(key,sources) in enumerate(sorted_sources.items()):
        if idx == n: 
            break
        sources.sort()
        for source in sources:
            bright_sources.append(source)
    return bright_sources,idx
##################################################################################################

def get_sql_result(conn,cur):

    query = SQL
    cur.execute(query)
    res = cur.fetchall()
    print("SQL statement returned:")
    for result in res:
        print(result)
    return

##################################################################################################

def query_db_for_sbid(cur,sbid):

    # This will return metadata stored in the db for a particular sbid
    if sbid != -1:  # Query a specific SBID
        query = "select sbid_num, version, spect_runid, id, detectionF, comment from sbid where sbid_num = %s"
        cur.execute(query,(sbid,))
    else:           # Query all SBIDS in the db. Order by SBID is default
        if ORDERBY == "SBID":
            query = "select sbid_num, version, spect_runid, id, detectionF, comment from sbid order by sbid_num;"
        elif ORDERBY in ["ID","DATE"]:
            query = "select sbid_num, version, spect_runid, id, detectionF, comment from sbid order by id;"
        cur.execute(query)
    res = cur.fetchall()
    title_str = "\nDATE\t\t\tSBID\tVERSION\tID\tTAG\t\t\tLINEFINDER RUN\t COMMENT"
    for i,result in enumerate(res):
        if i % 60 == 0:
            print(title_str)
        # get the run tags from the spect_run table
        spect_q = "select run_tag, date from spect_run where id = %s"
        cur.execute(spect_q,(result[2],))
        spect_tag,date = cur.fetchall()[0]
        print(f"{date}\t{result[0]}\t{result[1]}\t{result[3]}\t{spect_tag}\t\t\t{result[4]}\t{result[5]}")
    print()
    print(f"Number of records: {len(res)}")
    return

##################################################################################################

def write_lob(lobj,filename):
    with open(filename, 'wb') as f:
        while True:
            chunk = lobj.read(4096*4096)
            if not chunk:
                break
            f.write(chunk)  

##################################################################################################

def get_files_for_sbid(conn,cur,sbid,version):

    # This will return a tarball of ascii files stored for a particular sbid, 
    # or linefinder results files for an sbid, if available.

    # The directory for downloads:
    dir_download = DIR

    # The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    # then use the latest version

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)

    # Download tar of ascii files for the sbid
    if MODE == "ASCII":
        query = "select ascii_tar from sbid where id = %s"
        cur.execute(query,(sid,))
        oid = cur.fetchone()[0]
        print(f"Retrieving large object {oid} from db")
        loaded_lob = conn.lobject(oid=oid, mode="rb")
        name = f"{sbid}_{version}.tar.gz"
        # This may run out of mem for a very large object:
        #open(f"{dir_download}/{name}", 'wb').write(loaded_lob.read())
        # So use streaming function:
        write_lob(loaded_lob,f"{dir_download}/{name}")
        print(f"Downloaded tar of ascii files for {sbid}:{version}")

    elif MODE == "LINEFINDER":
        query = "select detectionF from sbid where id = %s"    
        cur.execute(query,(sid,))
        detect = cur.fetchone()[0]
        if not detect:
            print(f"No linefinder results available for sbid {sbid}:{version} !!")
            return
        query = "select detect_tar from sbid where id = %s"
        cur.execute(query,(sid,))
        oid = cur.fetchone()[0]
        if not oid:
            print(f"Linefinder was run, but no results stored in db for sbid {sbid}:{version} !!")
            return
        print(f"Retrieving large object {oid} from db")
        loaded_lob = conn.lobject(oid=oid, mode="rb")
        name = f"{sbid}_{version}.tar.gz"
        # This may run out of mem for a very large object:
        #open(f"{dir_download}/{name}", 'wb').write(loaded_lob.read())
        # So use streaming function:
        write_lob(loaded_lob,f"{dir_download}/{name}")
        print(f"Downloaded tar of linefinder result files for {sbid}:{version}")

    return



##################################################################################################

def get_plots_for_sbid(cur,sbid,version,get_flux=False):

    # This will return a tarball of spectral plots stored for a particular sbid
    # args[1] = directory for downloads
    # args[2] = The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    #           then use the latest version
    # args[3] = the top 'n' brightest sources only. A value of '-1' will download all
    #           Alternatively, supply a filename of a list of sources. Only those will be downloaded.
    # args[4] = plot type ('opd' or 'flux') to download


    # The directory for downloads:
    dir_download = DIR

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)

    # The component png's you want to download - ordered by brightness, eg '20' will 
    # download the top 20 components (and their 'a', 'b', 'c' etc varieties, so there will
    # be more than 20 files!)
    #
    try:
        num_sources = int(BRIGHT)
        source_list = None
    except ValueError:
        # This arg should be a filename:
        source_list_path = BRIGHT
        num_sources = -1
        source_list = []
        with open(source_list_path,'r') as f:
            for line in f.readlines():
                name = line.strip().split("component_")[1].split("_")[0]
                source_list.append("component_" + name)

    # The files type to download ("opd" or "flux")
    if get_flux:
        data_type = "flux"
    else:
        data_type = 'opd'
    if not sid:
        if version == 0:
            version = "any_version"
        print(f"sbid {sbid}:{version} is not in the database!")
        return

    print(f"For sbid = {sbid}:{version}")

    # Get the components in the database for the selected sbid:
    query = "select comp_id from component where sbid_id = %s"
    cur.execute(query,(sid,))
    comps = [comp[0] for comp in cur.fetchall()[1:]]

    # Re-order in descending brightness:
    if num_sources == -1:
        sources,number = returnBrightestSources(comps)
        if source_list: # specific sources requested
            explicit_sources = []
            for source in sources:
                for component_name in source_list:
                    if component_name in source:
                        explicit_sources.append(source)
            sources = explicit_sources
    else:
        sources,number = returnBrightestSources(comps,num_sources)
    # Get the image data for the component and write it to a local file:
    for idx,source in enumerate(sources):
        print(f"    {idx+1} of {len(sources)} : {source}")
        query = f"select {data_type}_image from component where comp_id = %s"
        cur.execute(query,(source,))
        data = cur.fetchone()
        if not data[0]:
            query = f"select fluxfilter from component where comp_id = %s and sbid_id = %s;"
            cur.execute(query,(source,sid))
            flux_filter = cur.fetchone()[0]
            print(f"plotfile for {source} missing from db. Flux cutoff was {flux_filter}")
            continue
        name = source.replace(".fits",f"_{data_type}.png")
        open(f"{dir_download}/{name}", 'wb').write(data[0])
    print(f"Downloaded {len(sources)} files from sbid {sbid}")

    return
##################################################################################################

def get_results_for_sbid(cur,sbid,version,verbose=False):

    # This will print out a table of linefinder output data for a given sbid
    # args[1] = 'linefinder'
    # args[2] = The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    #           then use the latest version
    # args[3] = ln_mean cutoff - only sources with an ln_mean() value larger than this will be shown
    #           Alternatively, supply a filename of a list of sources. Only those will be downloaded.

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)
    print(f"For {sbid}:{version} ...")
    # min val for ln_mean:
    try:
        ln_mean = float(LN_MEAN)
        source_list = None
    except ValueError: # a filename of sources was provided instead of ln_mean()
        ln_mean = 0.0
        source_list_path = LN_MEAN
        source_list = []
        with open(source_list_path,'r') as f:
            for line in f.readlines():
                name = line.strip().split("component_")[1].split("_")[0]
                source_list.append("component_" + name)

    # Get the relevant results file from the detect_run table:
    query = "select detect_runid from sbid where id = %s;"
    cur.execute(query,(sid,))
    res = cur.fetchone()[0]
    if not res:
        print(f"ERROR - {sbid} not in detection table")
        return 
    detect_runid = int(res)
    query = "select results from detect_run where id = %s;"
    cur.execute(query,(detect_runid,))
    result_data = cur.fetchone()[0].split('\n')

    # Get the list of relevant components and their values for this sbid from the component table
    if ln_mean == -1: # This means get all components, even if there is no value for ln_mean
        query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s order by ln_mean;")
        cur.execute(query,(sid,))
    else:
        query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s and ln_mean > %s order by ln_mean;")
        cur.execute(query,(sid,ln_mean))
    results = cur.fetchall()
    row_count = len(results)
    # Extract component id from results and get corresponding line from result_data
    results_dict = {}
    for result in results:
        comp_id = "component" + result[1].split("_component")[1].split(".")[0]
        results_dict[comp_id] = []
        found = False
        notf = 1
        for line in result_data:
            if comp_id in line:
                results_dict[comp_id].append(line)
                found = True
        if not found:
            print(f"{notf}: NOT FOUND! {comp_id}")
            notf += 1

    if verbose: # detailed output is saved to file
        f = open(f"{DIR}/{sbid}_{version}_linefinder_outputs.csv","w")
        # we want From component table - component_id, component_name, ra_hms_cont dec_dms_cont (both hms and degree), flux_peak, flux_int, has_siblings
        # From linefinder, all outputs except name: ModeNum x0_1_maxl dx_1_maxl y0_1_maxl abs_peakz_median abs_peakz_siglo abs_peakz_sighi abs_peakopd_median abs_peakopd_siglo abs_peakopd_sighi abs_intopd_median(km/s) abs_intopd_siglo(km/s) abs_intopd_sighi(km/s) abs_width_median(km/s) abs_width_siglo(km/s) abs_width_sighi(km/s) ln(B)_mean ln(B)_sigma chisq_mean chisq_sigma
        f.write("#Component_name,comp_id,modenum,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,x0_1_maxl,dx_1_maxl,y0_1_maxl,abs_peakz_median,abs_peakz_siglo,abs_peakz_sighi,abs_peakopd_median,abs_peakopd_siglo,abs_peakopd_sighi,abs_intopd_median(km/s),abs_intopd_siglo(km/s),abs_intopd_sighi(km/s),abs_width_median(km/s),abs_width_siglo(km/s),abs_width_sighi(km/s),ln(B)_mean,ln(B)_sigma,chisq_mean,chisq_sigma\n")
    print()
    print("component_name     comp_id   ra_hms_cont dec_dms_cont ra_deg_cont dec_deg mode ln_mean")
    print()
    for result in results:
        comp_id = "component" + result[1].split("_component")[1].split(".")[0]
        if source_list:
            row_count = len(source_list)
            for comp in source_list:
                if comp in result[1]:
                    if verbose:
                        linefinder_data = results_dict[comp]
                        for line in linefinder_data:
                            vals = line.split()
                            if float(vals[17]) > ln_mean:
                                f.write(f"{result[0]},{comp},{vals[1]},{result[2]},{result[3]},{result[4]},{result[5]},{result[6]},{result[7]},{vals[2]},{vals[3]},{vals[4]},{vals[5]},{vals[6]},{vals[7]},{vals[8]},{vals[9]},{vals[10]},{vals[11]},{vals[12]},{vals[13]},{vals[14]},{vals[15]},{vals[16]},{vals[17]},{vals[18]},{vals[19]},{vals[20]}\n")
                    # Summary to screen:
                    print(result[0],comp_id,result[2],result[3],result[4],result[5],result[9],result[10])
                    break
        else:
            if verbose:
                comp= "component" + result[1].split("_component")[1].split(".")[0]
                linefinder_data = results_dict[comp]
                for line in linefinder_data:
                    vals = line.split()
                    if float(vals[17]) > ln_mean:
                        f.write(f"{result[0]},{comp},{vals[1]},{result[2]},{result[3]},{result[4]},{result[5]},{result[6]},{result[7]},{vals[2]},{vals[3]},{vals[4]},{vals[5]},{vals[6]},{vals[7]},{vals[8]},{vals[9]},{vals[10]},{vals[11]},{vals[12]},{vals[13]},{vals[14]},{vals[15]},{vals[16]},{vals[17]},{vals[18]},{vals[19]},{vals[20]}\n")
            # Summary to screen:
            print(result[0],comp_id,result[2],result[3],result[4],result[5],result[9],result[10])
    print(f"{row_count} rows")
    if verbose:
        f.close()
    return

##################################################################################################
##################################################################################################

if __name__ == "__main__":

    conn = connect()
    args,parser = set_parser()
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    set_mode_and_values(args)
    cur = get_cursor(conn)
    # Query db for sbid metadata
    if MODE == "QUERY":
        query_db_for_sbid(cur,SBID)

    # Get plots for sbid
    elif MODE == "PLOTS":
        get_plots_for_sbid(cur,SBID,VERSION,args.flux)

    # Get tar of either ascii files or linefinder results
    elif MODE in ["ASCII","LINEFINDER"]:
        get_files_for_sbid(conn,cur,SBID,VERSION)

    # send a general SQL statement to the db
    elif MODE == "SQL":
        get_sql_result(conn,cur)

    # Get linfinder results for sbid
    if MODE == "LINEFINDER":
        get_results_for_sbid(cur,SBID,VERSION,verbose=True)

    
    cur.close()
    conn.close()

