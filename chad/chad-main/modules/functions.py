#!/usr/bin/python
# Helper functions
# L. Canepa, adapted from V.A. Moss

import sys
import requests

"""
Downloads information from Google spreadsheet and writes into local file.
Inputs:
	- sheet_id: Google sheet id
"""
def download_csv(sheet_id):

	url = "https://docs.google.com/spreadsheets/d/%s/export?exportFormat=csv" % sheet_id
	res = requests.get(url=url)
	open("input/chadsurveys.csv", "wb").write(res.content)
	
	return
	
"""
Generate SQL table header from csv file
Inputs:
	- table: an astropy Table holding catalogue information 
	- table_name: name of the table to be created
	- prim_key: primary key of the table 
Outputs:
	- header: string containing the generated SQL CREATE TABLE command 
	- keytypes: list of types for each column of the table
"""
def generate_header(table, table_name, prim_key = "id"):

	# Check that primary key exists
	if prim_key not in table.keys():
		print("ERROR: Please specify an existing column name for primary key")
		sys.exit()

	# Determine key type
	keytypes = []
	keytypes_db = []
	dbkeys = table.keys()
	for k in range(0, len(dbkeys)):
		key = dbkeys[k]
		keytype = str(table[key].dtype)
		keytypes.append(keytype)
		
		# Determine type for database
		if "int" in keytype:
			keytypes_db.append("BIGINT")
		elif "float" in keytype:
			keytypes_db.append("FLOAT")
		elif "<U" or "str" in keytype:
			keytypes_db.append("TEXT")
		else:
			# Stop if we can't find the correct type
			print("Type uncertain: %s... exiting!" % keytype)
			sys.exit()

		# Deal with bad column names
		if key[0].isdigit() == True:
			dbkeys[k] = 'x'+key
		if '.' in key:
			dbkeys[k] = '\"'+key+'\"'
		if key != "id" and key.lower() == "id": # check that foreign key "id" (from master) is not duplicated here
			# Duplicate column
			dbkeys[k] = key+"_x"

	# Generate create table command
	header = "CREATE TABLE %s(\n" % table_name
	
	for i in range(0, len(dbkeys)):
		if dbkeys[i] == prim_key or dbkeys[i] == prim_key+"_x" or dbkeys[i] == "x"+prim_key:
			header = header + "%s %s PRIMARY KEY,\n" % (dbkeys[i], keytypes_db[i])
		else:
			header = header + "%s %s,\n" % (dbkeys[i], keytypes_db[i])
	header = header[:-2]+"\n)"
	
	return header, keytypes

"""
Check incoming rows to existing table for mismatched types. Change if old_type = int
Inputs:
	- table: astropy Table containing catalogue information to be added
	- table_name: name of (existing) table in database
	- old_keytypes: list of keytypes from existing table 
Outputs:
	- cmd: empty string if all OK, otherwise a generated SQL ALTER TABLE command to change key type
	       of a column
"""
def check_keys(table, table_name, old_keytypes):
	cmd = ""

	new_keys = table.keys()
	for i in range(len(old_keytypes)):
		if table[new_keys[i]].dtype != old_keytypes[i]:
			# Check if old type = int and new type = float
			if "int" in old_keytypes[i] and "float" in str(table[new_keys[i]].dtype):
				# Check column name
				if new_keys[i][0].isdigit() == True:
					new_keys[i] = 'x'+new_keys[i]
				if '.' in new_keys[i]:
					new_keys[i] = '\"'+new_keys[i]+'\"'
				if new_keys[i] != "id" and new_keys[i].lower() == "id": # check that foreign key "id" (from master) is not duplicated here
					# Duplicate column
					new_keys[i] = new_keys[i]+"_x"

				# Update column type
				cmd += "ALTER TABLE %s ALTER COLUMN %s TYPE FLOAT; " % (table_name, new_keys[i])
			# Check if old type = int and new type = string
			elif ("int" in old_keytypes[i]) and ("<U" in str(table[new_keys[i]].dtype)) or ("str" in str(table[new_keys[i]].dtype)):
				# Check column name
				if new_keys[i][0].isdigit() == True:
					new_keys[i] = 'x'+new_keys[i]
				if '.' in new_keys[i]:
					new_keys[i] = '\"'+new_keys[i]+'\"'
				if new_keys[i] != "id" and new_keys[i].lower() == "id": # check that foreign key "id" (from master) is not duplicated here
					# Duplicate column
					new_keys[i] = new_keys[i]+"_x"

				# Update column type
				cmd += "ALTER TABLE %s ALTER COLUMN %s TYPE TEXT; " % (table_name, new_keys[i])

	return cmd
