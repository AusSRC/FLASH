#!/usr/bin/python3

import os
import sys
import xmltodict

filename = sys.argv[1]
comp_name = sys.argv[2]

with open(filename,'r',encoding = 'utf-8') as file:
    xml_data = file.read()

xml_dict = xmltodict.parse(xml_data)

fieldnames = []
datadict = {}
# Get field names
for row in xml_dict['VOTABLE']['RESOURCE']['TABLE']['FIELD']:
    fieldnames.append(row['@name'].strip())

# Get data for given component
for row in xml_dict['VOTABLE']['RESOURCE']['TABLE']['DATA']['TABLEDATA']['TR']:
    if row['TD'][1] == comp_name:
        for i,val in enumerate(row['TD']):
            datadict[fieldnames[i]] = val
        break
print(datadict)
print("Done")
