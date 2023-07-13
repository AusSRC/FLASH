
#######################################################################################
#       Script to download png files from flashdb database
#       GWHG @ CSIRO, July 2023
#
#       python3 get_png_from_db.py <directory to download to> <sbid> <top n brightest components>
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
#######################################################################################
import sys
import base64
import psycopg2
import re

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

def get_max_sbid_version(cur,sbid_num,version=None):

    # If version=None, returns the sbid_id:version for the latest version number of the sbid_num in the SBID table
    # Otherwise returns the sbid_id:version for the sbid_num and version combination provided
    # If the sbid_num doesn't exist, returns None:0

    if version:
        query = "select id from sbid where sbid_num = %s and version = %s;"
        cur.execute(query,(sbid_num,version))
        sbid_id = int(cur.fetchall()[0][0])
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

def usage():
    print()
    print("USAGE:")
    print("python3 get_png_from_db.py <directory to download to> <sbid> <top n brightest components>")
    print("     eg python3 get_png_from_db.py /home/ger063/tmp 43426 20")
    print()
    print("     will download brightest 20 sources from sbid 43426")
    print()
    print("     python3 get_png_from_db.py /home/ger063/tmp 43426:2 20")
    print("     will download the brightest 20 sources from version 2 of sbid 43426 in the db")

    print("     -- add 'flux' to download the flux images. Default is opd images only")
    sys.exit()

##################################################################################################
##################################################################################################

if __name__ == "__main__":

    conn = connect()
    cur = get_cursor(conn)

    if len(sys.argv) < 4:
        usage()
    # The directory for downloads:
    dir_download = sys.argv[1]

    # The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    # then use the latest version
    version = None
    sbid_str = sys.argv[2]
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
    num_sources = int(sys.argv[3])
    try:
        # The image type to download ("opd" or "flux")
        img_type = sys.argv[4]
    except IndexError:
        img_type = 'opd'

    if not sid:
        print(f"sbid {sbid}:{version} is not in the database!")
        sys.exit()
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
        query = f"select {img_type}_image from component where comp_id = %s"
        cur.execute(query,(source,))
        data = cur.fetchone()
        name = source.replace(".fits",f"_{img_type}.png")
        open(f"{dir_download}/{name}", 'wb').write(data[0])
    print(f"Downloaded {len(sources)} files from sbid {sbid}")
