import os
import sys
import logging
import time

import psycopg2

def connect(db="flashdb",user="flash",host="localhost",password="aussrc"):

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

def add_run(cur,spectralF=False,detectionF=False,SBIDS=[],logid=None):
    if logid:
        # Check the logs have been added
        cur.execute(f"SELECT count(*) from logs where logid = {logid}")
        result = cur.fetchall()[0][0]
        if result == 0:
            print("ERROR: log id not found in Table 'logs': aborting")
            return
    insert_query = f"INSERT into run(spectralF,detectionF,SBIDS,logid) VALUES({spectralF},{detectionF},ARRAY {SBIDS},{logid});"
    cur.execute(insert_query)
    print("Data inserted into tabe 'run'")

if __name__ == "__main__":

    #conn = connect(host="146.118.64.208")
    conn = connect()
    cur = get_cursor(conn)

    # Test
    cur.execute("SELECT version();")
    result = cur.fetchone()
    print(result)

    add_run(cur,spectralF=True,SBIDS=[33256,33257],logid="1")
    


    conn.commit()
    cur.close()
    conn.close()



#cobj.execute("INSERT INTO logs(err_log, std_log) VALUES(pg_read_binary_file('/home/ubuntu/plot_spectra_err736.log'),pg_read_binary_file('/home/ubuntu/plot_spectra_out736.log'));")
