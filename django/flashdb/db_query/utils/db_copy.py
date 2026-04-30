import subprocess
import os
import psycopg2
import time
import socket


SBID_NUM = 60095

PROD_VM_HOST = "flash@152.67.97.254"
PROD_DB_HOST = "10.0.2.225"
PROD_DB_PORT = 5432
LOCAL_PROD_DB_PORT = 55432

# Note this is localhost but still PROD DB as its port forwarded via the VM
PROD_DB = {
    "host": "localhost",
    "user": "flash",
    "dbname": "flashdb",
    "port": LOCAL_PROD_DB_PORT,
    "password": os.environ["PGPASSWORD"]
}

# This is your local db after tunnel has been dropped
DEV_DB = {
    "host": "localhost",
    "user": "flash",
    "dbname": "flashdb",
    "port": 5432
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
    print("Opening Tunnel")
    return subprocess.Popen([
        "ssh",
        "-i", SSH_KEY,
        "-N",
        "-L", f"{LOCAL_PROD_DB_PORT}:{PROD_DB_HOST}:{PROD_DB_PORT}",
        PROD_VM_HOST
    ])


def wait_for_db():
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


def copy(cur, filename, sql, params):
    with open(filename, "w") as f:
        q = cur.mogrify(sql, params).decode()
        cur.copy_expert(
            f"COPY ({q}) TO STDOUT WITH (FORMAT csv, HEADER true)", f
        )


def get_columns(cur, table):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return [r[0] for r in cur.fetchall()]


def load_csv(conn, table, csv_path, columns):
    print(f'Loading in {table}')
    cols = ",".join(columns)

    sql = f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)"

    with open(csv_path, "r") as f:
        with conn.cursor() as cur:
            cur.copy_expert(sql, f)

    conn.commit()


def export_lobject(conn, oid, path, chunk=CHUNK):
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


def get_oid_data(conn, sbid_map):
    for field in OID_FIELDS:
        oid = sbid_map.get(field)
        if oid:
            export_lobject(conn, oid, f"{field}_{oid}.bin")


def fetch_from_remote():
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
        copy(cur, "sbid.csv", sql, (SBID_NUM,))

        print('Copying Components')
        comp_cols = get_columns(cur, "component")
        sql = f"""         
            SELECT {",".join(comp_cols)}
            FROM component
            WHERE sbid_id = %s
            ORDER BY id DESC 
            LIMIT 10
        """
        copy(cur, "component.csv", sql, (sbid_id,))

        spect_cols = None
        if spect_id:
            print('Copying Spect Runs')
            spect_cols = get_columns(cur, "spect_run")
            sql = f"""
                SELECT {",".join(spect_cols)}
                FROM spect_run
                WHERE id = %s
            """
            copy(cur, "spect_run.csv", sql, (spect_id,))

        detect_cols = None
        if len(detect_ids) > 0:
            print('Copying Detect Runs')
            detect_cols = get_columns(cur, "detect_run")
            sql = f"""
                SELECT {",".join(detect_cols)}
                FROM detect_run
                WHERE id = ANY(%s)
            """
            copy(cur, "detect_run.csv", sql, (detect_ids,))

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

    return sbid_cols, comp_cols, spect_cols, detect_cols, spect_id, detect_ids


def write_to_local(
        sbid_cols,
        spect_cols,
        detect_cols,
        comp_cols,
        spect_id,
        detect_ids
):
    conn = None
    try:

        conn = psycopg2.connect(
            host=DEV_DB["host"],
            user=DEV_DB["user"],
            dbname=DEV_DB["dbname"],
            port=DEV_DB["port"]
        )

        # -------------------------
        # Load Table Data
        # -------------------------
        if spect_id:
            load_csv(conn, "spect_run", "spect_run.csv", spect_cols)
        if len(detect_ids) > 0:
            load_csv(conn, "detect_run", "detect_run.csv", detect_cols)
        load_csv(conn, "sbid", "sbid.csv", sbid_cols)
        load_csv(conn, "component", "component.csv", comp_cols)

        # -------------------------
        # Fix sequences
        # -------------------------


        # -------------------------
        # Load OID Data in
        # -------------------------
        print('Loadin in OID Data')

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sbid_cols, comp_cols, spect_cols, detect_cols, spect_id, detect_ids = fetch_from_remote()

    # TODO IF COMING BACK TO THIS AFTER A WHILE, BE DAMN CAREFUL THIS DOESNT WRITE TO PROD!
    #write_to_local(sbid_cols, comp_cols, spect_cols, detect_cols, spect_id, detect_ids)

