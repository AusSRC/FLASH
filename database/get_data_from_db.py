
#######################################################################################
#       Script to download png files from flashdb database
#       GWHG @ CSIRO, July 2023
#
#       Usage 1:
#       python3 get_png_from_db.py <directory to download to> <sbid> <'n' top brightest components>
#
#       eg "python3 get_png_from_db.py /home/ger063/tmp 43426 20"
#       will download brightest 20 sources from the latest version of sbid 43426 in the db
#
#        "python3 get_png_from_db.py /home/ger063/tmp 43426:2 20"
#       will download the brightest 20 sources from version 2 of sbid 43426 in the db
#
#       To get ALL the sources, use "-1" for n
#
#       By default only the opd images are downloaded. To get the flux images, add "flux"
#
#       eg "python3 get_png_from_db.py /home/ger063/tmp 43426 20 flux"
#
#       Usage 2:
#       python3 get_png_from_db.py <directory to download to> <sbid> ascii
#
#       eg "python3 get_png_from_db.py /home/ger063/tmp 43426:2 ascii"
#       will download the tarball of ascii files stored for SBID 43426 version2
#
#       Usage 3:
#       python3 get_png_from_db.py <directory to download to> <sbid> linefinder
#
#       eg "python3 get_png_from_db.py /home/ger063/tmp 43426:2 linefinder"
#       will download the tarball of linefinder result files stored for SBID 43426 version2
#
#       Usage 4: Query mode:
#       python3 get_png_from_db.py 45833
#
#       will return metadata about SB45833 stored in the db (use '-1' to get all SBIDS)
#######################################################################################
import sys
import base64
import psycopg2
import re

# default order for outputs from a query.
ORDERBY = "SBID"
#ORDERBY = "ID" # id is a proxy for date
#ORDERBY = "DATE"
#######################################################################################

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
            # sbid doesn't exist
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

def query_db_for_sbid(cur,sbid):

    if sbid != -1:  # Query a specific SBID
        query = "select sbid_num, version, spect_runid, id, detectionF from sbid where sbid_num = %s"
        cur.execute(query,(sbid,))
    else:           # Query all SBIDS in the db. Order by SBID is default
        if ORDERBY == "SBID":
            query = "select sbid_num, version, spect_runid, id, detectionF from sbid order by sbid_num;"
        elif ORDERBY in ["ID","DATE"]:
            query = "select sbid_num, version, spect_runid, id, detectionF from sbid order by id;"
        cur.execute(query)
    res = cur.fetchall()
    title_str = "\nDATE\t\t\tSBID\tVERSION\tID\tTAG\t\t\tLINEFINDER RUN"
    print(title_str)
    for i,result in enumerate(res):
        if i % 60 == 0:
            print(title_str)
        # get the run tags from the spect_run table
        spect_q = "select run_tag, date from spect_run where id = %s"
        cur.execute(spect_q,(result[2],))
        spect_tag,date = cur.fetchall()[0]
        print(f"{date}\t{result[0]}\t{result[1]}\t{result[3]}\t{spect_tag}\t\t\t{result[4]}")
    return

##################################################################################################

def get_files_for_sbid(conn,cur,args):

    # The directory for downloads:
    dir_download = args[1]

    # The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    # then use the latest version
    version = None
    sbid_str = args[2]
    if ":" in sbid_str:
        sbid = int(sbid_str.split(":")[0])
        version = int(sbid_str.split(":")[1])
    else:
        sbid = int(sbid_str)

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)

    # Download tar of ascii files for the sbid
    if args[-1] == "ascii":
        query = "select ascii_tar from sbid where id = %s"
        cur.execute(query,(sid,))
        oid = cur.fetchone()[0]
        print(f"Retrieving large object {oid} from db")
        loaded_lob = conn.lobject(oid=oid, mode="rb")
        name = f"{sbid}_{version}.tar.gz"
        open(f"{dir_download}/{name}", 'wb').write(loaded_lob.read())
        print(f"Downloaded tar of ascii files for {sbid}:{version}")

    elif args[-1] == "linefinder":
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
        open(f"{dir_download}/{name}", 'wb').write(loaded_lob.read())
        print(f"Downloaded tar of linefinder result files for {sbid}:{version}")

    return



##################################################################################################

def get_plots_for_sbid(cur,args):

    # The directory for downloads:
    dir_download = args[1]

    # The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    # then use the latest version
    version = None
    sbid_str = args[2]
    if ":" in sbid_str:
        sbid = int(sbid_str.split(":")[0])
        version = int(sbid_str.split(":")[1])
    else:
        sbid = int(sbid_str)

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)

    # The component png's you want to download - ordered by brightness, eg '20' will 
    # download the top 20 components (and their 'a', 'b', 'c' etc varieties, so there will
    # be more than 20 files!)
    #
    num_sources = int(args[3])
    try:
        # The files type to download ("opd" or "flux")
        data_type = args[4]
    except IndexError: # default is to download opd files
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
    else:
        sources,number = returnBrightestSources(comps,num_sources)

    # Get the image data for the component and write it to a local file:
    for idx,source in enumerate(sources):
        print(f"    {idx+1} of {len(sources)} : {source}")
        query = f"select {data_type}_image from component where comp_id = %s"
        cur.execute(query,(source,))
        data = cur.fetchone()
        name = source.replace(".fits",f"_{data_type}.png")
        open(f"{dir_download}/{name}", 'wb').write(data[0])
    print(f"Downloaded {len(sources)} files from sbid {sbid}")

    return
##################################################################################################

def usage():
    print()
    print("USAGE 1 - Get spectral plot files stored for SBID:")
    print("python3 get_png_from_db.py <directory to download to> <sbid> <'n' top brightest components>")
    print("     eg python3 get_png_from_db.py /home/ger063/tmp 43426 20")
    print()
    print("     will download brightest 20 sources from latest version of sbid 43426")
    print("     For all sources, use '-1' for n")
    print()
    print("     python3 get_png_from_db.py /home/ger063/tmp 43426:2 20")
    print("     will download the brightest 20 sources from version 2 of sbid 43426 in the db")

    print("     -- add 'flux' to download the flux images. Default is opd images only")
    print()
    print("USAGE 2 - Get tar of ascii files for SBID:")
    print("python3 get_png_from_db.py <directory to download to> <sbid> ascii")
    print("     eg python3 get_png_from_db.py /home/ger063/tmp 43426:2 ascii")
    print()
    print("     will download the tarball of ascii files stored for SBID 43426 version2")
    print()
    print("USAGE 3 - Get tar of linefinder results files for SBID:")
    print("python3 get_png_from_db.py <directory to download to> <sbid> linefinder")
    print("     eg python3 get_png_from_db.py /home/ger063/tmp 43426:2 linefinder")
    print()
    print("     will download the tarball of linefinder result files stored for SBID 43426 version2")
    print()
     print("USAGE 4 - query db for sbid metatdata")
    print("python3 get_png_from_db.py 45833")
    print()
    print("     will return metadata on sbid, eg number of versions, tags etc")
    print("     (use '-1' to get ALL sbids)")
    sys.exit()

##################################################################################################
##################################################################################################

if __name__ == "__main__":

    if len(sys.argv) not in [2,3,4,5]:
        usage()

    conn = connect()
    cur = get_cursor(conn)
    
    # Query db for sbid metadata
    if len(sys.argv) == 2:
        try:
            sbid = int(sys.argv[1])
        except:
            usage()
        query_db_for_sbid(cur,sbid)

    # Get tar of either ascii files or linefinder results
    elif sys.argv[-1] in ["ascii","linefinder"]:
        get_files_for_sbid(conn,cur,sys.argv)

    # Get plots for sbid
    elif len(sys.argv) > 3:
        get_plots_for_sbid(cur,sys.argv)

    else:
        usage()

