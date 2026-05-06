import subprocess
import os
import psycopg2
import time
import socket

"""
The purpose of this script is to populate your local database with a single
complete set of data for one SBID in order to do basic testing.
"""

# Pre-setup Instructions
# To get started install postgres18 and do this once you have entered the DB
# as the administrator
# 'psql postgres' or 'psql your_laptop_user' depending on how you installed PG
# CREATE DATABASE flashdbdev; <- For safety do not use Prod DB name here
# then quit postgres using \q

# Reconnect to local flashdbdev
# psql -d flashdbdev
# CREATE USER flashdev WITH PASSWORD 'password'; <- For safety do not use Prod password or usernames here
# GRANT ALL PRIVILEGES ON DATABASE flashdbdev TO flashdev;
# ALTER SCHEMA public OWNER TO flashdev;
# GRANT ALL ON SCHEMA public TO flashdev;

# Sets which SBID you wish to use for testing, ideally this should be a GOOD
# rated SBID quality with all of the current pipeline run options (masked etc)
# available for it so that you can test all Django UI options
SBID_NUM = 60095

# These settings are used to effectively make the PROD_DB_HOST available
# locally on LOCAL_PROD_DB_PORT
PROD_VM_HOST = "flash@152.67.97.254"
PROD_DB_HOST = "10.0.2.225"
PROD_DB_PORT = 5432
LOCAL_PROD_DB_PORT = 55432

# These settings then configure how to connect to the Prod DB on your localhost
# port.
# Note this is localhost but still PROD DB as its port forwarded via the VM
PROD_DB = {
    "host": "localhost",
    "user": "flash",
    "dbname": "flashdb",
    "port": LOCAL_PROD_DB_PORT,
    "password": os.environ["PGPASSWORD"]
}

# These settings define how you will connect to your actual local copy of the
# production database. They should match what you used to make your local db
# above
DEV_DB = {
    "host": "localhost",
    "user": "flashdev",
    "dbname": "flashdbdev",
    "port": 5432,
    "password": "password"
}

OID_FIELDS = [
    "ascii_tar",
    "detect_tar",
    "invert_detect_tar",
    "mask_detect_tar",
]

CHUNK = 1024 * 1024  # 1MB
SSH_KEY = os.path.expanduser("~/.ssh/flash_oracle_key")


def open_tunnel():
    """
    Opens the tunnel between the specified remote DB VM and your machine
    """
    print("Opening Tunnel")
    return subprocess.Popen([
        "ssh",
        "-i", SSH_KEY,
        "-N",
        "-L", f"{LOCAL_PROD_DB_PORT}:{PROD_DB_HOST}:{PROD_DB_PORT}",
        PROD_VM_HOST
    ])


def wait_for_db():
    """
    Retries DB for 10s every 0.5s while we wait for tunnel
    """
    print("Waiting for DB")
    for _ in range(20):
        try:
            s = socket.create_connection(
                ("localhost", LOCAL_PROD_DB_PORT),
                timeout=1
            )
            s.close()
            return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("Tunnel not ready")


def dump_csv(cur, filename, sql, params):
    """
    Dumps output from ran sql+sql params to specified filename as csv
    """
    with open(filename, "w") as f:
        q = cur.mogrify(sql, params).decode()
        cur.copy_expert(
            f"COPY ({q}) TO STDOUT WITH (FORMAT csv, HEADER true)", f
        )


def get_columns(cur, table):
    """
    Gets the columns in correct order for specified table, makes read/writes
    with differing sql column orders easy.
    """
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return [r[0] for r in cur.fetchall()]


def load_csv(conn, table, csv_path, columns):
    """
    Loads data from specified csv into specified columns in given table
    """
    print(f'Loading in {table}')
    cols = ",".join(columns)

    sql = f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)"

    with open(csv_path, "r") as f:
        with conn.cursor() as cur:
            cur.copy_expert(sql, f)

    conn.commit()


def export_lobject(conn, oid, path, chunk=CHUNK):
    """
    Exports given large objects by oid in chunks to the specified path
    """
    if oid is None:
        return
    i = 0
    lo = conn.lobject(oid, 'rb')
    with open(path, 'wb') as f:
        while True:
            if i % 50 == 0:
                print(f"{oid}: {i} chunks read")
            data = lo.read(chunk)
            if not data:
                break
            f.write(data)
            i = i+1
    lo.close()


def import_lobject(conn, oid, path, chunk=CHUNK):
    if oid is None:
        return
    """
    Imports given large objects path to specified oid in chunks
    """
    print(f"Restoring OID {oid}")

    with conn.cursor() as cur:
        cur.execute("SELECT lo_create(%s)", (oid,))

    lo = conn.lobject(oid, 'wb')

    with open(path, 'rb') as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            lo.write(data)

    lo.close()
    conn.commit()


def export_schema(schema_file):
    """
    Exports schema to specified schema file.
    """
    print("Exporting schema from production...")

    cmd = [
        "pg_dump",
        "-h", PROD_DB["host"],
        "-U", PROD_DB["user"],
        "-d", PROD_DB["dbname"],
        "-p", str(PROD_DB["port"]),
        "-s",  # schema only
        "-t", "sbid",
        "-t", "component",
        "-t", "spect_run",
        "-t", "detect_run",
        "-f", schema_file
    ]

    subprocess.run(cmd, check=True)

    print(f"Schema exported to {schema_file}")
    return schema_file


def import_schema(schema_file):
    """
    Imports schema from specified schema file.
    """
    print("Importing schema into local DB...")

    cmd = [
        "psql",
        "-h", DEV_DB["host"],
        "-U", DEV_DB["user"],
        "-d", DEV_DB["dbname"],
        "-f", schema_file
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = DEV_DB["password"]

    subprocess.run(cmd, env=env, check=True)

    print("Schema imported successfully")


def ensure_schema(schema_file):
    """
    Ensures schema exists in local DB by checking first then making it if not.
    # TODO make this generic, it currently checks for public.sbid
    """
    try:
        conn = psycopg2.connect(
            host=DEV_DB["host"],
            user=DEV_DB["user"],
            dbname=DEV_DB["dbname"],
            port=DEV_DB["port"],
            password=DEV_DB["password"],
        )
        cur = conn.cursor()

        # Cheap existence check
        cur.execute("""
            SELECT to_regclass('public.sbid')
        """)
        exists = cur.fetchone()[0]

        cur.close()
        conn.close()

        if exists:
            print("Schema already exists")
            return

    except Exception:
        pass

    print("Schema missing — rebuilding...")

    import_schema(schema_file)


def get_oid_data(conn, sbid_map):
    """
    Exports the large objects for each field that has them
    """
    for field in OID_FIELDS:
        oid = sbid_map.get(field)
        if oid:
            export_lobject(conn, oid, f"{field}_{oid}.bin")


def load_oid_data(conn, sbid_map):
    """
    Imports the large objects for each field that needs them
    """
    for field in OID_FIELDS:
        oid = sbid_map.get(field)
        if oid:
            path = f"{field}_{oid}.bin"
            import_lobject(conn, oid, path)


def fix_sequence(conn, table, id_col="id"):
    """
    Updates pq sequences to match the max in the imported tables
    """
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT setval(
                pg_get_serial_sequence(%s, %s),
                COALESCE(MAX({id_col}), 1),
                MAX({id_col}) IS NOT NULL
            )
            FROM {table}
        """, (table, id_col))
    conn.commit()


def fetch_from_remote():
    """
    Handles overall fetching of data from remote database
    """
    tunnel = open_tunnel()
    cur = None
    conn = None
    try:
        wait_for_db()

        conn = psycopg2.connect(
            host=PROD_DB["host"],
            user=PROD_DB["user"],
            dbname=PROD_DB["dbname"],
            port=PROD_DB["port"]
        )
        cur = conn.cursor()

        # -----
        schema_file = export_schema()

        # -------------------------
        # 1. Get other table ids for SBID
        # -------------------------
        cur.execute(
            "SELECT * FROM sbid WHERE sbid_num = %s",
            (SBID_NUM,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No SBID found for sbid_num={SBID_NUM}")

        cols = [d[0] for d in cur.description]
        sbid_map = dict(zip(cols, row))
        sbid_id = sbid_map["id"]
        spect_id = sbid_map.get("spect_runid")
        detect_ids = [
            sbid_map.get("detect_runid"),
            sbid_map.get("invert_detect_runid"),
            sbid_map.get("mask_detect_runid"),
            sbid_map.get("mask_invert_runid"),
        ]
        detect_ids = list(
            dict.fromkeys(i for i in detect_ids if i is not None)
        )

        # -------------------------
        # Copy Table Data
        # -------------------------
        print('Copying SBIDs')
        sbid_cols = get_columns(cur, "sbid")
        sql = f"""
            SELECT {",".join(sbid_cols)}
            FROM sbid
            WHERE sbid_num = %s
            ORDER BY id DESC 
            LIMIT 1
        """
        dump_csv(cur, "sbid.csv", sql, (SBID_NUM,))

        print('Copying Components')
        comp_cols = get_columns(cur, "component")
        sql = f"""         
            SELECT {",".join(comp_cols)}
            FROM component
            WHERE sbid_id = %s
            ORDER BY id DESC 
            LIMIT 10
        """
        dump_csv(cur, "component.csv", sql, (sbid_id,))

        spect_cols = None
        if spect_id:
            print('Copying Spect Runs')
            spect_cols = get_columns(cur, "spect_run")
            sql = f"""
                SELECT {",".join(spect_cols)}
                FROM spect_run
                WHERE id = %s
            """
            dump_csv(cur, "spect_run.csv", sql, (spect_id,))

        detect_cols = None
        if len(detect_ids) > 0:
            print('Copying Detect Runs')
            detect_cols = get_columns(cur, "detect_run")
            sql = f"""
                SELECT {",".join(detect_cols)}
                FROM detect_run
                WHERE id = ANY(%s)
            """
            dump_csv(cur, "detect_run.csv", sql, (detect_ids,))

        # -------------------------
        # Copy OID Data
        # -------------------------
        print('Copying OID Data')
        get_oid_data(conn, sbid_map)

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
        if tunnel is not None:
            tunnel.terminate()

    return (
        sbid_cols, comp_cols, spect_cols, detect_cols, spect_id, detect_ids,
        sbid_map, schema_file
    )


def write_to_local(
        sbid_cols,
        comp_cols,
        spect_cols,
        detect_cols,
        spect_id,
        detect_ids,
        sbid_map
):
    """
    Handles overall ingest of local csvs from remote database
    """
    conn = None
    try:
        print('Loading Tables & OIDs into:')
        print(f'User: {DEV_DB["user"]}')
        print(f'Host: {DEV_DB["host"]}')
        print(f'Database: {DEV_DB["dbname"]}')
        print(f'Port: {DEV_DB["port"]}')

        print('BE VERY SURE THE ABOVE IS NOT PRODUCTION OR YOUR LOCAL PORT '
              'FOR PRODUCTION IF YOU REUSED PROD PASSWORD!')
        answer = input("Do you want to continue? (y/n): ").lower().strip()
        if answer != "y":
            raise ValueError("User did not say 'y', erroring")

        conn = psycopg2.connect(
            host=DEV_DB["host"],
            user=DEV_DB["user"],
            dbname=DEV_DB["dbname"],
            port=DEV_DB["port"],
            password=DEV_DB["password"],
        )

        # -------------------------
        # Load Table Data
        # -------------------------
        if spect_id:
            load_csv(conn, "spect_run", "spect_run.csv", spect_cols)
            fix_sequence(conn, "spect_run")
        if len(detect_ids) > 0:
            load_csv(conn, "detect_run", "detect_run.csv", detect_cols)
            fix_sequence(conn, "detect_run")
        load_csv(conn, "sbid", "sbid.csv", sbid_cols)
        fix_sequence(conn, "sbid")

        load_csv(conn, "component", "component.csv", comp_cols)
        fix_sequence(conn, "component")


        # -------------------------
        # Load OID Data in
        # -------------------------
        print('Loadin in OID Data')
        load_oid_data(conn, sbid_map=sbid_map)

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    (sbid_cols, comp_cols, spect_cols, detect_cols, spect_id, detect_ids,
     sbid_map, schema_file) = fetch_from_remote()

    ensure_schema(schema_file)

    write_to_local(sbid_cols, comp_cols, spect_cols, detect_cols, spect_id, detect_ids, sbid_map)
