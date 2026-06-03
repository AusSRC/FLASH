import os
import time
import tempfile
import subprocess

import psycopg2


PROD_DB = {
    "host": "10.0.2.225",
    "user": "flash",
    "dbname": "flashdb",
    "port": 5432,
    "password": os.environ["PGPASSWORD"],
}

REMOTE_HOST = "grees1@data-mover.pawsey.org.au"
REMOTE_DIR = "/scratch/ja3/mah128/flashdb"

CHUNK = 8 * 1024 * 1024  # 8 MB
PAUSE_BETWEEN_FILES = 2  # seconds


def export_lobject_to_file(conn, oid, local_path):
    """
    Export postgres large object to local temp file.
    Sequential reads only -> gentle on DB.
    """

    lo = conn.lobject(oid, "rb")

    total = 0
    start = time.time()

    try:
        with open(local_path, "wb") as f:
            while True:
                data = lo.read(CHUNK)

                if not data:
                    break

                f.write(data)
                total += len(data)

        elapsed = time.time() - start

        mb = total / 1024 / 1024

        print(
            f"OID {oid}: "
            f"{mb:.1f} MB exported "
            f"in {elapsed:.1f}s "
            f"({mb/elapsed:.1f} MB/s)"
        )

    finally:
        lo.close()


def get_remote_existing_files():
    """
    Fetch list of already-uploaded files in one SSH call.
    """

    cmd = [
        "ssh",
        REMOTE_HOST,
        f"ls -1 {REMOTE_DIR}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    return set(result.stdout.splitlines())


def rsync_to_remote(local_path, remote_path):
    """
    Upload using rsync.
    More robust than raw ssh streaming.
    """

    print(f"Uploading -> {remote_path}")

    subprocess.run(
        [
            "rsync",
            "-av",
            "--partial",
            "--progress",
            local_path,
            f"{REMOTE_HOST}:{remote_path}",
        ],
        check=True,
    )


def process_oid(conn, sbid, oid):
    """
    Export -> upload -> cleanup
    """

    filename = f"sbid_{sbid}_ascii_tar_oid_{oid}.tar"

    remote_path = f"{REMOTE_DIR}/{filename}"

    print(f"Starting: {filename}")

    # temp file on VM local disk
    with tempfile.NamedTemporaryFile(
        prefix=f"{oid}_",
        suffix=".tar",
        delete=False,
    ) as tmp:

        local_path = tmp.name

    try:
        # -------------------------
        # Export from postgres
        # -------------------------
        export_lobject_to_file(
            conn=conn,
            oid=oid,
            local_path=local_path,
        )

        # -------------------------
        # Upload to Pawsey
        # -------------------------
        rsync_to_remote(
            local_path=local_path,
            remote_path=remote_path,
        )

        print(f"Completed: {filename}")

    finally:
        # -------------------------
        # Always cleanup local temp
        # -------------------------
        if os.path.exists(local_path):
            os.remove(local_path)

    # brief pause so we don't hammer DB/filesystem
    time.sleep(PAUSE_BETWEEN_FILES)


def main():

    conn = psycopg2.connect(**PROD_DB)

    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT sbid_num, ascii_tar
            FROM sbid
            WHERE quality IN ('GOOD', 'UNCERTAIN')
            """
        )

        sbids = cur.fetchall()

        print(f"Found {len(sbids)} OIDs")

        existing = get_remote_existing_files()
        existing = {
            f for f in existing
            if not f.endswith(".part")
        }
        print(f"Remote already has {len(existing)} files")

        filtered_sbids = [
            (sbid, oid)
            for sbid, oid in sbids
            if
            oid is not None and f"sbid_{sbid}_ascii_tar_oid_{oid}.tar" not in existing
        ]
        print(f"Found {len(sbids)} OIDs")
        print(f"Processing {len(filtered_sbids)} new OIDs")

        for sbid, oid in filtered_sbids:
            try:
                process_oid(conn, sbid, oid)
            except Exception as e:
                print(f"FAILED sbid={sbid} oid={oid}: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()