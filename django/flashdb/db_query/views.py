import json
import os
import sys
import re
import psycopg2
import random
import string

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
from .models import MyModel

#######################################################################################

def connect(db="flashdb",user="flash",host="10.0.2.225",password=None):

    if not password:
        password = PASSWD
    conn = psycopg2.connect(
        database = db,
        user = user,
        password = password,
        host = host,
        #port = 2095
        #host = "10.0.2.225",
        port = 5432
    )
    #print(conn.get_dsn_parameters(),"\n")
    return conn

def get_cursor(conn):

    cursor = conn.cursor()
    return cursor


##################################################################################################
def generate_id(length=20):
    # Generate a random id string of 20 letters
    letters = string.ascii_letters
    id = ''.join(random.choice(letters) for i in range(length))
    return id

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
            # sbid for this version doesn't exist
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
def get_comp_ra_dec(cur,comp_id):
    query = ("select ra_deg_cont,dec_deg_cont from component where comp_id = %s order by comp_id")
    cur.execute(query,(comp_id,))
    radec = cur.fetchone()
    return radec

##################################################################################################
def getSBIDmetadata(sbid):

    with connection.cursor() as cur:
        sbid_id,version = get_max_sbid_version(cur,sbid)
        query = "select s.quality,s.pointing,sr.date,sr.run_tag from sbid s inner join spect_run sr on s.spect_runid = sr.id where s.id = %s;"
        cur.execute(query,(sbid_id,))
        data = cur.fetchone()
    return data
##################################################################################################
def get_results_for_sbid(cur,sbid,version,LN_MEAN,order,reverse,dir_download,inverted,masked,verbose=True):
    # This will print out a table of linefinder output data for a given sbid
    # args[1] = db cursor
    # args[2] = The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    #           then use the latest version
    # args[3] = The sbid version you want to use - if a version is not declared ("45833" rather than "45833:2"),
    #           then use the latest version
    # args[4] = ln_mean cutoff - only sources with an ln_mean() value larger than this will be shown
    #           If no value is given, it will be set to 0.0
    # args[8] = if inverted spectra are requested
    # args[9] = if masked spectra are requested

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)
    #print(f"For {sbid}:{version} ...")
    # min val for ln_mean:
    try:
        ln_mean = float(LN_MEAN)
    except ValueError: # No value given. Set to 0
        ln_mean = 0.0
                 
    # Get the results table 
    if inverted:
        query = "select invert_results from sbid where id = %s;"
    elif masked:
        query = "select mask_results from sbid where id = %s;"
    else:
        query = "select results from sbid where id = %s;"
    cur.execute(query,(sid,))
    try:
        result_data = cur.fetchone()[0].split('\n')
    except TypeError:
        print(f"Output data = 0 for sbid {sbid}:{version}!")
        return None,None

    # Get the pointing field for the sbid:
    query = "select pointing from sbid where id = %s;"
    cur.execute(query,(sid,))
    pointing = cur.fetchone()[0]

    # Get the list of relevant components and their values for this sbid from the component table
    if ln_mean == -1: # This means get all components, even if there is no value for ln_mean
        if order == "lnmean":
            if inverted:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,invert_mode_num,invert_ln_mean from component where sbid_id = %s order by invert_ln_mean")
            else:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s order by ln_mean")
            if reverse:
                query += " desc;"
            else:
                query += ";"
        else:
            if inverted:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,invert_mode_num,invert_ln_mean from component where sbid_id = %s order by comp_id")
            else:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s order by comp_id")
            if reverse:
                query += " desc;"
            else:
                query += ";"
        cur.execute(query,(sid,))
    else:
        if order == "lnmean":
            if inverted:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,invert_mode_num,invert_ln_mean from component where sbid_id = %s and invert_ln_mean > %s and invert_mode_num > 0 order by invert_ln_mean")
            else:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s and ln_mean > %s and mode_num > 0 order by ln_mean")
            if reverse:
                query += " desc;"
            else:
                query += ";"
        else:
            if inverted:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,invert_mode_num,invert_ln_mean from component where sbid_id = %s and invert_ln_mean > %s and invert_mode_num > 0 order by comp_id")
            else:
                query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s and ln_mean > %s and mode_num > 0 order by comp_id")
            if reverse:
                query += " desc;"
            else:
                query += ";"
        cur.execute(query,(sid,ln_mean))
    results = cur.fetchall()
    row_count = len(results)
    # Extract component id from results and get corresponding line from result_data
    results_dict = {}
    notf = 0
    for result in results:
        comp_id = "component" + result[1].split("_component")[1].split(".")[0]
        results_dict[comp_id] = []
        found = False
        for line in result_data:
            if comp_id in line:
                results_dict[comp_id].append(line)
                found = True
        if not found:
            notf += 1
            print(f"{notf}: NOT FOUND! {comp_id}")

    if verbose: # detailed output is saved to file
        if inverted:
            f = open(f"{dir_download}/{sbid}_linefinder_inverted_outputs.csv","w")
        elif masked:
            f = open(f"{dir_download}/{sbid}_linefinder_masked_outputs.csv","w")
        else:
            f = open(f"{dir_download}/{sbid}_linefinder_outputs.csv","w")
        # we want From component table - component_id, component_name, ra_hms_cont dec_dms_cont (both hms and degree), flux_peak, flux_int, has_siblings
        # From linefinder, all outputs except name: ModeNum x0_1_maxl dx_1_maxl y0_1_maxl abs_peakz_median abs_peakz_siglo abs_peakz_sighi abs_peakopd_median abs_peakopd_siglo abs_peakopd_sighi abs_intopd_median(km/s) abs_intopd_siglo(km/s) abs_intopd_sighi(km/s) abs_width_median(km/s) abs_width_siglo(km/s) abs_width_sighi(km/s) ln(B)_mean ln(B)_sigma chisq_mean chisq_sigma
        f.write("#Component_name,comp_id,modenum,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,x0_1_maxl,dx_1_maxl,y0_1_maxl,abs_peakz_median,abs_peakz_siglo,abs_peakz_sighi,abs_peakopd_median,abs_peakopd_siglo,abs_peakopd_sighi,abs_intopd_median(km/s),abs_intopd_siglo(km/s),abs_intopd_sighi(km/s),abs_width_median(km/s),abs_width_siglo(km/s),abs_width_sighi(km/s),ln(B)_mean,ln(B)_sigma,chisq_mean,chisq_sigma,field\n")
    #print()
    outputs = []
    alt_outputs = []
    for result in results:
        comp_id = "component" + result[1].split("_component")[1].split(".")[0]
        if verbose:
            comp= "component" + result[1].split("_component")[1].split(".")[0]
            linefinder_data = results_dict[comp]
            for line in linefinder_data:
                vals = line.split()
                if float(vals[17]) > ln_mean:
                    f.write(f"{result[0]},{comp},{vals[1]},{result[2]},{result[3]},{result[4]},{result[5]},{result[6]},{result[7]},{vals[2]},{vals[3]},{vals[4]},{vals[5]},{vals[6]},{vals[7]},{vals[8]},{vals[9]},{vals[10]},{vals[11]},{vals[12]},{vals[13]},{vals[14]},{vals[15]},{vals[16]},{vals[17]},{vals[18]},{vals[19]},{vals[20]},{pointing}\n")
                alt_outputs.append([result[0],comp_id,result[4],result[5],vals[5],vals[8],vals[11],vals[14],result[9],result[10],pointing])
        outputs.append([result[0],comp_id,result[2],result[3],result[4],result[5],result[9],result[10],pointing])
    if verbose:
        f.close()
    return outputs,alt_outputs

##################################################################################################
def get_ascii_files_tarball(conn,cur,sid,sbid,static_dir,version,password=None):
    # Download tar of ascii files for the sbid
    query = "select ascii_tar from sbid where id = %s"
    cur.execute(query,(sid,))
    oid = cur.fetchone()[0]
    print(f"Retrieving large object {oid} from db to {static_dir}")
    name = f"{sbid}_{version}.tar.gz"
    pathname = f"{static_dir}/{name}"
    export_q = f"\lo_export {oid} '{pathname}'"
    os.system(f'export PGPASSWORD={password}; psql -h 10.0.2.225 -p 5432 -d flashdb -U flash -c "{export_q}"') 
    print(f"Downloaded tar of ascii files for {sbid}:{version} to {static_dir}",flush=True)
    return name


    #loaded_lob = conn.lobject(oid=oid, mode="rb")
    #name = f"{sbid}_{version}.tar.gz"
    # This may run out of mem for a very large object:
    #open(f"{dir_download}/{name}", 'wb').write(loaded_lob.read())
    # So use streaming function:
    #loaded_lob.export(f"{static_dir}/{name}")
    #loaded_lob.close()
    #print(f"Downloaded tar of ascii files for {sbid}:{version}")
    #return name

##################################################################################################
def get_linefinder_tarball(conn,sbid,dir_download,version,inverted,masked):
    cur = get_cursor(conn)
    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)

    oid = None
    outputs = None
    name = f"{sbid}_{version}.tar"
    if inverted:
        name = f"{sbid}_{version}_inverted.tar"
        query = "select invert_detectionF from sbid where id = %s"
    elif masked:
        name = f"{sbid}_{version}_masked.tar"
        query = "select mask_detectionF from sbid where id = %s"
    else:
        query = "select detectionF from sbid where id = %s"
    cur.execute(query,(sid,))
    detect = cur.fetchone()[0]
    if not detect:
        print(f"No linefinder results available for sbid {sbid}:{version} !!")
        return
    # The output files are normally stored as both a byte array AND a large object.
    # If the LOB exists, down load that in preference to the byte array, as it's more efficient:
    if not inverted and not masked:
        query = "select detect_tar from sbid where id = %s"
        cur.execute(query,(sid,))
        oid = cur.fetchone()[0]
    if oid:
        #print(f"Retrieving large object {oid} from db")
        loaded_lob = conn.lobject(oid=oid, mode="rb")
        # This may run out of mem for a very large object, but is 4x quicker than streaming:
        open(f"{dir_download}/{name}", 'wb').write(loaded_lob.read())
    else:
        print(f"No LOB found - retrieving byte array from db")
        if inverted:
            query = "select invert_detect_results from sbid where id = %s"
        elif masked:
            query = "select mask_detect_results from sbid where id = %s"
        else:
            query = "select detect_results from sbid where id = %s"
        cur.execute(query,(sid,))
        outputs = cur.fetchone()[0]
        if outputs:
            open(f"{dir_download}/{name}", 'wb').write(outputs)
        else:
            print(f"Linefinder was run, but no results stored in db for sbid {sbid}:{version} !!")
            return
        
    #print(f"Downloaded tar of linefinder result files for {sbid}:{version}")

    return name


##################################################################################################
def get_bright_comps(cur,sbid,number,version=None):

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)
    query = "select comp_id from component where sbid_id = %s"
    cur.execute(query,(sid,))
    comps = [comp[0] for comp in cur.fetchall()[1:]]

    namedir = {}

    for name in comps:
        source_num = int(re.split('(\\d+)',name)[-2])
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
    return bright_sources


##################################################################################################
def get_plots_for_comp(cur,sbid,comp,static_dir):

    # This will return the opd and flux plots for a given source.
    # The source name is constructed from the sbid and comp values, eg:
    #   sbid = 51449, com = '4c', source_name = 'spec_SB51449_component_4c.fits'

    source_name = comp
    # The directory for downloads:
    dir_download = static_dir
    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid)

    opd_name = None
    flux_name = None
    for data_type in ["opd","flux"]:
        query = f"select {data_type}_image from component where comp_id = %s"
        cur.execute(query,(source_name,))
        data = cur.fetchone()
        if not data or not data[0]:
            #query = f"select fluxfilter from component where comp_id = %s and sbid_id = %s;"
            #cur.execute(query,(source_name,sid))
            #flux_filter = cur.fetchone()[0]
            print(f"plotfile for {source_name} missing from db")
            continue
        name = source_name.replace(".fits",f"_{data_type}.png")
        if data_type == "opd":
            opd_name = name
        else:
            flux_name = name
        open(f"{dir_download}/{name}", 'wb').write(data[0])
    return flux_name,opd_name

##################################################################################################
##################################################################################################

# Create your views here.

def index(request):
    static_dir = os.path.abspath("db_query/static/db_query/")
    session_id = request.POST.get('session_id')
    if session_id is not None:
        print(f"Got {session_id} from POST")
        request.session["session_id"] = session_id
    else:    
        session_id = request.session.get("session_id")
        if session_id is None:
            session_id = generate_id(20)
            print(f"Generated {session_id}")
            request.session["session_id"] = session_id
        else:
            print(f"Got {session_id} from session")
    
    # Cleanup user session files
    try:
        os.system(f"sudo rm -R {static_dir}/plots/{session_id}")
        os.system(f"sudo rm -R {static_dir}/linefinder/{session_id}")
        os.system(f"sudo rm -R {static_dir}/linefinder/masks/{session_id}")
        os.system(f"sudo rm -R {static_dir}/ascii/{session_id}")
    except:
        pass

    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) from sbid;")
        num_records = cursor.fetchone()[0]

        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 1%';")
        pilot1_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 1%' and sbid.quality = 'REJECTED';")
        pilot1_reject = cursor.fetchone()[0]
        pilot1_accept = int(pilot1_records) - int(pilot1_reject)

        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 2%';")
        pilot2_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 2%' and sbid.quality = 'REJECTED';")
        pilot2_reject = cursor.fetchone()[0]
        pilot2_accept = int(pilot2_records) - int(pilot2_reject)

        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%Survey%';")
        survey_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%Survey%' and sbid.quality = 'REJECTED';")
        survey_reject = cursor.fetchone()[0]
        survey_accept = int(survey_records) - int(survey_reject)
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%Survey%' and sbid.quality = 'NOT_VALIDATED';")
        survey_unvalidated = cursor.fetchone()[0]
    return render(request, 'index.html', {'records': num_records, 
                                          'pilot1': pilot1_records, 
                                          'rpilot1': pilot1_reject, 
                                          'apilot1': pilot1_accept, 
                                          'pilot2': pilot2_records, 
                                          'rpilot2': pilot2_reject, 
                                          'apilot2': pilot2_accept, 
                                          'survey': survey_records,
                                          'asurvey': survey_accept,
                                          'unvalid': survey_unvalidated,
                                          'session_id': session_id})

def show_aladin(request):
    ra = request.POST.get('ra')
    dec = request.POST.get('dec')
    sbid = request.POST.get('sbid')
    comp_file = request.POST.get('comp')
    comp_id = comp_file.split('component_')[1].split('_flux')[0]
    return render(request, 'aladin.html', {'ra': ra, 'dec': dec, 'sbid': sbid, 'comp': comp_id})

def show_csv(request):
    csv_file = request.POST.get('csv')
    sbid_val = request.POST.get('sbid')
    lnmean = request.POST.get('lnmean')
    invert = request.POST.get('invert')
    return render(request, 'csv_parse.html', {'csv_file': csv_file, 'sbid': sbid_val, 'lnmean': lnmean, 'inverted': invert})

def show_sbids_aladin(request):
    # Show the aladin view with all SBIDs
    password = request.POST.get('pass')
    host = request.POST.get('host')
    session_id = request.POST.get('session_id')
    try:
        conn = connect(password=password, host=host)
    except:
        return HttpResponse("Password has failed")
    with conn.cursor() as cursor:
        query = 'SELECT t.sbid_num, t.pointing, comp.sbid_id, AVG(comp.ra_deg_cont::NUMERIC) AS ra,'\
            + ' AVG(comp.dec_deg_cont::NUMERIC) AS dec, t.quality AS status,'\
            + ' t.detectionf, t.invert_detectionf, t.mask_detectionf'\
            + ' FROM component comp'\
            + ' INNER JOIN sbid t ON comp.sbid_id = t.id'\
            + ' GROUP BY comp.sbid_id, t.sbid_num, t.pointing, t.quality, t.detectionf, t.invert_detectionf, t.mask_detectionf'
        cursor.execute(query)
        sbids = cursor.fetchall()
        # Count the number of SBIDs in each quality category
        query = "SELECT t.quality, COUNT(*) AS count" \
            + " FROM sbid t" \
            + " GROUP BY t.quality"
        print(query)
        cursor.execute(query)
        good = 0
        uncertain = 0
        rejected = 0
        not_validated = 0
        for row in cursor.fetchall():
            print(row)
            if row[0] == 'GOOD':
                good = row[1]
            elif row[0] == 'UNCERTAIN':
                uncertain = row[1]
            elif row[0] == 'REJECTED':
                rejected = row[1]
            elif row[0] == 'NOT_VALIDATED':
                not_validated = row[1]
        conn.close()
        return render(request, 'sbids_aladin.html', {'session_id': session_id, \
                'sbids': sbids, 'num_sbids': len(sbids), 'num_good': good, 'num_uncertain': uncertain,\
                'num_rejected': rejected, 'num_not_validated': not_validated})

def get_bad_file_description(name):
    category_dict = [ \
        {"name":"flux", "description": "File contains more than 40% NaN values for flux."},\
        {"name":"noise", "description": "File contains more than 40% NaN values for noise."},\
        {"name":"malformed", "description": "The files are missing values."},\
        {"name":"stalled", "description": "Linefinder repeatedly stopped on these files for unknown reason."}]
    for category in category_dict:
        if category["name"] == name:
            return category["description"]
    return None

def bad_ascii_view(request):
    session_id = request.POST.get('session_id')
    password = request.POST.get('pass')
    host = request.POST.get('host')
    try:
        conn = connect(password=password, host=host)
        conn.close()
    except:
        return HttpResponse("Password has failed")

    # Load the bad_files.json file
    bad_json_file = settings.BASE_DIR/"../../../cronjobs/bad_files/bad_files.json"
    sbid_source_dict = {}
    if os.path.exists(bad_json_file):
        with open(bad_json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for category in ['flux', 'noise', 'malformed', 'stalled']:
                category_data = data[category]
                description = get_bad_file_description(category)
                for sbid,sources in category_data.items():
                    if sbid not in sbid_source_dict:
                        sbid_source_dict[sbid] = []
                    sbid_source_dict[sbid].append(
                            [sources, category, description])
            f.close()
    else:
        return HttpResponse(f"{bad_json_file} is not found! Please run the cronjob to generate it.")
    #Flatten into rows, sorted by sbid
    rows = []
    last_bg = "white"
    sbid_source_dict = dict(sorted(sbid_source_dict.items()))
    for sbid, source_infos in sbid_source_dict.items():
        # Alternate color every sbid
        bg_color = "lightgrey" if last_bg == "white" else "white"
        for source_info in source_infos:
            rows.append([sbid,source_info[0],source_info[1],source_info[2],bg_color])
        last_bg = bg_color

    return render(request, "bad_ascii.html", {"session_id": session_id, "rows": rows, "num_sbids": len(sbid_source_dict)})

def query_database(request):
    # Build the SQL query using Django's SQL syntax
    password = request.POST.get('pass')
    host = request.POST.get('host')
    session_id = request.POST.get('session_id')
    # Try a psycopg2 connection with the supplied password. If it fails, return error msg
    try:
        conn = connect(password=password, host=host)
        conn.close()
    except:
        return HttpResponse("Password has failed")
    
    query_type = request.POST.get('query_type')
    reverse = False

    if query_type == "QUERY":
        sbid_val = request.POST.get('sbid_query')
        order = request.POST.get('order')
        reverse = request.POST.get('reverse1')
        pilot1 = request.POST.get('pilot1')
        pilot2 = request.POST.get('pilot2')
        survey1 = request.POST.get('survey1')
        no_bad_sbids = request.POST.get('bad')

        if reverse == "on":
            reverse = True
        if order == "date":
            order = "sp.date"
        elif order == "SBID":
            order = "s.sbid_num"
        else:
            order = f"s.{order}"

        where_clause = None
        if pilot1:
            where_clause = " where sp.run_tag in ('flash pilot 1'"
        if pilot2:
            if not where_clause:
                where_clause = " where sp.run_tag in ('flash pilot 2'"
            else:
                where_clause = where_clause + ",'flash pilot 2'"
        if survey1:
            if not where_clause:
                where_clause = " where sp.run_tag in ('FLASH Survey 1'"
            else:
                where_clause = where_clause + ",'FLASH Survey 1'"
        if where_clause:
                where_clause = where_clause +") "
        if no_bad_sbids:
                if where_clause:
                    where_clause = where_clause + "and s.quality not in ('BAD','REJECTED') "
                else:
                    where_clause = " where s.quality not in ('BAD','REJECTED') "

        with connection.cursor() as cursor:
            if sbid_val == "-1":
                query = f"SELECT sp.date,s.sbid_num,s.version,s.quality,sp.run_tag,s.detectionF,s.invert_detectionF,s.mask_detectionF,s.pointing,s.comment FROM SBID s inner join spect_run sp on sp.id = s.spect_runid"                
                mask_query = f"select s.mask,s.sbid_num,s.version FROM SBID s inner join spect_run sp on sp.id = s.spect_runid"
                if where_clause:
                    query = query + where_clause
                    mask_query += where_clause
                query = query + f" order by {order}"
                mask_query = mask_query + f" order by {order}"
                if reverse:
                    query += " desc;"
                    mask_query += " desc;"
                else:
                    query += ";"
                    mask_query += ";"
                cursor.execute(query,)
            else:
                query = f"SELECT sp.date,s.sbid_num,s.version,s.quality,sp.run_tag,s.detectionF,s.invert_detectionF,s.mask_detectionF,s.pointing,s.comment FROM SBID s inner join spect_run sp on sp.id = s.spect_runid where s.sbid_num = %s order by {order}"
                mask_query = f"select s.mask,s.sbid_num,s.version FROM SBID s inner join spect_run sp on sp.id = s.spect_runid where s.sbid_num = %s"
                if reverse:
                    query += " desc;"
                    mask_query += " desc;"
                else:
                    query += ";"
                    mask_query += ";"
                cursor.execute(query,(sbid_val,))
            rows = cursor.fetchall()
            cursor.execute(mask_query, (sbid_val if sbid_val != "-1" else None,))
            mask_rows = cursor.fetchall()
            mask_files = download_mask_files(mask_rows, session_id)

        # Render the template with the query results
        return render(request, 'query_results.html', {'session_id': session_id, 'sbid': sbid_val, 'rows': rows, 'num_rows': len(rows), 'mask_files': mask_files})

    elif query_type == "LINEFINDER":
        password = request.POST.get('pass')
        sbid_val = request.POST.get('sbid_line')
        lmean = request.POST.get('mean')
        order = request.POST.get('lorder')
        reverse = request.POST.get('reverse2')
        output_type = request.POST.get('output_type')

        use_invert = False
        use_masked = False
        if output_type == "inverted":
            use_invert = True
        elif output_type == "masked":
            use_masked = True

        if reverse == "on":
            reverse = True
        else:
            reverse = False
            
        with connection.cursor() as cursor:
            inverted = False
            masked = False
            if use_invert:
                # See if there are any inverted-spectra linefinder results
                query = f"SELECT invert_detectionF from sbid where sbid_num = %s"
                cursor.execute(query,(sbid_val,))
                inverted_results = cursor.fetchone()
                if inverted_results and inverted_results[0]:
                    inverted = inverted_results[0]
                else:
                    return HttpResponse(f"No inverted-spectra Linefinder results for sbid {sbid_val}")
            print(f"inverted value = {inverted}")
            if use_masked:
                # See if there are any masked-spectra linefinder results
                query = f"SELECT mask_detectionF from sbid where sbid_num = %s"
                cursor.execute(query,(sbid_val,))
                masked_results = cursor.fetchone()
                if masked_results and masked_results[0]:
                    masked = masked_results[0]
                else:
                    return HttpResponse(f"No masked-spectra Linefinder results for sbid {sbid_val}")
            print(f"masked value = {masked}")
            # The path to Django's static dir for linefinder outputs
            static_dir = os.path.abspath(f"db_query/static/db_query/linefinder/{session_id}/")
            os.system(f"mkdir -p {static_dir}")
            version = None
            # Screen outputs:
            outputs,alt_outputs = get_results_for_sbid(cursor,sbid_val,version,lmean,order,reverse,static_dir,inverted,masked)
        # Full tarball of results - here we need to open a psycopg2 connection to access the lob:
        if outputs:
            conn = connect(password=password)
            name = get_linefinder_tarball(conn,sbid_val,static_dir,version,inverted,masked)
            conn.close()

            tarball = f"db_query/linefinder/{session_id}/{name}"
            if inverted:
                csv_file = f"db_query/linefinder/{session_id}/{sbid_val}_linefinder_inverted_outputs.csv"
            elif masked:
                csv_file = f"db_query/linefinder/{session_id}/{sbid_val}_linefinder_masked_outputs.csv"
            else:
                csv_file = f"db_query/linefinder/{session_id}/{sbid_val}_linefinder_outputs.csv"
            return render(request, 'linefinder.html', {'session_id': session_id, 'sbid': sbid_val, 'lmean': lmean,\
                'outputs': outputs, 'csv_file': csv_file, 'alt_outputs': alt_outputs, 'num_outs': len(outputs), \
                'tarball': tarball, 'inverted':inverted, 'masked':masked})
        else:
            return HttpResponse(f"No Linefinder results for sbid {sbid_val}")

    elif query_type == "SOURCE":
        sbid_val = request.POST.get('sbid_source')
        comp = request.POST.get('comp')
        bright = request.POST.get('bright')
        view_or_tar = request.POST.get("view_or_tar")
        metadata = getSBIDmetadata(sbid_val)
        with connection.cursor() as cur:
            sources = []
            if bright:
                # we are getting plots for multiple sources
                comps = get_bright_comps(cur,sbid_val,bright)
            else:
                # comp may be a singular, or else a comma separated string of comps
                comps = []
                comp_vals = comp.split(',')
                for val in comp_vals:
                    val = val.strip()
                    if not val:
                        continue
                    comp = f"spec_SB{sbid_val}_component_{val}.fits"
                    comps.append(comp)
            # The path to Django's static dir for plots
            static_dir = os.path.abspath(f"db_query/static/db_query/plots/{session_id}/")
            os.system(f"mkdir -p {static_dir}")
            version = None
            for comp in comps:
                flux,opd = get_plots_for_comp(cur,sbid_val,comp,static_dir)
                if flux and opd:
                    radec = get_comp_ra_dec(cur,comp)
                    sources.append([f"db_query/plots/{session_id}/{flux}",f"db_query/plots/{session_id}/{opd}",radec])
            tarball_name = f"{sbid_val}_plots.tar"
            os.system(f"cd {static_dir}; tar -zcvf {tarball_name} spec_SB{sbid_val}*")
            tarball = f"db_query/plots/{session_id}/{tarball_name}"

        return render(request, 'source.html', {'session_id': session_id, 'sbid': sbid_val, 'comp_id': comp, 'brightest':bright, 'sources': sources, 'num_sources': int(len(sources)), 'tarball': tarball,'render': view_or_tar, 'metadata': metadata})
    elif query_type == "ASCII":
        ascii_dir = os.path.abspath(f"db_query/static/db_query/ascii/{session_id}/")
        os.system(f"mkdir -p {ascii_dir}")
        sbid_val = request.POST.get('sbid_for_ascii')
        with connection.cursor() as cur:
            sid,version = get_max_sbid_version(cur,sbid_val)
            conn = connect(password=password)
            get_ascii_files_tarball(conn,cur,sid,sbid_val,ascii_dir,version,password)
            conn.close()
            ascii_tar = f"db_query/ascii/{session_id}/{sbid_val}_{version}.tar.gz"

        return render(request, 'ascii.html', {'session_id': session_id, 'sbid': sbid_val, 'version': version, 'ascii_tar': ascii_tar})

def download_mask_files(mask_rows, session_id):
    # Stage mask file downloads
    mask_files = []
    if len(mask_rows) > 0:
        static_dir = os.path.abspath(f"db_query/static/db_query/linefinder/masks/{session_id}")
        os.system(f"mkdir -p {static_dir}")
        for mask_row in mask_rows:
            mask = mask_row[0]
            if mask:
                sbid_val = mask_row[1]
                version = mask_row[2]
                mask_file = f"{static_dir}/{sbid_val}_{version}_mask.txt"
                # TODO: When the bytea column is available, we use 'wb' mode instead
                open(mask_file, 'w').write(mask)
                mask_file_link = f"db_query/linefinder/masks/{session_id}/{sbid_val}_{version}_mask.txt"
                mask_files.append(mask_file_link)
            else:
                mask_files.append(None)
    return mask_files

def my_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT sbid_num,version,comment FROM SBID order by sbid_num,version;")
        rows = cursor.fetchall()

    return render(request, 'my_template.html', {'rows': rows, 'num_rows': len(rows)})
