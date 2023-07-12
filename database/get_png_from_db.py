
#######################################################################################
#       Script to download png files from flashdb database
#       GWHG @ CSIRO, July 2023
#
#       python3 get_png_from_db.py <directory to download to> <sbid> <top n brightest components>
#
#       eg "python3 get_png_from_db.py /home/ger063/tmp 43426 20"
#       will download brightest 20 sources from sbid 43426
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
    print("     -- add 'flux' to download the flux images. Default is opd images only")
    sys.exit()

##################################################################################################
##################################################################################################

if __name__ == "__main__":

    if len(sys.argv) < 4:
        usage()
    # The directory for downloads:
    dir_download = sys.argv[1]

    # The sbid you want to use
    sbid = int(sys.argv[2])

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


    conn = connect()
    cur = get_cursor(conn)
    query = "select id from SBID where sbid_num = %s"
    cur.execute(query,(sbid,))
    try:
        sid = int(cur.fetchall()[0][0])
    except IndexError:
        print(f"sbid {sbid} is not in the database!")
        sys.exit()
    print(f"For sbid = {sbid}")
    query = "select comp_id from component where sbid_id = %s"
    cur.execute(query,(sid,))
    comps = [comp[0] for comp in cur.fetchall()[1:]]
    if num_sources == -1:
        sources,number = returnBrightestSources(comps)
    else:
        sources,number = returnBrightestSources(comps,num_sources)
    for idx,source in enumerate(sources):
        print(f"    {idx+1} of {len(sources)} : {source}")
        query = f"select {img_type}_image from component where comp_id = %s"
        cur.execute(query,(source,))
        data = cur.fetchone()
        name = source.replace(".fits",f"_{img_type}.png")
        open(f"{dir_download}/{name}", 'wb').write(data[0])
    print(f"Downloaded {len(sources)} files from sbid {sbid}")
