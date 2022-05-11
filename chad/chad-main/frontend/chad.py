# Main application file for CHAD frontend
# L. Canepa
from flask import Flask, render_template, request, redirect, url_for
import db
from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError

app = Flask(__name__)

# Main landing page
@app.route('/')
def home():
    tables = db.get_tables()
    tables = [table for table in tables if "racs" not in table]
    return render_template("home.html", search_error = None, other_tables = tables)

# Main landing page, with search error message
@app.route('/error-<error>')
def home_error(error):
    tables = db.get_tables()
    tables = [table for table in tables if "racs" not in table]
    return render_template("home.html", search_error = error, other_tables = tables)

# About page
@app.route('/about')
def about():
    tables = db.get_tables()
    return render_template("about.html", tables=tables) 

###################################################################################################
#########                                 SEARCH FUNCTIONS                        #################
###################################################################################################

# Perform a cone search and display results
@app.route('/result-conesearch', methods=["POST", "GET"])
def results():
    if request.method == "GET":
        return redirect(url_for("home"))

    # Check the coordinates format
    ra = request.form['ra']
    dec = request.form['dec']
    radius = request.form['radius']
    cattype = request.form['cattype']
    table = "racs_"+cattype
    min_flux = None
    force_match = None

    if request.form.get('flux') == "on":
        min_flux = request.form['min_flux']
    if request.form.get('forcematch') == "on":
        force_match = request.form['forcematch_table']
    try: # Check that all parameters are ok
        if ':' in ra: # hms format
            h, m, s = ra.split(':')
            h, m, s = float(h), float(m), float(s)
            ra = 15*h+(15/60)*m+(15/3600)*s # Convert to degrees
        else:
            ra = float(ra)
        if ':' in dec: # dms format
            d, m, s = dec.split(':')
            d, m, s = float(d), float(m), float(s)
            if d < 0: # deal with negative declination
                m = -m
                s = -s
            dec = d + m/60 + s/3600
        else:
            dec = float(dec)
        radius = float(radius)
        if request.form.get('flux') == "on":
            min_flux = float(min_flux)
    except:
        return redirect(url_for("home_error", error="pos")) # Invalid request

    # Get the results from the database
    results = db.cone_search(ra, dec, radius, table, min_flux = min_flux, force_match = force_match)
    
    trunc = False
    if len(results) >= 100: # Only return the first 100 results
        trunc = True

    # Find the columns necessary for results display
    colnames = db.colnames(table)
    if len(results) > 0:
        # Take first column of type string with a 'J' in it as source name
        name_candidates = [x for x in results[0] if type(x) == str and 'J' in x]
        if len(name_candidates) == 0:
            name_candidates = [x for x in results[0] if type(x) == str]
        name_idx = results[0].index(name_candidates[0])
        name = [x[name_idx] for x in results] # Store name of source

        # Find source ra and dec
        ra_idx = colnames.index([x for x in colnames if "ra" in x][0])
        source_ra = [x[ra_idx] for x in results]
        dec_idx = colnames.index([x for x in colnames if "de" in x and "ra" not in x][0])
        source_dec = [x[dec_idx] for x in results]
        ids = [x[0] for x in results]
        ang_dist = [round(x[-1]*60, 2) for x in results]
    else:
        name = []
        source_ra = []
        source_dec = []
        ids = []
        ang_dist = []

    search_params = {}
    search_params['ra'] = ra
    search_params['dec'] = dec
    search_params['radius'] = radius
    search_params['table'] = table
    if force_match:
        search_params['name'] = force_match

    return render_template("results.html", search_params=search_params, results=(name, source_ra, source_dec, ang_dist), ids=ids, trunc = trunc)

# Search for single closest source to a given ra and dec
@app.route('/result-closest', methods=["POST", "GET"])
def result_closest():
    if request.method == "GET":
        return redirect(url_for("home"))
    
    # Check the coordinates format
    ra = request.form['ra']
    dec = request.form['dec']
    cattype = request.form['cattype']
    table = "racs_"+cattype
    min_flux = None
    force_match = None

    if request.form.get('flux') == "on":
        min_flux = request.form['min_flux']
    if request.form.get('forcematch') == "on":
        force_match = request.form['forcematch_table']
    try: # Check that all parameters are ok
        if ':' in ra: # hms format
            h, m, s = ra.split(':')
            h, m, s = float(h), float(m), float(s)
            ra = 15*h+(15/60)*m+(15/3600)*s # Convert to degrees
        else:
            ra = float(ra)
        if ':' in dec: # dms format
            d, m, s = dec.split(':')
            d, m, s = float(d), float(m), float(s)
            if d < 0: # deal with negative declination
                m = -m
                s = -s
            dec = d + m/60 + s/3600
        else:
            dec = float(dec)
        if request.form.get('flux') == "on":
            min_flux = float(min_flux)
    except:
        return redirect(url_for("home_error", error="closest"))
    
    # Get the results from the database
    result = db.search_closest(ra, dec, table, min_flux = min_flux, force_match = force_match)
    if len(result) > 0:
        # Find the columns we want
        colnames = db.colnames(table)
        name_candidates = [x for x in result if type(x) == str and 'J' in x]
        if len(name_candidates) == 0:
            name_candidates = [x for x in result if type(x) == str]
        name = [name_candidates[0]]

        ra_idx = colnames.index([x for x in colnames if "ra" in x][0])
        source_ra = [result[ra_idx]]
        dec_idx = colnames.index([x for x in colnames if "de" in x][0])
        source_dec = [result[dec_idx]]
        id = [result[0]]
        ang_dist = [round(result[-1]*60, 2)]
    else:
        name = []
        source_ra = []
        source_dec = []
        id = []
        ang_dist = []

    search_params = {}
    search_params['ra'] = ra
    search_params['dec'] = dec
    search_params['table'] = table

    return render_template("results.html", search_params=search_params, results=(name, source_ra, source_dec, ang_dist), ids=id, trunc = False)

# Search by name
@app.route('/result-name', methods=['POST', 'GET'])
def result_name():
    if request.method == 'GET':
        return redirect(url_for("home"))
    # Get parameters from the form
    search_name = request.form['name']
    table = "racs_" + request.form['cattype']

    # Try to find the coordinates of this object
    try:
        coord = SkyCoord.from_name(search_name)
    except NameResolveError:
        return redirect(url_for("home_error", error="name"))
    # Search with the coordinates of the object
    ra = coord.ra.degree
    dec = coord.dec.degree
    result = db.search_closest(ra, dec, table)

    if len(result) > 0:
        # Find the columns we want
        colnames = db.colnames(table)
        name_candidates = [x for x in result if type(x) == str and 'J' in x]
        if len(name_candidates) == 0:
            name_candidates = [x for x in result if type(x) == str]
        name = [name_candidates[0]]

        ra_idx = colnames.index([x for x in colnames if "ra" in x][0])
        source_ra = [result[ra_idx]]
        dec_idx = colnames.index([x for x in colnames if "de" in x][0])
        source_dec = [result[dec_idx]]
        id = [result[0]]
        ang_dist = [round(result[-1]*60*60, 2)]
    else:
        name = []
        source_ra = []
        source_dec = []
        id = []
        ang_dist = []

    search_params = {}
    search_params['ra'] = ra
    search_params['dec'] = dec
    search_params['table'] = table
    search_params['name'] = search_name

    return render_template("results.html", search_params=search_params, results=(name, source_ra, source_dec, ang_dist), ids=id, trunc = False)

# Find components from source id
@app.route('/<source_id>/components')
def find_components(source_id):
    # Search for corresponding components
    components = db.find_components(source_id)

    # Define the column names
    id = [x[0] for x in components]
    name = [x[1] for x in components]
    ra = [x[2] for x in components]
    dec = [x[3] for x in components]

    if len(components) == 1:
        # Go directly to show component page
        return redirect(url_for("show_summary", id = id[0], table="component"))

    search_params = {}
    search_params['table'] = "racs_component"

    return render_template("results.html", search_params=search_params, results=(name, ra, dec, None), ids=id)

# Find source from component id
@app.route('/<source_id>/source')
def find_source(source_id):
    id = db.search_exact("racs_island", "source_id", source_id)
    return redirect(url_for('show', id=id[0][0], table="racs_island"))

###################################################################################################
###########                            DISPLAY FUNCTIONS                             ##############
###################################################################################################

# Show summary information from a particular source
@app.route('/summary/<table>/<int:id>')
def show_summary(id, table):
    # Get entry from racs table
    table = "racs_" + table

    # Find other tables with this id
    tables = [table]
    other_tables = db.get_matches(id, table)

    if len(other_tables) > 0:
        tables = tables + other_tables
    else:
        # If this source is in no other tables, redirect straight to the RACS show page
        return redirect(url_for("show", id = id, table = tables[0]))

    # Get all table entries for this source
    entries = []
    for t in tables:
        entries.append(db.search_id(id, t))

    # Get name, ra, dec and other information
    dicts = [{} for i in range(len(tables))]
    for i in range(len(tables)):
        name_candidates = [x for x in entries[i] if type(x) == str and 'J' in x]
        if len(name_candidates) == 0:
            name_candidates = [x for x in entries[i] if type(x) == str]

        dicts[i]["name"] = name_candidates[0]
        colnames = db.colnames(tables[i])
        dicts[i]["ra"] = entries[i][colnames.index([x for x in colnames if "ra" in str(x).lower()][0])]
        dicts[i]["dec"] = entries[i][colnames.index([x for x in colnames if "de" in str(x).lower() and "ra" not in str(x).lower()][0])]
        
        # Add all the other table data into the dictionary
        table_dict = dict(zip(colnames, entries[i]))
        dicts[i].update(table_dict)
    
    # Get WISE colour-colour plot information
    wise_plot = None
    for i in range(len(tables)):
        if tables[i] == "allwise":
            colour_x = dicts[i]["w2mag"]-dicts[i]["w3mag"] # W2-W3 on the x axis
            colour_y = dicts[i]["w1mag"]-dicts[i]["w2mag"] # W1-W2 on the y axis
            wise_plot = (colour_x, colour_y)
    
    # Pass into display template
    return render_template('show/show_summary.html', dicts = dicts, tables = tables, wise_plot=wise_plot)
        
# Display source information from table
@app.route('/<table>/<int:id>')
def show(id, table):
    # Get the master table information about the source
    source = db.search_id(id, table)
    colnames = db.colnames(table)

    # Make a dictionary based on source table and colnames for easy access
    source_dict = dict(zip(colnames, source))

    # List other tables that match this source
    match_tables = db.get_matches(id, curtable = table)
    
    if "racs" in table:
        if table == "racs_component":
            source_dict['name'] = source_dict['gaussian_id']
        else:
            source_dict['name'] = source_dict['source_name']
        return render_template("show/show_racs.html", source=source_dict, match_tables=match_tables, table=table)
    else:
        # Determine basic info (name, ra, dec)
        name = [x for x in source if type(x) == str and 'J' in x][0]
        source_dict['name'] = name
        ra = source[colnames.index([x for x in colnames if "ra" in x.lower()][0])]
        source_dict['ra'] = ra
        dec = source[colnames.index([x for x in colnames if "de" in x.lower() and "ra" not in x.lower()][0])]
        source_dict['dec'] = dec
        # Get the matching RACS source name
        racs_table = db.get_racs_table(table)
        racs_match = db.search_id(source_dict['id'], racs_table)
        racs_match = [col for col in racs_match if type(col) == str][0]

        # Display correct table template
        if table == "allwise":
            return render_template("show/show_wise.html", source=source_dict, match_tables=match_tables, table=table, racs_match=racs_match, racs_table = racs_table)
        elif table == "rosat_2rxs":
            return render_template("show/show_rosat.html", source=source_dict, match_tables=match_tables, table=table, racs_match=racs_match, racs_table = racs_table)
        elif table == "fermi_4fgl":
            return render_template("show/show_fermi.html", source=source_dict, match_tables=match_tables, table=table, racs_match=racs_match, racs_table = racs_table)
        elif table == "xmm4_dr9":
            return render_template("show/show_xmm.html", source=source_dict, match_tables=match_tables, table=table, racs_match=racs_match, racs_table = racs_table)
        elif table == "sdss":
            return render_template("show/show_sdss.html", source=source_dict, match_tables=match_tables, table=table, racs_match=racs_match, racs_table=racs_table)
        else:
            return render_template("show/show_basic.html", source=source_dict, match_tables=match_tables, table=table, racs_match=racs_match, racs_table=racs_table)
