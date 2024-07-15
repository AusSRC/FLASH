import os
import sys
import re
import psycopg2
import random
import string

from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
from .models import MyModel

#######################################################################################

def connect(db="flashdb",user="flash",host="146.118.64.208",password=None):

    if not password:
        password = PASSWD
    conn = psycopg2.connect(
        database = db,
        user = user,
        password = password,
        host = host,
        port = 2095
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
def get_results_for_sbid(cur,sbid,version,LN_MEAN,order,reverse,dir_download,verbose=True):

    # This will print out a table of linefinder output data for a given sbid
    # args[1] = db cursor
    # args[2] = The sbid you want to use - if a version is not declared ("45833" rather than "45833:2"),
    #           then use the latest version
    # args[3] = The sbid version you want to use - if a version is not declared ("45833" rather than "45833:2"),
    #           then use the latest version
    # args[4] = ln_mean cutoff - only sources with an ln_mean() value larger than this will be shown
    #           If no value is given, it will be set to 0.0

    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)
    #print(f"For {sbid}:{version} ...")
    # min val for ln_mean:
    try:
        ln_mean = float(LN_MEAN)
    except ValueError: # No value given. Set to 0
        ln_mean = 0.0
    
    # Get the relevant results file from the detect_run table:
    query = "select detect_runid from sbid where id = %s;"
    cur.execute(query,(sid,))
    res = cur.fetchone()[0]
    if not res:
        print(f"ERROR - {sbid} not in detection table")
        return 
    detect_runid = int(res)
    query = "select results from detect_run where id = %s;"
    cur.execute(query,(detect_runid,))
    try:
        result_data = cur.fetchone()[0].split('\n')
    except TypeError:
        print(f"Output data = 0 for sbid {sbid}:{version}!")
        return 

    # Get the pointing field for the sbid:
    query = "select pointing from sbid where id = %s;"
    cur.execute(query,(sid,))
    pointing = cur.fetchone()[0]

    # Get the list of relevant components and their values for this sbid from the component table
    if ln_mean == -1: # This means get all components, even if there is no value for ln_mean
        if order == "lnmean":
            query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s order by ln_mean,mode_num")
            if reverse:
                query += " desc;"
            else:
                query += ";"
        else:
            query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s order by comp_id")
            if reverse:
                query += " desc;"
            else:
                query += ";"
        cur.execute(query,(sid,))
    else:
        if order == "lnmean":
            query = ("select component_name,comp_id,ra_hms_cont,dec_dms_cont,ra_deg_cont,dec_deg_cont,flux_peak,flux_int,has_siblings,mode_num,ln_mean from component where sbid_id = %s and ln_mean > %s and mode_num > 0 order by ln_mean,mode_num")
            if reverse:
                query += " desc;"
            else:
                query += ";"
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
def get_linefinder_tarball(conn,sbid,dir_download,version):
    cur = get_cursor(conn)
    # get the corresponding sbid id for the sbid_num:version
    sid,version = get_max_sbid_version(cur,sbid,version)

    oid = None
    outputs = None
    name = f"{sbid}_{version}.tar"
    query = "select detectionF from sbid where id = %s"    
    cur.execute(query,(sid,))
    detect = cur.fetchone()[0]
    if not detect:
        print(f"No linefinder results available for sbid {sbid}:{version} !!")
        return
    # The output files are normally stored as both a byte array AND a large object.
    # If the LOB exists, down load that in preference to the byte array, as it's more efficient:
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
            query = f"select fluxfilter from component where comp_id = %s and sbid_id = %s;"
            cur.execute(query,(source_name,sid))
            flux_filter = cur.fetchone()[0]
            print(f"plotfile for {source_name} missing from db. Flux cutoff was {flux_filter}")
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
    try:
        session_id = request.session.get("session_id")
        # Cleanup session files
        os.system(f"rm -R {static_dir}/plots/{session_id}")
        os.system(f"rm -R {static_dir}/linefinder/{session_id}")
    except:
        session_id = generate_id(4)
        request.session["session_id"] = session_id
        
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) from sbid;")
        num_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 1%';")
        pilot1_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 1%' and sbid.quality = 'REJECTED';")
        pilot1_reject = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 2%';")
        pilot2_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%pilot 2%' and sbid.quality = 'REJECTED';")
        pilot2_reject = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%Survey%';")
        survey_records = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%Survey%' and sbid.quality = 'REJECTED';")
        survey_reject = cursor.fetchone()[0]
        cursor.execute("select count(*) from sbid inner join spect_run on sbid.spect_runid = spect_run.id where spect_run.run_tag like '%Survey%' and sbid.quality = 'NOT_VALIDATED';")
        survey_unvalidated = cursor.fetchone()[0]
    return render(request, 'index.html', {'records': num_records, 
                                          'pilot1': pilot1_records, 
                                          'rpilot1': pilot1_reject, 
                                          'pilot2': pilot2_records, 
                                          'rpilot2': pilot2_reject, 
                                          'survey': survey_records,
                                          'rsurvey': survey_reject,
                                          'unvalid': survey_unvalidated,
                                          'id': session_id})

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
    return render(request, 'csv_parse.html', {'csv_file': csv_file, 'sbid': sbid_val, 'lnmean': lnmean})

def query_database(request):
    # Build the SQL query using Django's SQL syntax
    #qs = MyModel.objects.all().values('name', 'age')
    password = request.POST.get('pass')
    session_id = request.session["session_id"]
    # Try a psycopg2 connection with the supplied password. If it fails, return error msg
    try:
        conn = connect(password=password)
        conn.close()
    except:
        return HttpResponse("Password failed")
    
    query_type = request.POST.get('query_type')
    reverse = False

    if query_type == "QUERY":
        sbid_val = request.POST.get('sbid_query')
        order = request.POST.get('order')
        reverse = request.POST.get('reverse1')
        if reverse == "on":
            reverse = True
        if order == "date":
            order = "sp.date"
        elif order == "SBID":
            order = "s.sbid_num"
        else:
            order = f"s.{order}"
        with connection.cursor() as cursor:
            if sbid_val == "-1":
                query = f"SELECT sp.date,s.sbid_num,s.version,s.quality,sp.run_tag,s.detectionF,s.pointing,s.comment FROM SBID s inner join spect_run sp on sp.id = s.spect_runid order by {order}"
                if reverse:
                    query += " desc;"
                else:
                    query += ";"
                cursor.execute(query,)
            else:
                query = f"SELECT sp.date,s.sbid_num,s.version,s.quality,sp.run_tag,s.detectionF,s.pointing,s.comment FROM SBID s inner join spect_run sp on sp.id = s.spect_runid where s.sbid_num = %s order by {order}"
                if reverse:
                    query += " desc;"
                else:
                    query += ";"
                cursor.execute(query,(sbid_val,))
            rows = cursor.fetchall()

        # Render the template with the query results
        return render(request, 'query_results.html', {'id': session_id, 'sbid': sbid_val, 'rows': rows, 'num_rows': len(rows)})

    elif query_type == "LINEFINDER":
        password = request.POST.get('pass')
        sbid_val = request.POST.get('sbid_line')
        lmean = request.POST.get('mean')
        order = request.POST.get('lorder')
        reverse = request.POST.get('reverse2')
        if reverse == "on":
            reverse = True
        with connection.cursor() as cursor:
            # The path to Django's static dir for linefinder outputs
            static_dir = os.path.abspath(f"db_query/static/db_query/linefinder/{session_id}/")
            os.system(f"mkdir -p {static_dir}")
            version = None
        # Screen outputs:
            outputs,alt_outputs = get_results_for_sbid(cursor,sbid_val,version,lmean,order,reverse,static_dir)
            # Full tarball of results - here we need to open a psycopg2 connection to access the lob:
            conn = connect(password=password)
            name = get_linefinder_tarball(conn,sbid_val,static_dir,version)
            conn.close()

            csv_file = f"db_query/linefinder/{session_id}/{sbid_val}_linefinder_outputs.csv"
            tarball = f"db_query/linefinder/{session_id}/{name}"
        if outputs:
            return render(request, 'linefinder.html', {'id': session_id, 'sbid': sbid_val, 'lmean': lmean,'outputs': outputs, 'csv_file': csv_file, 'alt_outputs': alt_outputs, 'num_outs': len(outputs), 'tarball': tarball})
        else:
            return HttpResponse(f"No Linefinder results for sbid {sbid_val}")

    elif query_type == "SOURCE":
        sbid_val = request.POST.get('sbid_source')
        comp = request.POST.get('comp')
        bright = request.POST.get('bright')
        metadata = getSBIDmetadata(sbid_val)
        with connection.cursor() as cur:
            sources = []
            if bright:
                # we are getting plots for multiple sources
                comps = get_bright_comps(cur,sbid_val,bright)
            else:
                comp = f"spec_SB{sbid_val}_component_{comp}.fits"
                comps = [comp]
            # The path to Django's static dir for plots
            static_dir = os.path.abspath("db_query/static/db_query/plots/{session_id}/")
            os.system(f"mkdir -p {static_dir}")
            version = None
            for comp in comps:
                flux,opd = get_plots_for_comp(cur,sbid_val,comp,static_dir)
                radec = get_comp_ra_dec(cur,comp)
                sources.append([f"db_query/plots/{session_id}/{flux}",f"db_query/plots/{session_id}/{opd}",radec])
            tarball_name = f"{sbid_val}_plots.tar"
            os.system(f"cd {static_dir}; tar -zcvf {tarball_name} spec_SB{sbid_val}*")
            tarball = f"db_query/plots/{session_id}/{tarball_name}"

        return render(request, 'source.html', {'id': session_id, 'sbid': sbid_val, 'comp_id': comp, 'brightest':bright, 'sources': sources, 'num_sources': int(len(sources)), 'tarball': tarball,'metadata': metadata})




def my_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT sbid_num,version,comment FROM SBID order by sbid_num,version;")
        rows = cursor.fetchall()

    return render(request, 'my_template.html', {'rows': rows, 'num_rows': len(rows)})
