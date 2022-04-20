# Database functions
# L. Canepa

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import numpy as np

"""
Open a connection to the database
Outputs: 
    - conn: connection (needed to close connection after execution)
    - cur: cursor (needed to execute queries)
"""
def connect():
    conn = psycopg2.connect("dbname=chad user=postgres password=hello")
    cur = conn.cursor()
    return conn, cur

"""
Get a list of all tables in the database
Outputs:
    - list of tables
"""
def get_tables():
    conn, cur = connect()

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')")
    tables = cur.fetchall()
    tables = [table[0] for table in tables if table[0] != "match_info"]

    cur.close()
    conn.close()

    return tables

"""
Return a list of column names from the database
Inputs:
    - cat: table to be queried
Outputs:
    - colnames: list of column names
"""
def colnames(cat):
    conn, cur = connect()

    cur.execute("SELECT * FROM " + cat + " LIMIT 0")
    colnames = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return colnames

"""
Perform a positional search against RACS catalogues. 
Inputs:
    - ra: right ascension (degrees, float)
    - dec: declination (degrees, float)
    - radius: search radius (arcmin, float)
    - cat: table to search in (string)
    - min_flux (optional): minimum flux for results (mJy, float)
    - force_match (optional): only return results with match in this table (string)
Outputs:
    - results: list of tuples of sources matching constraints
"""
def cone_search(ra, dec, radius, cat, min_flux = None, force_match = None):
    conn, cur = connect()
    # Convert everything to radians
    radius = np.radians(radius / 60)
    ra = np.radians(ra)
    dec = np.radians(dec)

    flux_constraint = ""
    values = (dec, dec, ra, dec, dec, ra, radius, dec, dec, ra)
    if min_flux != None:
        flux_constraint = " AND peak_flux >= %s"
        values = (dec, dec, ra, dec, dec, ra, radius, min_flux, dec, dec, ra)

    # Perform cone search with conditions (if any)
    if force_match != None: 
        # Check whether force_match table is valid for this racs catalogue type
        cur.execute("SELECT racs_table FROM match_info WHERE match_table = %s", (force_match,))
        result = cur.fetchone()
        print(result[0], cat)
        if result[0] != cat:
            # Invalid force_match to racs catalogue type, no result
            return []
        
        # Only select rows that have a match in the other table
        cur.execute(sql.SQL("SELECT {}.*, DEGREES(ACOS(SIN(RADIANS(dec))*SIN(%s)+\
                    COS(RADIANS(dec))*COS(%s)*COS(RADIANS(ra)-%s))) FROM {} INNER JOIN {} ON {}.id = {}.id WHERE \
                    ACOS(SIN(RADIANS(dec))*SIN(%s)+COS(RADIANS(dec))*COS(%s)*\
                    COS(RADIANS(ra)-%s)) < %s" + flux_constraint + " ORDER BY ACOS(SIN(RADIANS(dec))*SIN(%s)+\
                    COS(RADIANS(dec))*COS(%s)*COS(RADIANS(ra)-%s))").format(sql.Identifier(cat), sql.Identifier(cat), \
                    sql.Identifier(force_match), sql.Identifier(cat), sql.Identifier(force_match)), values)
    else:
        cur.execute(sql.SQL("SELECT *, DEGREES(ACOS(SIN(RADIANS(dec))*SIN(%s)+COS(RADIANS(dec))*COS(%s)*\
                    COS(RADIANS(ra)-%s))) FROM {} WHERE ACOS(SIN(RADIANS(dec))*SIN(%s)+COS(RADIANS(dec))*COS(%s)*\
                    COS(RADIANS(ra)-%s)) < %s" + flux_constraint + " ORDER BY ACOS(SIN(RADIANS(dec))*SIN(%s)+\
                    COS(RADIANS(dec))*COS(%s)*COS(RADIANS(ra)-%s))").format(sql.Identifier(cat)), values)

    results = cur.fetchmany(100) # Return first 100 results?
    cur.close()
    conn.close()

    return results

"""
Search for the closest source to a given RA and DEC
Inputs:
    - ra: right ascension (degrees, float)
    - dec: declination (degrees, float)
    - table: table to search in (string)
    - min_flux (optional): minimum flux for results (mJy, float)
    - force_match (optional): only show results with match in this table (string)
Outputs:
    - results: tuple of closest source to ra and dec that matches constraints
"""
def search_closest(ra, dec, table, min_flux = None, force_match = None):
    conn, cur = connect()

    ra = np.radians(ra)
    dec = np.radians(dec)

    flux_constraint = ""
    values = (dec, dec, ra, dec, dec, ra)
    if min_flux != None:
        flux_constraint = " WHERE peak_flux >= %s"
        values = (dec, dec, ra, min_flux, dec, dec, ra)

    if force_match != None:
        # Check whether force_match table is valid for this racs catalogue type
        cur.execute("SELECT racs_table FROM match_info WHERE match_table = %s", (force_match,))
        result = cur.fetchone()
        print(result[0], table)
        if result[0] != table:
            # Invalid force_match to racs catalogue type, no result
            return []

        # Using the small angle approximation since we assume there will always be a source < 1 degree away
        cur.execute(sql.SQL("SELECT {}.*, DEGREES(ACOS(SIN(RADIANS(dec))*SIN(%s)+COS(RADIANS(dec))*COS(%s)*\
                    COS(RADIANS(ra)-%s))) FROM {} INNER JOIN {} ON {}.id = {}.id" + flux_constraint +" ORDER BY \
                    ACOS(SIN(RADIANS(dec))*SIN(%s)+COS(RADIANS(dec))*COS(%s)*COS(RADIANS(ra)-%s)) ASC \
                    LIMIT 1").format(sql.Identifier(table),sql.Identifier(table), sql.Identifier(force_match), \
                    sql.Identifier(table), sql.Identifier(force_match)), values)
    else:
        cur.execute(sql.SQL("SELECT *, DEGREES(ACOS(SIN(RADIANS(dec))*SIN(%s)+COS(RADIANS(dec))*COS(%s)*\
                    COS(RADIANS(ra)-%s))) FROM {}" + flux_constraint + " ORDER BY ACOS(SIN(RADIANS(dec))*SIN(%s)+\
                    COS(RADIANS(dec))*COS(%s)*COS(RADIANS(ra)-%s)) ASC LIMIT 1").format(sql.Identifier(table)), values)

    result = cur.fetchone()

    conn.close()
    cur.close()

    return result

"""
Search for a source by id
Inputs:
    - id: ID of source
    - table: table name to search in
Outputs:
    - result: tuple of source with matching ID
"""
def search_id(id, table):
    conn, cur = connect()

    cur.execute("SELECT * FROM " + table + " WHERE id = %s", (id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result

"""
Return other tables with an id match
Inputs:
    - id: RACS id
    - curtable: name of current table
Outputs:    
    - match_tables: list of tables that also match this source
"""
def get_matches(id, curtable):
    conn, cur = connect()

    # Get a list of all other possible matching tables
    if "racs" in curtable:
        cur.execute("SELECT match_table FROM match_info WHERE racs_table = %s", (curtable,))
        tables = cur.fetchall()
        tables = [table[0] for table in tables]
    else:
        cur.execute("SELECT racs_table FROM match_info WHERE match_table = %s", (curtable,))
        racs_table = cur.fetchone()[0]
        cur.execute("SELECT match_table FROM match_info WHERE racs_table = %s", (racs_table,))
        tables = cur.fetchall()
        tables = [racs_table] + [table[0] for table in tables if curtable not in table[0]]
    
    # Search through all other tables for matching object
    match_tables = []
    for table in tables:
        cur.execute("SELECT * FROM " + table + " WHERE id = %s", (id,))
        m = cur.fetchall()
        if len(m) > 0:
            match_tables.append(table)

    cur.close()
    conn.close()
    return match_tables

"""
For a given source, find all associated components
Inputs:
    - source_id: RACS id of source
Outputs:
    - comp: list of tuples of components belonging to this source
"""
def find_components(source_id):
    conn, cur = connect()

    # Get all components associated with this source
    cur.execute("SELECT id, gaussian_id, ra, dec FROM racs_component WHERE source_id = %s", (source_id,))
    comp = cur.fetchall()

    cur.close()
    conn.close()

    return comp

"""
Search for an exact value in a given table column
Inputs:
    - table: name of table to search in
    - colname: column name to search in
    - constraint: value to search for
Outputs:
    - r: rows matching the search (list of tuples)
"""
def search_exact(table, colname, constraint):
    conn, cur = connect()

    # Perform the search
    cur.execute(sql.SQL("SELECT id FROM {} WHERE {} = %s").format(sql.Identifier(table), sql.Identifier(colname)), (constraint,))
    r = cur.fetchmany(50)
    
    cur.close()
    conn.close()

    return r

"""
Get the matching RACS table
Input:
    - curtable: name of current (non-RACS) table
Output:
    - racs_table: name of matching RACS table
"""
def get_racs_table(curtable):
    conn, cur = connect()

    cur.execute("SELECT racs_table FROM match_info WHERE match_table = %s", (curtable,))
    racs_table = cur.fetchone()[0]

    cur.close()
    conn.close()

    return racs_table