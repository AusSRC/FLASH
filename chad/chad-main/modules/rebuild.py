#!/usr/bin/python
# Module to delete and rebuild CHAD database with just master catalogue.
# L. Canepa, adapted from V.A. Moss
__author__ = "L. Canepa"
__version__ = "0.2"

import glob
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from astropy.io import ascii
from . import functions as f

passwd = "hello" # Update with password for user postgres

def rebuild():
	
	# Connect to the host to rebuild database
	conn = psycopg2.connect("host=localhost dbname=postgres user=postgres password=%s" % passwd)
	conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
	cur = conn.cursor()
	cur.execute("DROP DATABASE IF EXISTS chad;")
	conn.commit()
	cur.execute("CREATE DATABASE chad;")
	conn = psycopg2.connect("host=localhost dbname=chad user=postgres password=hello")
	cur = conn.cursor()
	
	# Add the base catalogue to CHAD
	print("Adding base catalogue to CHAD...")
	add_master(cur, name = "racs") # If master table is something different, change name

	conn.commit()		
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
		cur.execute("CREATE TABLE match_info(match_table TEXT, racs_table TEXT)")

	return
