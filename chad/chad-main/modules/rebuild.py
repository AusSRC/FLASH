#!/usr/bin/python
# Module to delete and rebuild CHAD database with just master catalogue.
# L. Canepa, adapted from V.A. Moss
__author__ = "L. Canepa"
__version__ = "0.2"

import glob
import requests
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from astropy.io import ascii
from . import functions as f

passwd = "aussrc" # Update with password for user postgres
conn = None
try:
    conn = psycopg2.connect("host=localhost dbname=chad user=postgres password=%s" % passwd)
except:
    conn = psycopg2.connect("host=localhost dbname=postgres user=postgres password=%s" % passwd)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()


def rebuild():
    
    # Connect to the host to rebuild database
    conn = psycopg2.connect("host=localhost dbname=postgres user=postgres password=%s" % passwd)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS chad;")
    conn.commit()
    cur.execute("CREATE DATABASE chad;")
    conn = psycopg2.connect("host=localhost dbname=chad user=postgres password=%s" % passwd)
    cur = conn.cursor()
    
    # Add the base catalogue to CHAD
    print("Adding base catalogue to CHAD...")
    add_master(cur, name = "racs") # If master table is something different, change name
    conn.commit()        

    # Add the status of the surveys from the Google spreadsheet
    add_survey_status(cur,name = "survey_status")

    print("Done rebuild")

    return
    
# Add the master catalogue (RACS) to the database
def add_master(cur, name = "racs"):
    
    # Get both catalogue types into the database
    for cattype in ["component", "island"]:
        table = name+"_"+cattype
        cats = glob.glob("input/%s*.csv" % table)
        
        # Loop over the input tables
        for i, cat in enumerate(cats):
            print("Reading in Table %s..." % cat)
            d = ascii.read(cat, format="csv")
            
            # Generate header and create table for just the first component/island catalogue
            if i == 0:
                header, _ = f.generate_header(d, table)
                #print(header)
                # Create the table
                cur.execute(header)

            # Insert rows into the table
            print("Inserting rows...")
            for i in range(0, len(d)):
                print(f"{i}/{len(d)}", end = "\r")
                if i == len(d) - 1: # leave the last line printed
                    print(f"{len(d)}/{len(d)}")
                
                # Get the values to insert
                values = ", ".join(['%s'] * len(d[i]))

                query = "INSERT INTO %s VALUES (" % table
                
                cur.execute(query + values + ")", tuple(map(str, d[i])))

    # Also need a table to keep track of which surveys are matched to which RACS catalogue
    cur.execute("CREATE TABLE IF NOT EXISTS match_info(match_table TEXT, racs_table TEXT)")

    return

# Add the survey status from the Google spreadsheet as a table to the db
def add_survey_status(cur = cur, name = "survey_status"):
    sheet_id = "1KLFRPpbS_4AlsBKz2iguSdLRWLZvBEj9jjhR3SHVimU"
    url = "https://docs.google.com/spreadsheets/d/%s/export?exportFormat=csv" % sheet_id
    res = requests.get(url=url)
    csvdata = res.content.decode("utf-8").lower().splitlines()
    headers = csvdata.pop(0).split(',')
    cur.execute("DROP TABLE %s" % name)
    sql_command = "CREATE TABLE %s (" % (name)
    sql_command = sql_command + "type TEXT, survey TEXT PRIMARY KEY, vizier_code TEXT, angular_sep INT, global_density FLOAT, status TEXT, relevant_columns TEXT, sourced_from TEXT);"
    cur.execute(sql_command)
    for line in csvdata:
        data = line.split(',')
        for i,val in enumerate(data):
            if val == '-':
                data[i] = "NULL"
        sql_command = "INSERT INTO %s VALUES ('%s','%s','%s',%s,%s,'%s','%s','%s');" % (name,data[0],data[1],data[2],data[3],data[4],data[5],data[6],url)
        cur.execute(sql_command)
    conn.commit()
    return 

